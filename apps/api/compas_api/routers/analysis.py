"""Analysis endpoints. Stub for v0.1 — real pipeline lands in Phase 1."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from compas_api.config import get_settings
from compas_api.db import Song, SongAnalysis, get_session

log = logging.getLogger("compas.analysis")
router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.post("/songs/{song_id}/analyze", status_code=202)
async def queue_analysis(song_id: str) -> dict:
    """Queue an analysis job. In v0.1 with run_ml_inline=True, this runs synchronously
    in the API request (slow, but no worker needed)."""
    settings = get_settings()
    with get_session() as s:
        song = s.get(Song, song_id)
        if not song:
            raise HTTPException(404, "Song not found")
        song.analysis_status = "running"
        s.commit()

    if settings.run_ml_inline:
        # Stub: mark as "done" with no real analysis yet.
        # Real implementation in Phase 1 will invoke the ML pipeline here.
        log.info("Inline ML run for %s (stub)", song_id)
        with get_session() as s:
            song = s.get(Song, song_id)
            assert song is not None
            analysis = SongAnalysis(
                id=str(uuid.uuid4()),
                song_id=song_id,
                version=song.analysis_version + 1,
                model_set={"stub": "v0.1"},
                status="done",
                confidence_overall=0.0,
                result={
                    "stub": True,
                    "message": "Real ML pipeline lands in Phase 1. For now, use the web prototype with mock data.",
                },
            )
            s.add(analysis)
            song.analysis_status = "done"
            song.analysis_version = analysis.version
            s.commit()
        return {"status": "done", "song_id": song_id, "version": analysis.version}
    else:
        # In Phase 4+, this would push to Dramatiq
        return {"status": "queued", "song_id": song_id}


@router.get("/songs/{song_id}/latest")
async def get_latest_analysis(song_id: str) -> dict:
    with get_session() as s:
        song = s.get(Song, song_id)
        if not song:
            raise HTTPException(404, "Song not found")
        analysis = (
            s.query(SongAnalysis)
            .filter(SongAnalysis.song_id == song_id)
            .order_by(SongAnalysis.version.desc())
            .first()
        )
        if not analysis:
            raise HTTPException(404, "No analysis yet")
        return {
            "song_id": song_id,
            "version": analysis.version,
            "status": analysis.status,
            "confidence_overall": analysis.confidence_overall,
            "result": analysis.result,
            "created_at": analysis.created_at.isoformat(),
        }
