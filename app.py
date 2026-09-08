"""
app.py — Blue Eye AI Voice & Agentic Reception Agent.

Behaviour:
- Mic tab opens → Blue Eye greeting plays AUTOMATICALLY (no click needed)
- User records → clicks End → AI processes → AI reply plays AUTOMATICALLY
- Upload tab → same auto-play reply flow
- All calls saved to SQLite with transcript + spoken_response
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

# ── Helper: autoplay audio inline (no download, no controls needed) ───────────
def autoplay_audio(audio_bytes: bytes, fmt: str = "audio/wav") -> None:
    """Embed audio that plays automatically without any visible download link."""
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f"""
        <audio autoplay style="width:100%;border-radius:10px;margin:0.5rem 0;">
            <source src="data:{fmt};base64,{b64}" type="{fmt}">
        </audio>
        """,
        unsafe_allow_html=True,
    )


# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .blue-eye-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1f6feb 0%, #0d47a1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .blue-eye-subtitle {
        color: #586069;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }
    .status-badge {
        display: inline-block;
        background: #e6ffed;
        color: #22863a;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #34d058;
    }
    .response-card {
        background: #f0f7ff;
        border-left: 5px solid #1f6feb;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 0.8rem 0;
    }
    .transcript-card {
        background: #fafbfc;
        border-left: 5px solid #6f42c1;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin: 0.8rem 0;
    }
    .phone-btn {
        background: #25D366;
        color: white;
        border: none;
        padding: 6px 14px;
        border-radius: 6px;
        cursor: pointer;
        font-weight: 600;
        text-decoration: none;
        display: inline-block;
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
            "kavya": "👩 Kavya — Warm & Professional",
            "shubh": "👨 Shubh — Executive & Confident",
            "pooja": "👩 Pooja — Friendly & Welcoming",
            "kabir": "👨 Kabir — Corporate & Clear",
            "priya": "👩 Priya — Empathetic & Polite",
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
    '<div class="blue-eye-subtitle">2-Way AI Receptionist: '
    'Greets you instantly, listens to your query, and <b>speaks back in voice</b> automatically.</div>',
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
# SECTION 1 — Speak or Upload
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1️⃣  Speak or Upload a Call")

tab_mic, tab_upload = st.tabs(
    ["🎙️  Live Microphone  (Speak Now)", "📁  Upload Audio File"]
)

audio_bytes_to_process: Optional[bytes] = None
source_filename: str = "recording.wav"

# ─── MICROPHONE TAB ──────────────────────────────────────────────────────────
with tab_mic:

    # ── Auto-play greeting as soon as mic tab is visible ──────────────────────
    GREETING_PATH = "audio/blue_eye_greeting.wav"

    # Generate greeting file if missing (runs once, ~3 seconds)
    if not os.path.exists(GREETING_PATH):
        with st.spinner("🔊 Blue Eye Receptionist is getting ready..."):
            greeting_text = (
                "Hello! Welcome to Blue Eye. "
                "Please speak clearly after this message. "
                "Tell us your name, your query, and your callback number if you'd like us to reach you."
            )
            g_bytes, g_err = generate_voice_response(greeting_text, speaker=speaker_choice)
            if g_bytes:
                os.makedirs("audio", exist_ok=True)
                with open(GREETING_PATH, "wb") as f:
                    f.write(g_bytes)

    # Play greeting automatically — no controls, no download
    if os.path.exists(GREETING_PATH):
        with open(GREETING_PATH, "rb") as f:
            greeting_bytes = f.read()
        st.markdown(
            "#### 🤖 Blue Eye Receptionist is ready — greeting is playing automatically:"
        )
        autoplay_audio(greeting_bytes)
        st.caption("👆 Blue Eye is greeting you. Record your message below when ready.")

    st.divider()
    st.markdown("#### 🎤 Your turn — record your message:")
    mic_audio = st.audio_input(
        "Tap the mic, speak your query, then tap Stop",
        key="mic_input",
    )
    if mic_audio is not None:
        audio_bytes_to_process = mic_audio.getvalue()
        source_filename = "live_mic_call.wav"

# ─── UPLOAD TAB ──────────────────────────────────────────────────────────────
with tab_upload:
    uploaded_file = st.file_uploader(
        "Choose an audio recording (WAV, MP3, M4A, OGG, WebM…)",
        type=["wav", "mp3", "m4a", "ogg", "flac", "webm", "aac"],
    )
    if uploaded_file is not None and audio_bytes_to_process is None:
        audio_bytes_to_process = uploaded_file.getvalue()
        source_filename = uploaded_file.name

# ── Process button ────────────────────────────────────────────────────────────
can_process = audio_bytes_to_process is not None
process_btn = st.button(
    "🚀  End Call & Process",
    type="primary",
    disabled=not can_process,
    help="Click after you've recorded or uploaded to start Blue Eye's analysis.",
)

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
if process_btn and audio_bytes_to_process:
    st.divider()
    st.markdown("---")
    st.markdown("### 📞 Call in Progress — Blue Eye is Processing...")

    # ── Step 1: Show the caller's own audio (standard player, no autoplay) ───
    st.markdown("#### 🎧 Your Recorded Message")
    st.audio(audio_bytes_to_process)

    # Save to temp file for STT
    suffix = os.path.splitext(source_filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes_to_process)
        tmp_path = tmp.name

    try:
        # ── Step 2: Transcription ─────────────────────────────────────────────
        with st.spinner("🎙️  Transcribing your speech with Sarvam Saaras…"):
            transcript, stt_err = transcribe_audio(tmp_path)

        if stt_err:
            st.error(stt_err)
            st.stop()

        st.markdown("#### 📝 What Blue Eye Heard:")
        st.markdown(
            f'<div class="transcript-card">"{transcript}"</div>',
            unsafe_allow_html=True,
        )

        # ── Step 3: LLM extraction + response generation ──────────────────────
        with st.spinner("🤖  Blue Eye Agent is understanding your query and preparing a reply…"):
            info, llm_err = extract_call_info(transcript)

        if llm_err:
            st.error(llm_err)
            st.stop()

        # ── Step 4: Show extracted caller details ─────────────────────────────
        st.markdown("#### 📋 Extracted Call Details")
        c1, c2, c3 = st.columns(3)
        c1.metric("👤 Caller Name",       info.get("caller_name")     or "Not Stated")
        c2.metric("📋 Intent",            info.get("intent")          or "Not Stated")
        c3.metric("📱 Callback Number",   info.get("callback_number") or "None Provided")

        # ── Step 5: Auto-play Blue Eye voice reply ────────────────────────────
        spoken_text = info.get("spoken_response") or (
            "Thank you for calling Blue Eye. "
            "We have received your message and our team will get back to you shortly."
        )

        st.markdown("---")
        st.markdown("### 🤖 Blue Eye Receptionist is Replying Now:")
        st.markdown(
            f'<div class="response-card">'
            f'<b>🗣️ {speaker_choice.capitalize()} (Blue Eye) says:</b><br><br>'
            f'"{spoken_text}"'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.spinner(f"🔊  Generating Blue Eye voice ({speaker_choice})…"):
            reply_bytes, tts_err = generate_voice_response(
                text=spoken_text,
                speaker=speaker_choice,
            )

        if reply_bytes:
            # Auto-play immediately — no download, no controls to click
            st.markdown("**🔊 Blue Eye is speaking now:**")
            autoplay_audio(reply_bytes)
        else:
            st.info(f"Voice note: {tts_err}")

        # ── Step 6: Persist call to SQLite ────────────────────────────────────
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
                f"✅ Call successfully logged to Blue Eye database — Record **#{row_id}**"
            )
        except sqlite3.Error as db_err:
            st.error(f"❌ Database error: {db_err}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — All Stored Calls Dashboard
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋  Blue Eye Call Records")

st.button("🔄  Refresh Logs")  # triggers rerun

try:
    rows = fetch_all_calls()
except sqlite3.Error as e:
    st.error(f"❌ Could not read database: {e}")
    rows = []

if not rows:
    st.info("No calls stored yet. Speak or upload a call recording above to get started.")
else:
    total = len(rows)
    with_cb = sum(1 for r in rows if dict(r).get("callback_number"))
    no_cb   = total - with_cb

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📞 Total Calls",         total)
    m2.metric("📱 Callback Requested",  with_cb)
    m3.metric("ℹ️  No Number",          no_cb)
    m4.metric("🏢 Organization",        "Blue Eye")

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

            # ── WhatsApp 1-click callback button ──────────────────────────────
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
