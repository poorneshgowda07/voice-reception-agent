"""
speech_to_text.py -- Transcribe an audio file using the Sarvam AI Speech-to-Text API.

Endpoint : POST https://api.sarvam.ai/speech-to-text
Auth     : api-subscription-key header (SARVAM_API_KEY in .env)
Model    : saaras:v3  (Sarvam's flagship STT model, supports en-IN + 22 Indian languages)
"""
import os
from pathlib import Path
from typing import Tuple, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

STT_ENDPOINT = "https://api.sarvam.ai/speech-to-text"
STT_MODEL    = "saaras:v3"


def transcribe_audio(audio_path: str) -> Tuple[str, Optional[str]]:
    """
    Transcribe an audio file via the Sarvam AI STT API.

    Returns:
        (transcript_text, error_message)
        On success: (text, None)
        On failure: ("", human-readable error string)
    """
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    # Fallback: Streamlit Cloud stores secrets in st.secrets, not .env
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("SARVAM_API_KEY", "").strip()
        except Exception:
            pass
    if not api_key:
        return "", (
            "[ERROR] SARVAM_API_KEY is not set. "
            "Add SARVAM_API_KEY=<your_key> to your .env file or Streamlit secrets."
        )

    audio_path = Path(audio_path)
    if not audio_path.exists():
        return "", f"[ERROR] Audio file not found: {audio_path}"

    # Determine MIME type from extension
    ext = audio_path.suffix.lower()
    mime_map = {
        ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
        ".ogg": "audio/ogg", ".flac": "audio/flac", ".webm": "audio/webm",
        ".aac": "audio/aac", ".opus": "audio/opus",
    }
    mime_type = mime_map.get(ext, "audio/wav")

    try:
        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                STT_ENDPOINT,
                headers={"api-subscription-key": api_key},
                files={"file": (audio_path.name, audio_file, mime_type)},
                data={"model": STT_MODEL, "language_code": "en-IN"},
                timeout=60,
            )

        if response.status_code == 200:
            data = response.json()
            transcript = data.get("transcript", "").strip()
            if not transcript:
                return "", "[ERROR] Sarvam returned an empty transcript."
            return transcript, None

        # Handle known error codes
        err_body = response.text
        if response.status_code == 401:
            return "", "[ERROR] Invalid SARVAM_API_KEY -- check your .env file."
        if response.status_code == 429:
            return "", "[ERROR] Sarvam rate limit reached -- wait a moment and retry."
        if response.status_code == 413:
            return "", "[ERROR] Audio file too large for Sarvam STT API (max ~25 MB)."
        return "", f"[ERROR] Sarvam STT returned HTTP {response.status_code}: {err_body[:300]}"

    except requests.exceptions.Timeout:
        return "", "[ERROR] Sarvam STT request timed out (60 s) -- try a shorter audio file."
    except requests.exceptions.ConnectionError:
        return "", "[ERROR] Cannot reach api.sarvam.ai -- check your internet connection."
    except Exception as exc:
        return "", f"[ERROR] Transcription error: {exc}"


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "audio/rahul_call.wav"
    print(f"Transcribing: {path}")
    text, error = transcribe_audio(path)
    if error:
        print(error)
    else:
        print("[OK] Transcript:")
        print(text)
