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

SYSTEM_PROMPT = """You are the AI Voice Receptionist for the company "Blue Eye".

Given a call transcript, extract and generate:
  - caller_name      : The name the caller stated, or null if not mentioned.
  - intent           : A short description (<=15 words) of why they called, or null.
  - callback_number  : The phone number the caller provided, digits only (no spaces/dashes), or null.
  - spoken_response  : A warm, professional 1-2 sentence spoken reply from "Blue Eye" addressing the caller by name (if known), acknowledging their intent, and confirming next steps.

Rules:
  1. Output ONLY valid JSON -- no markdown fences, no explanation, no extra text.
  2. Use null for caller_name or callback_number if not clearly stated.
  3. The spoken_response must ALWAYS mention "Blue Eye" as the company name. Never mention any other company name.
  4. NEVER invent phone numbers or caller names not explicitly in the transcript.

Example output:
{"caller_name": "Rahul", "intent": "Inquire about available courses", "callback_number": "9876543210", "spoken_response": "Hello Rahul, thank you for calling Blue Eye! We have received your inquiry regarding our available courses and will call you back at 9876543210 shortly."}"""


def extract_call_info(transcript: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Extract structured call info from a transcript via Sarvam sarvam-105b.

    Returns:
        (info_dict, error_message)
        On success: ({"caller_name": ..., "intent": ..., "callback_number": ...}, None)
        On failure: ({}, human-readable error string)
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
        return {}, (
            "[ERROR] SARVAM_API_KEY is not set. "
            "Add SARVAM_API_KEY=<your_key> to your .env file or Streamlit secrets."
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
        msg = data["choices"][0]["message"]

        # sarvam-105b is a reasoning model: it may put the JSON in
        # "content", or the JSON may only appear inside "reasoning_content"
        raw = (msg.get("content") or "").strip()

        # Strip accidental markdown fences
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        def _build_result(parsed: dict) -> dict:
            """Normalise a parsed dict into the standard result shape."""
            r = {
                "caller_name":     parsed.get("caller_name") or None,
                "intent":          parsed.get("intent") or None,
                "callback_number": parsed.get("callback_number") or None,
                "spoken_response": parsed.get("spoken_response") or None,
            }
            if r["callback_number"]:
                d = re.sub(r"\D", "", str(r["callback_number"]))
                r["callback_number"] = d if d else None
            if not r["spoken_response"]:
                name = r["caller_name"] or "there"
                intn = r["intent"] or "your inquiry"
                cb   = r["callback_number"]
                r["spoken_response"] = (
                    f"Hello {name}, thank you for calling Blue Eye. "
                    + (f"We will call you back at {cb} shortly." if cb
                       else f"We have received your message regarding {intn} and will respond shortly.")
                )
            return r

        try:
            parsed = json.loads(raw)
            return _build_result(parsed), None

        except json.JSONDecodeError:
            # content was truncated/malformed — try reasoning_content
            reasoning = (msg.get("reasoning_content") or "").strip()
            json_candidates = re.findall(r'\{[\s\S]*?"caller_name"[\s\S]*?\}', reasoning)
            for candidate in reversed(json_candidates):
                candidate = re.sub(r"```(?:json)?", "", candidate).strip().rstrip("`").strip()
                try:
                    return _build_result(json.loads(candidate)), None
                except json.JSONDecodeError:
                    continue

            # Last resort: extract from transcript directly via regex
            phone_match = re.search(r'\b[6-9]\d{9}\b', transcript)
            cb_fallback = phone_match.group(0) if phone_match else None
            name_match  = re.search(r'my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)*)',
                                    transcript, re.IGNORECASE)
            name_fallback = name_match.group(1) if name_match else None
            spoken_fallback = (
                f"Hello{' ' + name_fallback if name_fallback else ''}, "
                f"thank you for calling Blue Eye. "
                + (f"We will call you back at {cb_fallback} shortly." if cb_fallback
                   else "We have received your message and our team will respond shortly.")
            )
            return {
                "caller_name":     name_fallback,
                "intent":          "General inquiry",
                "callback_number": cb_fallback,
                "spoken_response": spoken_fallback,
            }, None

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
