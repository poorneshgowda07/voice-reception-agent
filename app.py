"""
app.py — Blue Eye AI Voice & Agentic Reception Agent.

Features:
- Dual Input: Live Microphone Call (st.audio_input) OR Audio File Upload
- Sarvam STT (saaras:v3) for high-accuracy Indian-context speech transcription
- Sarvam LLM (sarvam-105b) for structured extraction + Blue Eye contextual response
- Sarvam TTS (bulbul:v3) for real-time 2-way spoken voice response
- SQLite persistent storage with caller metrics & 1-click WhatsApp callback
"""
import io
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
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar: Persona & Voice Settings ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👁️ **Blue Eye Settings**")
    st.markdown('<div class="status-badge">● Receptionist Live</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 🎙️ Receptionist Voice")
    speaker_choice = st.selectbox(
        "Choose Voice Persona",
        options=["kavya", "shubh", "pooja", "kabir", "priya", "aditya"],
        format_func=lambda x: {
            "kavya": "👩 Kavya (Warm & Professional)",
            "shubh": "👨 Shubh (Executive & Confident)",
            "pooja": "👩 Pooja (Friendly & Welcoming)",
            "kabir": "👨 Kabir (Corporate & Clear)",
            "priya": "👩 Priya (Empathetic & Polite)",
            "aditya": "👨 Aditya (Deep & Calm)",
        }.get(x, x),
        index=0,
    )

    st.divider()
    st.markdown("#### 📁 Quick-Load Sample Calls")
    sample_files = {
        "Rahul (Course Inquiry)": "audio/rahul_call.wav",
        "Priya (Technical Support)": "audio/priya_call.wav",
        "Arjun (Product Demo)": "audio/arjun_call.wav",
    }
    chosen_sample = st.selectbox("Select sample to inspect", list(sample_files.keys()))
    sample_path = sample_files[chosen_sample]
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            st.audio(f.read(), format="audio/wav")
        st.caption(f"File: `{sample_path}`")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="blue-eye-title">👁️ Blue Eye — AI Voice Reception Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="blue-eye-subtitle">2-Way Intelligent Receptionist: Listens, Transcribes, Extracts Details, and <b>Speaks Back in Voice</b>.</div>',
    unsafe_allow_html=True,
)

# ── API Key Verification ──────────────────────────────────────────────────────
_has_key = bool(os.getenv("SARVAM_API_KEY", "").strip())
if not _has_key:
    try:
        _has_key = bool(st.secrets.get("SARVAM_API_KEY", "").strip())
    except Exception:
        pass

