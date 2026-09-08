"""
text_to_speech.py -- Synthesize spoken audio using the Sarvam AI Text-to-Speech API.

Endpoint : POST https://api.sarvam.ai/text-to-speech
Auth     : api-subscription-key header (SARVAM_API_KEY in .env or st.secrets)
Model    : bulbul:v3
"""
import base64
import os
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

TTS_ENDPOINT = "https://api.sarvam.ai/text-to-speech"
TTS_MODEL = "bulbul:v3"


def generate_voice_response(
    text: str,
    speaker: str = "kavya",
    target_language_code: str = "en-IN",
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Generate spoken voice audio from text using Sarvam bulbul:v3.

    Args:
        text: The message script to be spoken.
        speaker: Voice persona (e.g., 'kavya', 'shubh', 'priya', 'aditya').
        target_language_code: Language code (default 'en-IN').

    Returns:
        (audio_bytes, error_message)
        On success: (bytes, None)
        On failure: (None, error_string)
    """
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("SARVAM_API_KEY", "").strip()
        except Exception:
            pass

    if not api_key:
        return None, "[ERROR] SARVAM_API_KEY is not set for Text-to-Speech."

    clean_text = text.strip()
    if not clean_text:
        return None, "[ERROR] Text for speech synthesis is empty."

    payload = {
        "inputs": [clean_text],
        "target_language_code": target_language_code,
        "speaker": speaker,
        "model": TTS_MODEL,
    }

    try:
        response = requests.post(
            TTS_ENDPOINT,
            headers={
                "api-subscription-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            err_body = response.text
            return None, f"[ERROR] Sarvam TTS returned HTTP {response.status_code}: {err_body[:200]}"

        data = response.json()
        audios = data.get("audios", [])
        if not audios:
            return None, "[ERROR] Sarvam TTS returned no audio data."

        # Decode base64 WAV audio bytes
        audio_bytes = base64.b64decode(audios[0])
        return audio_bytes, None

    except requests.exceptions.Timeout:
        return None, "[ERROR] Sarvam TTS request timed out (30 s)."
    except requests.exceptions.ConnectionError:
        return None, "[ERROR] Cannot connect to Sarvam TTS API."
    except Exception as exc:
        return None, f"[ERROR] Voice synthesis error: {exc}"


if __name__ == "__main__":
    sample_text = "Hello! Thank you for calling Blue Eye. Our team has received your inquiry and will reach out shortly."
    print("Testing text_to_speech.py...")
    audio, err = generate_voice_response(sample_text, speaker="kavya")
    if err:
        print(err)
    else:
        print(f"[OK] Voice generated successfully! ({len(audio)} bytes)")
