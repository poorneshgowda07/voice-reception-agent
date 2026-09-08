# Voice & Agentic Reception Agent

An MVP that transcribes call recordings, extracts structured caller info using an LLM, stores everything in SQLite, and presents it in a Streamlit dashboard.

**Live App:** [voice-reception-agent.streamlit.app](https://voice-reception-agent.streamlit.app)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Speech-to-Text | Sarvam AI `saaras:v3` STT API |
| LLM Extraction | Sarvam AI `sarvam-105b` Chat API |
| Sample Audio Gen | pyttsx3 (Windows SAPI5, offline) |
| Database | SQLite via Python `sqlite3` stdlib |
| UI | Streamlit |

---

## Quick Start (Local)

```bash
pip install -r requirements.txt
```

Create a `.env` file:
```
SARVAM_API_KEY=sk_your_key_here
```

Run:
```bash
streamlit run app.py
```

---

## Cloud Deployment (Streamlit Community Cloud)

1. Fork/push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and deploy the repo
3. In the app settings, add `SARVAM_API_KEY` under **Secrets**:
   ```toml
   SARVAM_API_KEY = "sk_your_key_here"
   ```
4. The app will be live at `https://your-app.streamlit.app`

---

## Sample Audio Files

3 pre-generated WAV files in `audio/`:

| File | Caller | Intent | Callback |
|---|---|---|---|
| `rahul_call.wav` | Rahul | Course inquiry | 9876543210 |
| `priya_call.wav` | Priya | Technical support | (none) |
| `arjun_call.wav` | Arjun | Product demo | 9123456789 |

Generate fresh copies (Windows only): `python generate_audio.py`

---

## Project Structure

```
├── app.py                  # Streamlit UI
├── speech_to_text.py       # Sarvam STT transcription
├── agent.py                # Sarvam LLM JSON extraction
├── database.py             # SQLite schema + CRUD
├── generate_audio.py       # Offline TTS sample generator
├── pipeline_test.py        # End-to-end CLI test
├── audio/                  # Sample WAV files
├── sql/queries.sql         # Reference SQL queries
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing API key | Warning banner in UI, never crashes |
| Bad audio file | Error string shown, processing stops |
| Transcription failure | Error displayed in UI |
| Malformed LLM JSON | Caught and shown in UI |
| DB write error | Caught and shown in UI |
| Rate limit / timeout | Friendly message, no traceback |