if not _has_key:
    st.warning(
        "⚠️ **SARVAM_API_KEY not detected.** "
        "Add it to your `.env` file (local) or Streamlit Secrets (cloud) to process live voice calls."
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Talk to Blue Eye (Live Mic or Upload)
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1️⃣ Speak or Upload Call")

tab_mic, tab_upload = st.tabs(["🎙️ Speak Directly (Live Microphone)", "📁 Upload Audio File"])

audio_bytes_to_process: Optional[bytes] = None
source_filename: str = "recording.wav"

with tab_mic:
    st.markdown("**Click the microphone below to speak directly with Blue Eye Receptionist:**")
    mic_audio = st.audio_input("Record your voice message")
    if mic_audio is not None:
        audio_bytes_to_process = mic_audio.getvalue()
        source_filename = f"live_call_{mic_audio.name if hasattr(mic_audio, 'name') else 'mic.wav'}"

with tab_upload:
    uploaded_file = st.file_uploader(
        "Choose an audio recording (WAV, MP3, M4A, OGG, WebM)",
        type=["wav", "mp3", "m4a", "ogg", "flac", "webm", "aac"],
    )
    if uploaded_file is not None and audio_bytes_to_process is None:
        audio_bytes_to_process = uploaded_file.getvalue()
        source_filename = uploaded_file.name

# ── Processing Trigger ────────────────────────────────────────────────────────
can_process = audio_bytes_to_process is not None
process_btn = st.button("🚀 Process & Answer Call", type="primary", disabled=not can_process)

if process_btn and audio_bytes_to_process:
    st.divider()

    # Step A: Show Caller Audio Player
    st.markdown("#### 🎧 Caller Audio")
    st.audio(audio_bytes_to_process)

    # Step B: Write to temporary file for STT
    suffix = os.path.splitext(source_filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes_to_process)
        tmp_path = tmp.name

    try:
        # Step C: Speech-to-Text Transcription
        with st.spinner("🎙️ Transcribing speech with Sarvam Saaras..."):
            transcript, stt_err = transcribe_audio(tmp_path)

        if stt_err:
            st.error(stt_err)
            st.stop()

        # Display Transcript
        st.subheader("2️⃣ Call Transcript")
        st.markdown(
            f'<div class="transcript-card"><b>📝 What the caller said:</b><br><br>"{transcript}"</div>',
            unsafe_allow_html=True,
        )

        # Step D: LLM Extraction & Blue Eye Response Generation
        with st.spinner("🤖 Blue Eye Agent extracting information & formulating response..."):
            info, llm_err = extract_call_info(transcript)

        if llm_err:
            st.error(llm_err)
            st.stop()

        # Display Extracted Metrics
        st.subheader("3️⃣ Extracted Caller Details")
        c1, c2, c3 = st.columns(3)
        c1.metric("👤 Caller Name", info.get("caller_name") or "Not Stated")
        c2.metric("📋 Intent", info.get("intent") or "Not Stated")
        c3.metric("📱 Callback Number", info.get("callback_number") or "None Provided")

        # Step E: Blue Eye Voice Synthesis
        spoken_text = info.get("spoken_response") or (
            f"Hello, thank you for calling Blue Eye. We have received your inquiry and will reach out shortly."
        )

        st.subheader("4️⃣ 🤖 Blue Eye Voice Response")
        st.markdown(
            f'<div class="response-card"><b>🗣️ Blue Eye Spoken Reply ({speaker_choice.capitalize()}):</b><br><br>"{spoken_text}"</div>',
            unsafe_allow_html=True,
        )

        with st.spinner(f"🔊 Synthesizing Blue Eye response voice ({speaker_choice})..."):
            reply_audio_bytes, tts_err = generate_voice_response(
                text=spoken_text,
                speaker=speaker_choice,
            )

        if reply_audio_bytes:
            st.audio(reply_audio_bytes, format="audio/wav")
            st.download_button(
                label="📥 Download Blue Eye Voice Response (.wav)",
                data=reply_audio_bytes,
                file_name=f"blue_eye_reply_{info.get('caller_name') or 'call'}.wav",
                mime="audio/wav",
            )
        elif tts_err:
            st.info(f"Spoken text generated. Voice audio warning: {tts_err}")

        # Step F: Persist into SQLite Database
        try:
            row_id = insert_call(
                caller_name=info.get("caller_name"),
                intent=info.get("intent"),
                callback_number=info.get("callback_number"),
                transcript=transcript,
                audio_filename=source_filename,
                spoken_response=spoken_text,
            )
            st.success(f"✅ Call record successfully saved to `calls.db` (Record ID: #{row_id})")
        except sqlite3.Error as db_err:
            st.error(f"[ERROR] Database save error: {db_err}")

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — All Stored Calls (CRM & Dispatch)
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📋 All Stored Calls (Blue Eye Records)")

col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    refresh_btn = st.button("🔄 Refresh Logs")

try:
    rows = fetch_all_calls()
except sqlite3.Error as e:
    st.error(f"❌ Could not read calls database: {e}")
    rows = []

if not rows:
    st.info("No calls stored yet. Speak or upload a call recording above to get started.")
else:
    # Summary KPI metrics
    total_calls = len(rows)
    calls_with_number = sum(1 for r in rows if dict(r).get("callback_number"))

    m1, m2, m3 = st.columns(3)
    m1.metric("📞 Total Processed Calls", total_calls)
    m2.metric("📱 Callbacks Required", calls_with_number)
    m3.metric("🏢 Organization", "Blue Eye")

    st.write("")

    for row in rows:
        r = dict(row)
        name = r.get("caller_name") or "Unknown Caller"
        intent = r.get("intent") or "General Inquiry"
        callback = r.get("callback_number")
        created = r.get("created_at", "")
        call_id = r.get("id")

        badge = "📱 Callback Needed" if callback else "ℹ️ No Number"
        label = f"#{call_id} — {name} | {intent} | {badge} | {created}"

        with st.expander(label):
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**👤 Caller Name:** {name}")
            col_b.markdown(f"**📋 Intent:** {intent}")
            col_c.markdown(f"**📱 Callback Number:** {callback or '*(None provided)*'}")

            st.markdown(f"**📁 Audio Source:** `{r.get('audio_filename') or 'recording.wav'}`")
            st.markdown(f"**🕐 Logged At:** `{created}`")

            st.markdown("**📝 Call Transcript:**")
            st.info(r.get("transcript") or "(Empty transcript)")

            # Show spoken response if recorded
            spoken_reply = r.get("spoken_response")
            if spoken_reply:
                st.markdown("**🤖 Blue Eye Spoken Response:**")
                st.success(f'"{spoken_reply}"')

            # 1-Click WhatsApp callback shortcut if phone number available
            if callback:
                clean_num = re.sub(r"\D", "", str(callback))
                # If 10-digit Indian number, prefix with country code 91
                if len(clean_num) == 10:
                    clean_num = "91" + clean_num
                msg = f"Hello {name}, this is Blue Eye following up on your call regarding '{intent}'."
                encoded_msg = urllib.parse.quote(msg)
                wa_url = f"https://wa.me/{clean_num}?text={encoded_msg}"
                st.markdown(
                    f'<a href="{wa_url}" target="_blank" style="text-decoration:none;">'
                    f'<button style="background:#25D366; color:white; border:none; padding:6px 14px; border-radius:6px; cursor:pointer; font-weight:600;">'
                    f'📲 Open WhatsApp Callback to {callback}'
                    f'</button></a>',
                    unsafe_allow_html=True,
                )
