"""
agent.py -- LLM-based extraction of structured call data from a transcript.

Uses Sarvam AI Chat Completions API (sarvam-105b) via REST.
Endpoint : POST https://api.sarvam.ai/v1/chat/completions
Auth     : api-subscription-key header (SARVAM_API_KEY in .env)
Never invents values: anything not stated in the transcript is returned as null.
"""
import json
import os
import re
from typing import Dict, Any, Tuple, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

CHAT_ENDPOINT = "https://api.sarvam.ai/v1/chat/completions"
CHAT_MODEL    = "sarvam-105b"

SYSTEM_PROMPT = """You are a reception-call data extraction assistant.

Given a call transcript, extract EXACTLY these three fields:
  - caller_name      : The name the caller stated, or null if not mentioned.
  - intent           : A short description (<=15 words) of why they called, or null.
  - callback_number  : The phone number the caller provided, digits only (no spaces/dashes), or null.

Rules:
  1. Output ONLY valid JSON -- no markdown fences, no explanation, no extra text.
  2. Use null (JSON null, not the string "null") for any field not clearly stated.
  3. NEVER invent or infer values not explicitly in the transcript.

Example output:
{"caller_name": "Rahul", "intent": "Inquire about available courses", "callback_number": "9876543210"}"""


def extract_call_info(transcript: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Extract structured call info from a transcript via Sarvam sarvam-105b.

    Returns:
        (info_dict, error_message)
        On success: ({"caller_name": ..., "intent": ..., "callback_number": ...}, None)
        On failure: ({}, human-readable error string)
    """
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key:
        return {}, (
            "[ERROR] SARVAM_API_KEY is not set. "
            "Add SARVAM_API_KEY=<your_key> to your .env file."
        )

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
        "temperature": 0,
        "max_tokens": 1500,
    }

    raw = ""
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            headers={
                "api-subscription-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            err_body = response.text
            if response.status_code == 401:
                return {}, "[ERROR] Invalid SARVAM_API_KEY -- check your .env file."
            if response.status_code == 429:
                return {}, "[ERROR] Sarvam rate limit reached -- wait a moment and retry."
            return {}, f"[ERROR] Sarvam Chat returned HTTP {response.status_code}: {err_body[:300]}"

        data = response.json()
        raw = data["choices"][0]["message"]["content"] or ""
        raw = raw.strip()

        # Strip accidental markdown fences (model sometimes wraps in ```json)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        parsed = json.loads(raw)

        result = {
            "caller_name":     parsed.get("caller_name") or None,
            "intent":          parsed.get("intent") or None,
            "callback_number": parsed.get("callback_number") or None,
        }

        # Sanitize callback_number: keep digits only, regardless of how
        # the LLM formatted it (e.g. "9-8-7-6-5" -> "98765")
        if result["callback_number"]:
            digits_only = re.sub(r"\D", "", str(result["callback_number"]))
            result["callback_number"] = digits_only if digits_only else None

        return result, None

    except json.JSONDecodeError as exc:
        return {}, f"[ERROR] LLM returned malformed JSON: {exc}\nRaw: {raw!r}"
    except requests.exceptions.Timeout:
        return {}, "[ERROR] Sarvam Chat request timed out (60 s)."
    except requests.exceptions.ConnectionError:
        return {}, "[ERROR] Cannot reach api.sarvam.ai -- check your internet connection."
    except Exception as exc:
        return {}, f"[ERROR] LLM extraction error: {exc}"


if __name__ == "__main__":
    test_transcript = (
        "Hello, my name is Rahul. I'm calling to inquire about the available courses "
        "you offer. Could you please provide me with more details? "
        "You can reach me back at 9876543210. Thank you."
    )
    print("Testing agent with transcript:")
    print(test_transcript)
    print()
    result, error = extract_call_info(test_transcript)
    if error:
        print(error)
    else:
        print("[OK] Extracted info:")
        print(json.dumps(result, indent=2))
