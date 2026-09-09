"""
app.py — Blue Eye AI Voice & Agentic Reception Agent.

Behaviour:
- Mic tab  : greeting auto-plays → record → click "End Call & Process" → AI speaks back auto.
- Upload tab: browse & select file → processing starts AUTOMATICALLY → AI speaks back auto.
- All calls saved to SQLite with transcript + spoken_response + WhatsApp callback link.
"""
import base64
import os
import re
import sqlite3
import tempfile
import urllib.parse
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from agent import extract_call_info
from database import fetch_all_calls, init_db, insert_call
from speech_to_text import transcribe_audio
from text_to_speech import generate_voice_response

load_dotenv()

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Blue Eye — AI Voice Receptionist",
    page_icon="👁️",
    layout="wide",
)

# ── Database Initialisation ───────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"[ERROR] Database initialisation failed: {e}")
    st.stop()

# ── Helper: autoplay audio inline (no download button) ───────────────────────
def autoplay_audio(audio_bytes: bytes, fmt: str = "audio/wav") -> None:
    """Embed audio that plays automatically in the browser."""
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f"""
        <audio autoplay controls style="width:100%;border-radius:10px;margin:0.5rem 0;">
            <source src="data:{fmt};base64,{b64}" type="{fmt}">
        </audio>
        """,
        unsafe_allow_html=True,
    )


