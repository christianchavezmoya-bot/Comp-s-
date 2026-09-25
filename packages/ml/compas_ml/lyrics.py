"""Lyrics transcription + translation.

Stage 1: Whisper (or stable-whisper) for transcription with word-level timestamps.
Stage 2: NLLB-200 for translation (optional, lazy-loaded).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from compas_ml.io_utils import load_audio

log = logging.getLogger("compas.ml.lyrics")


@dataclass
class LyricLine:
    start_sec: float
    end_sec: float
    text: str
    vocal_type: str  # "lead", "backing", "coro", "soneo", "spoken"
    confidence: float
    words: list[dict] | None = None  # [{start, end, word, prob}]
    translation: dict[str, str] | None = None  # {"en": "...", "es": "..."}


@dataclass
class LyricsResult:
    language: str
    lines: list[LyricLine]
    elapsed_sec: float


def transcribe(
    y: np.ndarray,
    sr: int,
    model_name: str = "base",
    device: str = "cpu",
    word_level: bool = True,
    translate_to: list[str] | None = None,
) -> LyricsResult:
    """Transcribe a vocal stem (or the mix) to text with timestamps.

    Uses stable-whisper when word_level=True (more accurate word boundaries).
    Falls back to plain whisper if stable-whisper isn't installed.
    """
    t0 = time.time()
    log.info(
        "Transcribing (model=%s, device=%s, word_level=%s, translate_to=%s)",
        model_name, device, word_level, translate_to,
    )

    # 16kHz mono for Whisper
    if sr != 16000:
        from scipy.signal import resample_poly
        y16 = resample_poly(y, 16000, sr).astype(np.float32)
        sr_use = 16000
    else:
        y16 = y.astype(np.float32)
        sr_use = sr
    audio = _pad_or_trim(y16, 16000, 30)

    if word_level:
        try:
            result = _transcribe_stable(audio, model_name, device)
        except ImportError as e:
            log.warning("stable-whisper not available (%s), falling back to plain whisper", e)
            result = _transcribe_plain(audio, model_name, device, word_level=True)
    else:
        result = _transcribe_plain(audio, model_name, device, word_level=False)

    lines: list[LyricLine] = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if not text:
            continue
        # Extract word-level if present
        words = seg.get("words") or None
        lines.append(
            LyricLine(
                start_sec=float(seg.get("start", 0.0)),
                end_sec=float(seg.get("end", 0.0)),
                text=text,
                vocal_type="lead",  # TODO: classify lead/backing/coro/soneo
                confidence=float(seg.get("avg_logprob") or seg.get("no_speech_prob", 0.0) * -1),
                words=words,
            )
        )

    # Optional translation
    if translate_to:
        for line in lines:
            line.translation = _translate(line.text, result.get("language", "unknown"), translate_to)

    elapsed = time.time() - t0
    log.info(
        "Transcription done in %.1fs: %d lines, lang=%s, translations=%d",
        elapsed, len(lines), result.get("language", "?"), len(translate_to or []),
    )
    return LyricsResult(
        language=result.get("language", "unknown"),
        lines=lines,
        elapsed_sec=elapsed,
    )


def _pad_or_trim(y: np.ndarray, sr: int, max_sec: float) -> np.ndarray:
    n = int(max_sec * sr)
    if len(y) > n:
        return y[:n]
    if len(y) < n:
        return np.pad(y, (0, n - len(y)))
    return y


def _transcribe_stable(audio: np.ndarray, model_name: str, device: str) -> dict[str, Any]:
    """Use stable-whisper for refined word-level alignment."""
    import stable_whisper

    model = stable_whisper.load_model(model_name, device=device)
    # stable-whisper extends whisper.transcribe with better word alignment
    result = model.transcribe(
        audio,
        language=None,
        verbose=False,
        word_timestamps=True,
        regroup=True,
    )
    # Convert to plain dict
    return {
        "language": result.language,
        "segments": [
            {
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "avg_logprob": getattr(s, "avg_logprob", 0.0),
                "words": [
                    {
                        "start": w.start if w.start is not None else s.start,
                        "end": w.end if w.end is not None else s.end,
                        "word": w.word,
                        "prob": w.probability if hasattr(w, "probability") else getattr(w, "prob", 0.0),
                    }
                    for w in (s.words or [])
                ],
            }
            for s in result.segments
        ],
    }


def _transcribe_plain(audio: np.ndarray, model_name: str, device: str, word_level: bool) -> dict[str, Any]:
    """Plain Whisper fallback."""
    import whisper

    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(
        audio,
        language=None,
        verbose=False,
        word_timestamps=word_level,
    )
    return result


# ====== NLLB-200 translation ======

_NLLB_MODEL = None
_NLLB_TOKENIZER = None
_NLLB_LOADED_FOR = None

# NLLB language code mapping (whisper ISO 639-1 -> NLLB)
_NLLB_LANG = {
    "en": "eng_Latn", "es": "spa_Latn", "pt": "por_Latn", "fr": "fra_Latn",
    "it": "ita_Latn", "de": "deu_Latn", "nl": "nld_Latn", "ru": "rus_Cyrl",
    "zh": "zho_Hans", "ja": "jpn_Jpan", "ko": "kor_Hang", "ar": "arb_Arab",
}


def _load_nllb(model_name: str = "facebook/nllb-200-distilled-600M"):
    global _NLLB_MODEL, _NLLB_TOKENIZER, _NLLB_LOADED_FOR
    if _NLLB_LOADED_FOR == model_name:
        return _NLLB_MODEL, _NLLB_TOKENIZER
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

    log.info("Loading NLLB model %s (one-time, ~600MB)...", model_name)
    _NLLB_TOKENIZER = AutoTokenizer.from_pretrained(model_name)
    _NLLB_MODEL = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    _NLLB_LOADED_FOR = model_name
    return _NLLB_MODEL, _NLLB_TOKENIZER


def _translate(text: str, src_lang: str, targets: list[str]) -> dict[str, str]:
    """Translate text into each of the target languages. Lazy-loads NLLB on first call."""
    out: dict[str, str] = {}
    if not text.strip():
        return out
    try:
        model, tok = _load_nllb()
    except Exception as e:
        log.warning("NLLB load failed: %s — translations skipped", e)
        return out
    src = _NLLB_LANG.get(src_lang, None)
    if src is None:
        # Whisper sometimes gives us just the language name; try a few common ones
        alias = {"english": "en", "spanish": "es", "portuguese": "pt"}
        src = _NLLB_LANG.get(alias.get(src_lang.lower(), src_lang), None)
        if src is None:
            return out
    for tgt_iso in targets:
        tgt = _NLLB_LANG.get(tgt_iso)
        if not tgt:
            log.warning("NLLB: unknown target language %s, skipping", tgt_iso)
            continue
        try:
            tok.src_lang = src
            enc = tok(text, return_tensors="pt")
            forced_bos = tok.convert_tokens_to_ids(tgt)
            gen = model.generate(**enc, forced_bos_token_id=forced_bos, max_length=256)
            translation = tok.decode(gen[0], skip_special_tokens=True)
            out[tgt_iso] = translation
        except Exception as e:
            log.warning("NLLB translation to %s failed: %s", tgt_iso, e)
    return out
