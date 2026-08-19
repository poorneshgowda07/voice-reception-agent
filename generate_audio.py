"""
generate_audio.py — Generate 3 sample WAV files using pyttsx3 (offline TTS).

Run once:  python generate_audio.py
Produces:  audio/rahul_call.wav
           audio/priya_call.wav
           audio/arjun_call.wav
"""
import os
import sys
import subprocess

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")

# Each tuple: (filename, spoken_text)
SAMPLES = [
    (
        "rahul_call.wav",
        (
            "Hello, my name is Rahul. I'm calling to inquire about the available courses "
            "you offer. Could you please provide me with more details? "
            "My callback phone number is nine eight seven six five four three two one zero. Thank you."
        ),
    ),
    (
        "priya_call.wav",
        (
            "Hi there, this is Priya. I'm experiencing a technical issue with the software "
            "I purchased from you. The application keeps crashing whenever I try to open it. "
            "I need technical support as soon as possible. "
            "I haven't provided a callback number, so please check my account details. Thank you."
        ),
    ),
    (
        "arjun_call.wav",
        (
            "Good morning! My name is Arjun. I'm interested in scheduling a product demo "
            "for your enterprise solution. We have a team of about fifty people and would love "
            "to see how your product can help us. "
            "Please call me back at 9 1 2 3 4 5 6 7 8 9. Looking forward to hearing from you."
        ),
    ),
]

# Helper script that generates ONE file per invocation.
# We spawn it in a subprocess so that pyttsx3's COM engine reinitialises
# cleanly for each file (avoids the hang on repeated runAndWait calls).
_HELPER = """
import sys, os, pyttsx3
out_path, text = sys.argv[1], sys.argv[2]
engine = pyttsx3.init()
engine.setProperty('rate', 160)
voices = engine.getProperty('voices')
if len(voices) > 1:
    engine.setProperty('voice', voices[1].id)
engine.save_to_file(text, out_path)
engine.runAndWait()
engine.stop()
"""

def generate_wav_files() -> None:
    os.makedirs(AUDIO_DIR, exist_ok=True)

    try:
        import pyttsx3  # noqa: F401 — just verify it's installed
    except ImportError:
        print("[FAIL] pyttsx3 not installed. Run: pip install pyttsx3")
        sys.exit(1)

    for filename, text in SAMPLES:
        out_path = os.path.join(AUDIO_DIR, filename)

        # Skip if already generated
        if os.path.exists(out_path) and os.path.getsize(out_path) > 4096:
            size_kb = os.path.getsize(out_path) // 1024
            print(f"  {filename} already exists ({size_kb} KB) — skipping.")
            continue

        print(f"  Generating {filename} ...", end=" ", flush=True)

        result = subprocess.run(
            [sys.executable, "-c", _HELPER, out_path, text],
            timeout=60,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"[FAIL]\n  stderr: {result.stderr}")
        elif os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            size_kb = os.path.getsize(out_path) // 1024
            print(f"[OK]  ({size_kb} KB)")
        else:
            print("[FAIL]  File missing or empty!")

    print(f"\nAll audio files saved to: {AUDIO_DIR}")


if __name__ == "__main__":
    print("Generating sample audio files with pyttsx3 (Windows SAPI5)...\n")
    generate_wav_files()