# ── Shared pipeline: process audio bytes end-to-end ──────────────────────────
def run_pipeline(audio_bytes: bytes, source_filename: str, speaker: str) -> None:
    """
    Full Blue Eye pipeline:
    1. Show caller audio
    2. Transcribe (Sarvam STT)
    3. Extract + generate reply (Sarvam LLM)
    4. Speak reply (Sarvam TTS) — AUTO-PLAY, no download
    5. Save to SQLite
    """
    st.markdown("---")
    st.markdown("### 📞 Blue Eye is Processing Your Call…")

    # Step 1 — Caller audio playback
    st.markdown("#### 🎧 Recorded Message")
    st.audio(audio_bytes)

    suffix = os.path.splitext(source_filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Step 2 — Transcription
        with st.spinner("🎙️ Transcribing with Sarvam Saaras…"):
            transcript, stt_err = transcribe_audio(tmp_path)

        if stt_err:
            st.error(stt_err)
            return

        st.markdown("#### 📝 What Blue Eye Heard:")
        st.markdown(
            f'<div class="transcript-card">"{transcript}"</div>',
            unsafe_allow_html=True,
        )

        # Step 3 — LLM extraction + response generation
        with st.spinner("🤖 Blue Eye Agent is understanding your query…"):
            info, llm_err = extract_call_info(transcript)

        if llm_err:
            st.error(llm_err)
            return

        # Step 4 — Show extracted details
        st.markdown("#### 📋 Extracted Call Details")
        c1, c2, c3 = st.columns(3)
        c1.metric("👤 Caller Name",     info.get("caller_name")     or "Not Stated")
        c2.metric("📋 Intent",          info.get("intent")          or "Not Stated")
        c3.metric("📱 Callback Number", info.get("callback_number") or "None Provided")

        # Step 5 — Generate + AUTO-PLAY reply (no download button)
        spoken_text = info.get("spoken_response") or (
            "Thank you for calling Blue Eye. "
            "We have received your message and our team will get back to you shortly."
        )

        st.markdown("---")
        st.markdown("### 🤖 Blue Eye Receptionist is Replying:")
        st.markdown(
            f'<div class="response-card">'
            f'<b>🗣️ {speaker.capitalize()} says:</b><br><br>'
            f'"{spoken_text}"'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.spinner(f"🔊 Generating voice reply ({speaker})…"):
            reply_bytes, tts_err = generate_voice_response(
                text=spoken_text, speaker=speaker
            )

        if reply_bytes:
            st.markdown("**🔊 Playing Blue Eye reply now:**")
            autoplay_audio(reply_bytes)           # ← auto-plays, no download
        else:
            st.warning(f"Voice synthesis note: {tts_err}")

        # Step 6 — Save to SQLite
        try:
            row_id = insert_call(
                caller_name=info.get("caller_name"),
                intent=info.get("intent"),
                callback_number=info.get("callback_number"),
                transcript=transcript,
                audio_filename=source_filename,
                spoken_response=spoken_text,
            )
            st.success(
                f"✅ Call saved to Blue Eye database — Record **#{row_id}**"
            )
        except sqlite3.Error as db_err:
            st.error(f"❌ Database error: {db_err}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── CSS Styling ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .blue-eye-title {
        font-size: 2.3rem; font-weight: 800;
        background: linear-gradient(135deg, #1f6feb 0%, #0d47a1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .blue-eye-subtitle { color: #586069; font-size: 1.05rem; margin-bottom: 1.2rem; }
    .status-badge {
        display: inline-block; background: #e6ffed; color: #22863a;
        padding: 4px 12px; border-radius: 20px; font-size: 0.85rem;
        font-weight: 600; border: 1px solid #34d058;
    }
    .response-card {
        background: #f0f7ff; border-left: 5px solid #1f6feb;
        padding: 1rem 1.2rem; border-radius: 8px; margin: 0.8rem 0;
    }
    .transcript-card {
        background: #fafbfc; border-left: 5px solid #6f42c1;
        padding: 1rem 1.2rem; border-radius: 8px; margin: 0.8rem 0;
    }
    .phone-btn {
        background: #25D366; color: white; border: none; padding: 6px 14px;
        border-radius: 6px; cursor: pointer; font-weight: 600;
        text-decoration: none; display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👁️ **Blue Eye Settings**")
    st.markdown('<div class="status-badge">● Receptionist Live</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 🎙️ Receptionist Voice Persona")
    speaker_choice = st.selectbox(
        "Choose Voice",
        options=["kavya", "shubh", "pooja", "kabir", "priya", "aditya"],
        format_func=lambda x: {
            "kavya":  "👩 Kavya — Warm & Professional",
            "shubh":  "👨 Shubh — Executive & Confident",
            "pooja":  "👩 Pooja — Friendly & Welcoming",
            "kabir":  "👨 Kabir — Corporate & Clear",
            "priya":  "👩 Priya — Empathetic & Polite",
            "aditya": "👨 Aditya — Deep & Calm",
        }.get(x, x),
        index=0,
    )

    st.divider()
    st.markdown("#### 📁 Sample Calls (Preview)")
    sample_files = {
        "Rahul — Course Inquiry":       "audio/rahul_call.wav",
        "Priya — Technical Support":    "audio/priya_call.wav",
        "Arjun — Product Demo Request": "audio/arjun_call.wav",
    }
    chosen_sample = st.selectbox("Select a sample", list(sample_files.keys()))
    sample_path = sample_files[chosen_sample]
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            st.audio(f.read(), format="audio/wav")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="blue-eye-title">👁️ Blue Eye — AI Voice Reception Agent</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="blue-eye-subtitle">'
    '2-Way AI Receptionist: Greets you, listens to your query, '
    'and <b>speaks back automatically</b>.'
    '</div>',
    unsafe_allow_html=True,
)

# ── API Key check ─────────────────────────────────────────────────────────────
_has_key = bool(os.getenv("SARVAM_API_KEY", "").strip())
if not _has_key:
    try:
        _has_key = bool(st.secrets.get("SARVAM_API_KEY", "").strip())
    except Exception:
        pass
if not _has_key:
    st.warning(
        "⚠️ **SARVAM_API_KEY not detected.** "
        "Add it to your `.env` file (local) or Streamlit Secrets (cloud)."
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TABS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1️⃣  Speak or Upload a Call")

tab_mic, tab_upload = st.tabs(
    ["🎙️  Live Microphone  (Speak Now)", "📁  Upload Audio File (Auto-Analyzes)"]
)

# ─── MIC TAB (unchanged — button required) ───────────────────────────────────
with tab_mic:

    GREETING_PATH = "audio/blue_eye_greeting.wav"

    # Generate greeting once if missing
    if not os.path.exists(GREETING_PATH):
        with st.spinner("🔊 Preparing Blue Eye greeting…"):
            greeting_text = (
                "Hello! Welcome to Blue Eye. "
                "Please speak clearly after this message. "
                "Tell us your name, your query, and your callback number "
                "if you would like us to reach you."
            )
            g_bytes, _ = generate_voice_response(greeting_text, speaker=speaker_choice)
            if g_bytes:
                os.makedirs("audio", exist_ok=True)
                with open(GREETING_PATH, "wb") as gf:
                    gf.write(g_bytes)

    # Auto-play greeting
    if os.path.exists(GREETING_PATH):
        with open(GREETING_PATH, "rb") as gf:
            greeting_bytes = gf.read()
        st.markdown("#### 🤖 Blue Eye is greeting you — plays automatically:")
        autoplay_audio(greeting_bytes)
        st.caption("Record your message below after the greeting.")

    st.divider()
    st.markdown("#### 🎤 Your turn — record your message:")
    mic_audio = st.audio_input(
        "Tap mic → speak → tap Stop",
        key="mic_input",
    )

    mic_bytes: Optional[bytes] = None
    if mic_audio is not None:
        mic_bytes = mic_audio.getvalue()

    process_btn = st.button(
        "🚀  End Call & Process",
        type="primary",
        disabled=(mic_bytes is None),
        key="mic_process_btn",
    )

    if process_btn and mic_bytes:
        run_pipeline(mic_bytes, "live_mic_call.wav", speaker_choice)


# ─── UPLOAD TAB (auto-analyzes the moment file is selected) ──────────────────
with tab_upload:
    st.markdown(
        "#### 📂 Browse & select your audio file — Blue Eye will analyze it automatically:"
    )

    uploaded_file = st.file_uploader(
        "Choose an audio recording (WAV, MP3, M4A, OGG, WebM…)",
        type=["wav", "mp3", "m4a", "ogg", "flac", "webm", "aac"],
        key="upload_file",
        label_visibility="collapsed",
    )

    # ← No button here. As soon as a file is selected, process immediately.
    if uploaded_file is not None:
        upload_bytes = uploaded_file.getvalue()
        upload_name  = uploaded_file.name
        st.caption(f"📎 Selected: `{upload_name}` ({len(upload_bytes)//1024} KB)")
        run_pipeline(upload_bytes, upload_name, speaker_choice)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Call Records Dashboard
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋  Blue Eye Call Records")

st.button("🔄  Refresh Logs", key="refresh_btn")

try:
    rows = fetch_all_calls()
except sqlite3.Error as e:
    st.error(f"❌ Could not read database: {e}")
    rows = []

if not rows:
    st.info("No calls stored yet. Speak or upload a recording above to get started.")
else:
    total   = len(rows)
    with_cb = sum(1 for r in rows if dict(r).get("callback_number"))
    no_cb   = total - with_cb

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📞 Total Calls",        total)
    m2.metric("📱 Callback Requested", with_cb)
    m3.metric("ℹ️  No Number",         no_cb)
    m4.metric("🏢 Organization",       "Blue Eye")

    st.markdown("")

    for row in rows:
        r        = dict(row)
        name     = r.get("caller_name")     or "Unknown Caller"
        intent   = r.get("intent")          or "General Inquiry"
        callback = r.get("callback_number")
        created  = r.get("created_at", "")
        call_id  = r.get("id")
        badge    = "📱 Callback Needed" if callback else "ℹ️ No Number"
        label    = f"#{call_id} — {name}  |  {intent}  |  {badge}  |  {created}"

        with st.expander(label):
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**👤 Caller Name:** {name}")
            col_b.markdown(f"**📋 Intent:** {intent}")
            col_c.markdown(f"**📱 Callback:** {callback or '*(None provided)*'}")

            st.markdown(f"**📁 Audio Source:** `{r.get('audio_filename') or '—'}`")
            st.markdown(f"**🕐 Logged At:** `{created}`")

            st.markdown("**📝 Call Transcript:**")
            st.info(r.get("transcript") or "(Empty)")

            spoken_reply = r.get("spoken_response")
            if spoken_reply:
                st.markdown("**🤖 Blue Eye Spoken Response:**")
                st.success(f'"{spoken_reply}"')

            # 1-click WhatsApp callback button
            if callback:
                clean_num = re.sub(r"\D", "", str(callback))
                if len(clean_num) == 10:
                    clean_num = "91" + clean_num
                msg = (
                    f"Hello {name}, this is Blue Eye following up on your call "
                    f"regarding '{intent}'. Please let us know a convenient time to connect."
                )
                wa_url = (
                    f"https://wa.me/{clean_num}?text="
                    + urllib.parse.quote(msg)
                )
                st.markdown(
                    f'<a href="{wa_url}" target="_blank">'
                    f'<span class="phone-btn">📲 WhatsApp Callback to {callback}</span>'
                    f'</a>',
                    unsafe_allow_html=True,
                )
