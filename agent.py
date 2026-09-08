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
        # when content is null/empty.
        raw = (msg.get("content") or "").strip()

        if not raw:
            # Try extracting JSON from the reasoning trace
            reasoning = (msg.get("reasoning_content") or "").strip()
            # Find JSON objects in the reasoning text (supporting multiline)
            json_candidates = re.findall(r'\{[\s\S]*?"caller_name"[\s\S]*?\}', reasoning)
            if json_candidates:
                raw = json_candidates[-1]

        if not raw:
            return {}, "[ERROR] LLM returned empty content -- try again."

        # Strip accidental markdown fences (model sometimes wraps in ```json)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        parsed = json.loads(raw)

        result = {
            "caller_name":     parsed.get("caller_name") or None,
            "intent":          parsed.get("intent") or None,
            "callback_number": parsed.get("callback_number") or None,
            "spoken_response": parsed.get("spoken_response") or None,
        }

        # Sanitize callback_number: keep digits only, regardless of how
        # the LLM formatted it (e.g. "9-8-7-6-5" -> "98765")
        if result["callback_number"]:
            digits_only = re.sub(r"\D", "", str(result["callback_number"]))
            result["callback_number"] = digits_only if digits_only else None

        # Fallback for spoken_response if LLM omitted it
        if not result["spoken_response"]:
            name = result["caller_name"] or "there"
            intent = result.get("intent") or "your inquiry"
            if result["callback_number"]:
                result["spoken_response"] = (
                    f"Hello {name}, thank you for calling Blue Eye. We have logged your request regarding {intent} "
                    f"and our team will call you back at {result['callback_number']} shortly."
                )
            else:
                result["spoken_response"] = (
                    f"Hello {name}, thank you for calling Blue Eye. We have received your message regarding {intent} "
                    f"and our team will review your account promptly."
                )

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
