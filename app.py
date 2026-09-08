"""
app.py — Streamlit UI for the Voice & Agentic Reception Agent.

Run with:  streamlit run app.py
"""
import os
import tempfile
import sqlite3

import streamlit as st
from dotenv import load_dotenv

from database import init_db, insert_call, fetch_all_calls
from speech_to_text import transcribe_audio
from agent import extract_call_info

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Voice Reception Agent",
    page_icon="📞",
    layout="wide",
)

# ── Initialise DB on every cold start ─────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"❌ Database initialisation failed: {e}")
    st.stop()

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #1f6feb; }
    .section-header { font-size: 1.1rem; font-weight: 600; color: #444; margin-top: 1rem; }
    .status-box { padding: 0.6rem 1rem; border-radius: 6px; margin: 0.5rem 0; }
    .status-ok  { background: #e6ffed; border-left: 4px solid #28a745; }
    .status-err { background: #ffeef0; border-left: 4px solid #d73a49; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">📞 Voice &amp; Agentic Reception Agent</p>', unsafe_allow_html=True)
st.caption("Upload a call recording → auto-transcribe → extract caller info → store in database")
st.divider()

# ── API Key warning (never display the key itself) ─────────────────────────────
_has_key = bool(os.getenv("SARVAM_API_KEY", "").strip())
if not _has_key:
    try:
        _has_key = bool(st.secrets.get("SARVAM_API_KEY", "").strip())
    except Exception:
        pass
if not _has_key:
    st.warning(
        "**SARVAM_API_KEY not found.** "
        "Add it to your `.env` file (local) or Streamlit Secrets (cloud) "
        "then restart the app."
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Upload & Process
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1️⃣  Upload & Process Audio")

uploaded_file = st.file_uploader(
    "Choose an audio file (WAV, MP3, M4A, OGG…)",
    type=["wav", "mp3", "m4a", "ogg", "flac", "webm"],
    help="Supported formats: WAV, MP3, M4A, OGG, FLAC, WebM",
)

process_btn = st.button("🚀 Process Call", disabled=(uploaded_file is None))

if process_btn and uploaded_file:
    # ── Step 1: save upload to a temp file ────────────────────────────────────
    suffix = os.path.splitext(uploaded_file.name)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    st.divider()

    # ── Step 2: Transcription ─────────────────────────────────────────────────
    with st.spinner("Transcribing audio via Sarvam Saaras STT..."):
        transcript, stt_error = transcribe_audio(tmp_path)

    st.subheader("2️⃣  Transcript")
    if stt_error:
        st.error(stt_error)
        os.unlink(tmp_path)
        st.stop()
    else:
        st.markdown(
            f'<div class="status-box status-ok">✅ Transcription successful</div>',
            unsafe_allow_html=True,
        )
        st.text_area(
            "Full Transcript",
            value=transcript,
            height=150,
            key="transcript_display",
        )

    # ── Step 3: LLM Extraction ────────────────────────────────────────────────
    with st.spinner("Extracting call info via Sarvam sarvam-105b..."):
        info, llm_error = extract_call_info(transcript)

    st.subheader("3️⃣  Extracted Information")
    if llm_error:
        st.error(llm_error)
        os.unlink(tmp_path)
        st.stop()
    else:
        st.markdown(
            f'<div class="status-box status-ok">✅ Extraction successful</div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("👤 Caller Name",    info.get("caller_name")     or "—")
        col2.metric("📋 Intent",         info.get("intent")          or "—")
        col3.metric("📱 Callback Number",info.get("callback_number") or "—")

    # ── Step 4: Save to DB ────────────────────────────────────────────────────
    st.subheader("4️⃣  Database")
    try:
        row_id = insert_call(
            caller_name=info.get("caller_name"),
            intent=info.get("intent"),
            callback_number=info.get("callback_number"),
            transcript=transcript,
            audio_filename=uploaded_file.name,
        )
        st.markdown(
            f'<div class="status-box status-ok">✅ Saved to <code>calls.db</code> — row ID <strong>{row_id}</strong></div>',
            unsafe_allow_html=True,
        )
    except sqlite3.Error as e:
        st.error(f"❌ Database error while saving: {e}")
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — All Stored Calls
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋  All Stored Calls")

refresh_btn = st.button("🔄 Refresh Table")

try:
    rows = fetch_all_calls()
except sqlite3.Error as e:
    st.error(f"❌ Could not read from database: {e}")
    rows = []

if not rows:
    st.info("No calls stored yet. Upload and process an audio file above.")
else:
    st.caption(f"Total records: **{len(rows)}**")

    for row in rows:
        r = dict(row)
        # Build a human-friendly header for the expander
        name    = r.get("caller_name") or "Unknown Caller"
        intent  = r.get("intent") or "unknown intent"
        created = r.get("created_at", "")
        label   = f"🔔 #{r['id']} — {name} | {intent} | {created}"

        with st.expander(label):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**👤 Caller:** {r.get('caller_name') or '—'}")
            c2.markdown(f"**📋 Intent:** {r.get('intent') or '—'}")
            c3.markdown(f"**📱 Callback:** {r.get('callback_number') or '—'}")
            st.markdown(f"**📁 File:** `{r.get('audio_filename') or '—'}`")
            st.markdown(f"**🕐 Created:** {r.get('created_at') or '—'}")
            st.markdown("**📝 Transcript:**")
            st.text(r.get("transcript") or "(empty)")
