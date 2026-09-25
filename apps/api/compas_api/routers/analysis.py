"""Analysis endpoints. v0.2 — real ML pipeline via compas_ml."""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from compas_api.config import get_settings
from compas_api.db import Song, SongAnalysis, get_session

log = logging.getLogger("compas.analysis")
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Make compas_ml importable (sibling package)
_ML_PATH = Path(__file__).resolve().parents[4] / "packages" / "ml"
if str(_ML_PATH) not in sys.path:
    sys.path.insert(0, str(_ML_PATH))


def _run_pipeline_task(song_id: str) -> None:
    """Background task: run the ML pipeline and persist the result."""
    try:
        from compas_ml.pipeline import run_pipeline
        from compas_ml.config import PipelineConfig

        with get_session() as s:
            song = s.get(Song, song_id)
            if not song:
                log.error("Song %s disappeared mid-analysis", song_id)
                return
            source_path = Path(song.source_path)
            genre = song.genre
            song_id_val = song.id

        log.info("Running ML pipeline for %s (genre=%s)", song_id_val, genre)
        settings = get_settings()
        analysis_dir = Path(settings.storage_dir) / "analysis" / song_id_val
        analysis_dir.mkdir(parents=True, exist_ok=True)

        config = PipelineConfig(
            separator="htdemucs" if not settings.use_htdemucs_ft else "htdemucs_ft",
            separator_shifts=0,
            transcribe=settings.transcribe,
            whisper_model="base",
        )

        analysis = run_pipeline(
            source_path=source_path,
            out_dir=analysis_dir,
            genre=genre,
            config=config,
        )

        # Persist to DB
        with get_session() as s:
            song = s.get(Song, song_id_val)
            if not song:
                return
            version = song.analysis_version + 1
            db_analysis = SongAnalysis(
                id=str(uuid.uuid4()),
                song_id=song_id_val,
                version=version,
                model_set=analysis.get("model_set", {}),
                status="done",
                confidence_overall=float(analysis.get("confidence_overall", 0.0)),
                result=analysis,
            )
            s.add(db_analysis)
            song.analysis_status = "done"
            song.analysis_version = version
            song.bpm = float(analysis.get("global", {}).get("bpm", 0)) or None
            song.key_signature = analysis.get("global", {}).get("key")
            s.commit()
            log.info("Analysis done for %s v%d (confidence=%.2f)", song_id_val, version, db_analysis.confidence_overall)

    except Exception as e:
        log.exception("Pipeline failed for %s: %s", song_id, e)
        with get_session() as s:
            song = s.get(Song, song_id)
            if song:
                song.analysis_status = "failed"
                s.commit()


@router.post("/songs/{song_id}/analyze", status_code=202)
async def queue_analysis(song_id: str, background: BackgroundTasks) -> dict:
    """Queue an analysis job. Runs in background to avoid blocking the request."""
    settings = get_settings()
    with get_session() as s:
        song = s.get(Song, song_id)
        if not song:
            raise HTTPException(404, "Song not found")
        if not song.source_path or not Path(song.source_path).exists():
            raise HTTPException(400, "Source audio file not found")
        song.analysis_status = "running"
        s.commit()

    if settings.run_ml_inline:
        # Synchronous: block until done
        _run_pipeline_task(song_id)
        return {"status": "done", "song_id": song_id}
    else:
        background.add_task(_run_pipeline_task, song_id)
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


@router.get("/songs/{song_id}/status")
async def get_analysis_status(song_id: str) -> dict:
    with get_session() as s:
        song = s.get(Song, song_id)
        if not song:
            raise HTTPException(404, "Song not found")
        return {
            "song_id": song_id,
            "status": song.analysis_status,
            "version": song.analysis_version,
        }

