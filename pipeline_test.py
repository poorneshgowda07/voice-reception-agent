"""
pipeline_test.py — One-shot pipeline test for all 3 sample audio files.
Run after setting OPENAI_API_KEY in .env

Usage: python pipeline_test.py
"""
import os
import sys
import json

# Force UTF-8 output on Windows so emoji in error strings don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from database import init_db, insert_call, fetch_all_calls
from speech_to_text import transcribe_audio
from agent import extract_call_info

AUDIO_FILES = [
    "audio/rahul_call.wav",
    "audio/priya_call.wav",
    "audio/arjun_call.wav",
]

def run_pipeline():
    print("=== Voice Reception Agent -- Pipeline Test ===\n")
    init_db()

    for audio_path in AUDIO_FILES:
        filename = os.path.basename(audio_path)
        print(f"--- Processing: {filename} ---")

        # Step 1: Transcribe
        print("  [1] Transcribing...", end=" ", flush=True)
        transcript, stt_err = transcribe_audio(audio_path)
        if stt_err:
            # Strip emoji from error for safe printing
            safe_err = stt_err.encode('ascii', errors='replace').decode('ascii')
            print(f"FAILED\n  Error: {safe_err}\n")
            continue
        print("OK")
        print(f"  Transcript: {transcript[:120]}...")

        # Step 2: Extract
        print("  [2] Extracting call info...", end=" ", flush=True)
        info, llm_err = extract_call_info(transcript)
        if llm_err:
            safe_err = llm_err.encode('ascii', errors='replace').decode('ascii')
            print(f"FAILED\n  Error: {safe_err}\n")
            continue
        print("OK")
        print(f"  Extracted: {json.dumps(info, ensure_ascii=True)}")

        # Step 3: Save
        print("  [3] Saving to DB...", end=" ", flush=True)
        row_id = insert_call(
            caller_name=info.get("caller_name"),
            intent=info.get("intent"),
            callback_number=info.get("callback_number"),
            transcript=transcript,
            audio_filename=filename,
            spoken_response=info.get("spoken_response"),
        )
        print(f"OK (row_id={row_id})")
        print()

    print("\n=== All Stored Calls ===")
    rows = fetch_all_calls()
    for r in rows:
        d = dict(r)
        print(f"  [{d['id']}] {d['caller_name']} | {d['intent']} | {d['callback_number']} | {d['audio_filename']}")

if __name__ == "__main__":
    run_pipeline()
