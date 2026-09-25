"""Library CRUD. Stub for v0.1 — real auth comes in Phase 4."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from compas_api.config import get_settings
from compas_api.db import Song, get_session

log = logging.getLogger("compas.library")
router = APIRouter(prefix="/api/library", tags=["library"])


class SongOut(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None
    genre: str
    style: str | None
    duration_sec: float
    bpm: float | None
    analysis_status: str
    analysis_version: int
    visibility: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: Song) -> "SongOut":
        return cls(
            id=row.id,
            title=row.title,
            artist=row.artist,
            album=row.album,
            genre=row.genre,
            style=row.style,
            duration_sec=row.duration_sec,
            bpm=row.bpm,
            analysis_status=row.analysis_status,
            analysis_version=row.analysis_version,
            visibility=row.visibility,
            created_at=row.created_at,
        )


@router.get("/songs", response_model=list[SongOut])
async def list_songs(
    genre: str | None = None,
    visibility: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[SongOut]:
    with get_session() as s:
        q = s.query(Song)
        if genre:
            q = q.filter(Song.genre == genre)
        if visibility:
            q = q.filter(Song.visibility == visibility)
        rows = q.order_by(Song.created_at.desc()).limit(limit).offset(offset).all()
        return [SongOut.from_row(r) for r in rows]


@router.get("/songs/{song_id}", response_model=SongOut)
async def get_song(song_id: str) -> SongOut:
    with get_session() as s:
        row = s.get(Song, song_id)
        if not row:
            raise HTTPException(404, "Song not found")
        return SongOut.from_row(row)


@router.post("/songs", response_model=SongOut, status_code=201)
async def upload_song(
    title: Annotated[str, Form()],
    artist: Annotated[str, Form()],
    album: Annotated[str | None, Form()] = None,
    genre: Annotated[str, Form()] = "bachata",
    style: Annotated[str | None, Form()] = None,
    visibility: Annotated[str, Form()] = "private",
    audio: Annotated[UploadFile, File()] = ...,
) -> SongOut:
    """Upload a song. Stored locally. Analysis is queued."""
    settings = get_settings()
    settings_get = get_settings()
    if genre not in ("bachata", "salsa"):
        raise HTTPException(400, f"Unsupported genre: {genre} (only bachata, salsa)")
    if visibility not in ("private", "community"):
        raise HTTPException(400, "visibility must be 'private' or 'community'")

    song_id = str(uuid.uuid4())
    storage_root = Path(settings_get.storage_dir).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)
    song_dir = storage_root / "originals" / song_id
    song_dir.mkdir(parents=True, exist_ok=True)

    # Save the file
    suffix = Path(audio.filename or "audio.bin").suffix or ".bin"
    src_path = song_dir / f"source{suffix}"
    content = await audio.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")
    src_path.write_bytes(content)
    log.info("Saved %s (%d bytes) to %s", audio.filename, len(content), src_path)

    # Compute duration via ffprobe if available; else default 0
    duration = 0.0
    try:
        import json
        import subprocess

        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(src_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0:
            info = json.loads(out.stdout)
            duration = float(info.get("format", {}).get("duration", 0.0))
    except Exception as e:
        log.warning("ffprobe failed: %s", e)

    song = Song(
        id=song_id,
        title=title,
        artist=artist,
        album=album,
        genre=genre,
        style=style,
        duration_sec=duration,
        visibility=visibility,
        source_path=str(src_path),
    )
    with get_session() as s:
        s.add(song)
        s.commit()
        s.refresh(song)

    log.info("Created song %s (%s - %s)", song_id, title, artist)
    return SongOut.from_row(song)


@router.delete("/songs/{song_id}", status_code=204)
async def delete_song(song_id: str) -> None:
    with get_session() as s:
        row = s.get(Song, song_id)
        if not row:
            raise HTTPException(404, "Song not found")
        # Delete files
        if row.source_path:
            try:
                Path(row.source_path).unlink(missing_ok=True)
            except Exception as e:
                log.warning("Failed to delete %s: %s", row.source_path, e)
        s.delete(row)
        s.commit()


@router.get("/songs/{song_id}/audio")
async def stream_audio(song_id: str) -> FileResponse:
    """Stream the original uploaded audio file. Supports HTTP Range for seeking."""
    with get_session() as s:
        row = s.get(Song, song_id)
        if not row:
            raise HTTPException(404, "Song not found")
        if not row.source_path or not Path(row.source_path).exists():
            raise HTTPException(404, "Audio file not found on disk")
        path = Path(row.source_path)
    # Pick a media type that matches the file extension
    ext = path.suffix.lower()
    media_types = {
        ".flac": "audio/flac",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(path, media_type=media_type, filename=path.name)


@router.get("/songs/{song_id}/stems/{stem_name}")
async def stream_stem(song_id: str, stem_name: str) -> FileResponse:
    """Stream a separated stem (FLAC)."""
    settings = get_settings()
    stem_path = (
        Path(settings.storage_dir) / "analysis" / song_id / "stems" / f"{stem_name}.flac"
    )
    if not stem_path.exists():
        raise HTTPException(404, f"Stem '{stem_name}' not found")
    return FileResponse(stem_path, media_type="audio/flac", filename=stem_path.name)
