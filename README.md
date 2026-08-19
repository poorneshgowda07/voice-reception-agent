# 📞 Voice & Agentic Reception Agent

An MVP that transcribes call recordings, extracts structured caller info using an LLM, stores everything in SQLite, and presents it in a Streamlit dashboard.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Speech-to-Text | OpenAI Whisper API (`whisper-1`) |
| LLM Extraction | OpenAI GPT-4o-mini |
| Sample Audio Gen | pyttsx3 (Windows SAPI5, fully offline) |
| Database | SQLite via Python `sqlite3` stdlib |
| UI | Streamlit |

> **Why Whisper API instead of local whisper?**  
> `ffmpeg` is not installed on the target machine (required by local `openai-whisper` for audio decoding). The Whisper API achieves identical quality with only the `openai` pip package and zero system dependencies.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your API key
```bash
copy .env.example .env
```
Edit `.env` and replace `your_api_key_here` with your real OpenAI API key.

```
OPENAI_API_KEY=sk-...
```

### 3. Generate sample audio files (one-time)
```bash
python generate_audio.py
```
This creates `audio/rahul_call.wav`, `audio/priya_call.wav`, `audio/arjun_call.wav` using offline Windows TTS.

### 4. Run the app
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Demo Sequence

1. Run `python generate_audio.py` to create sample audio files.
2. Launch: `streamlit run app.py`
3. Upload `audio/rahul_call.wav` → click **Process Call** → verify transcript & extracted fields.
4. Repeat for `priya_call.wav` (no callback number expected) and `arjun_call.wav`.
5. Scroll down to see the **All Stored Calls** table with expandable transcripts.
6. Restart the app (`Ctrl+C` → `streamlit run app.py`) — records persist in `calls.db`.
7. Run SQL queries: `sqlite3 calls.db ".read sql/queries.sql"`

---

## Project Structure

```
├── audio/                  # Generated sample WAV files
│   ├── rahul_call.wav
│   ├── priya_call.wav
│   └── arjun_call.wav
├── sql/
│   └── queries.sql         # SELECT *, column-subset, COUNT(*)
├── app.py                  # Streamlit UI
├── database.py             # SQLite schema + CRUD
├── speech_to_text.py       # Whisper API transcription
├── agent.py                # GPT-4o-mini JSON extraction
├── generate_audio.py       # Offline TTS sample generator
├── calls.db                # SQLite database (auto-created)
├── requirements.txt
├── .env.example
├── .env                    # ← YOUR KEY GOES HERE (never committed)
└── .gitignore
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API key | Clear warning banner in UI, never crashes |
| Bad audio file | STT returns error string, displayed in UI |
| Transcription failure | Error shown, processing stops gracefully |
| Malformed LLM JSON | Caught by `json.JSONDecodeError`, shown in UI |
| DB write error | `sqlite3.Error` caught, shown in UI |
| Rate limit / quota | Friendly message shown, no traceback |
