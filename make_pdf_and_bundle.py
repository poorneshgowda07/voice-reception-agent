import os
import shutil
import zipfile
from fpdf import FPDF

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop")
if not os.path.exists(DESKTOP_DIR):
    DESKTOP_DIR = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")

PDF_FILENAME = "Blue_Eye_AI_Receptionist_Interview_Guide.pdf"
ZIP_FILENAME = "Blue_Eye_Voice_Reception_Agent_Complete.zip"

OUTPUT_PDF_PATH = os.path.join(DESKTOP_DIR, PDF_FILENAME)
OUTPUT_ZIP_PATH = os.path.join(DESKTOP_DIR, ZIP_FILENAME)

class PDFGuide(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Blue Eye - AI Voice Reception Agent | Interview Guide & Documentation", 0, 1, "R")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", 0, 0, "C")

def generate_pdf():
    pdf = PDFGuide()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title Banner
    pdf.set_fill_color(31, 111, 235)
    pdf.rect(10, 18, 190, 24, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(10, 21)
    pdf.cell(190, 10, "Blue Eye - AI Voice Reception Agent", 0, 1, "C")
    pdf.set_font("Helvetica", "I", 11)
    pdf.cell(190, 7, "Comprehensive System Architecture & Technical Interview Guide", 0, 1, "C")
    pdf.ln(10)

    def chapter_title(title):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(31, 111, 235)
        pdf.cell(0, 8, title, 0, 1, "L")
        pdf.set_draw_color(31, 111, 235)
        pdf.set_line_width(0.5)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
        pdf.ln(3)

    def body_text(text, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5.5, text)
        pdf.ln(2)

    def bullet(title, desc):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(6, 5, chr(149), 0, 0)
        pdf.cell(45, 5, title + ":", 0, 0)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 5, desc)
        pdf.ln(1)

    # Section 1
    chapter_title("1. Executive Summary & Core Value Proposition")
    body_text(
        "Blue Eye is a full-stack, two-way conversational AI Voice Receptionist application. "
        "It acts as a 24/7 intelligent front-desk agent that greets incoming callers, transcribes spoken queries, "
        "accurately extracts key details (caller name, caller intent, callback phone number), "
        "persists the conversation in a structured SQLite database with Indian Standard Time (IST) timestamps, "
        "and synthesizes an immediate, personalized audio response that automatically plays back in the caller's browser."
    )
    pdf.ln(2)

    # Section 2
    chapter_title("2. Key Architectural Components")
    bullet("Frontend / UI Layer", "Streamlit web application (app.py) providing live microphone recording (st.audio_input), audio file browsing, audio playback, metrics, and call logs.")
    bullet("Speech-to-Text (STT)", "Sarvam AI Saaras v3 model - highly tuned for Indian accents and multilingual nuances; converts audio to verbatim text.")
    bullet("Agent Reasoning (LLM)", "Sarvam AI sarvam-105b Chat Completions API with 3-tier fallback architecture to extract structured JSON (caller_name, intent, callback_number, spoken_response).")
    bullet("Text-to-Speech (TTS)", "Sarvam AI Bulbul v3 model - converts the generated receptionist script into high-fidelity, natural Indian voice audio.")
    bullet("Database Layer", "SQLite relational database (calls.db via database.py) with automated column migration, indexing, and IST timestamping.")
    bullet("One-Click Launcher", "start_blue_eye.bat Windows launcher paired with a Desktop shortcut for instant startup without terminal commands.")
    pdf.ln(3)

    # Section 3
    chapter_title("3. End-to-End System Workflow")
    body_text("1. Caller Initiation: Caller either clicks the live microphone or uploads an audio file.")
    body_text("2. Auto Greeting: Blue Eye automatically plays a professional welcome greeting prompting for details.")
    body_text("3. STT Transcription: Audio bytes are transmitted to Sarvam Saaras v3, generating verbatim English text.")
    body_text("4. LLM Extraction: Prompt engineering guides sarvam-105b to extract exact details with strict zero-hallucination rules.")
    body_text("5. Audio Synthesis: The receptionist's personalized reply is synthesized into WAV bytes via Bulbul v3.")
    body_text("6. Autoplay Response: Browser automatically plays the agent's voice response using embedded HTML5 audio.")
    body_text("7. Database Persistence: All records are saved to calls.db, populating the live CRM table with 1-click WhatsApp callbacks.")
    pdf.ln(3)

    # Section 4
    chapter_title("4. Project Directory & File Layout")
    bullet("app.py", "Streamlit UI application, handling audio inputs, state, autoplay, and CRM records.")
    bullet("agent.py", "LLM prompt design, JSON parser, and 3-layer resilient fallback engine.")
    bullet("speech_to_text.py", "REST client integration for Sarvam Saaras v3 STT.")
    bullet("text_to_speech.py", "REST client integration for Sarvam Bulbul v3 TTS with persona support.")
    bullet("database.py", "SQLite schema initialisation, migration, and CRUD queries.")
    bullet("generate_audio.py", "Offline utility for generating pre-recorded sample call scenarios.")
    bullet("pipeline_test.py", "End-to-end CLI integration test script verifying all 3 call scenarios.")
    bullet("start_blue_eye.bat", "Automated port-checking and browser launch script.")
    bullet("audio/", "Directory holding sample WAV files (Rahul, Priya, Arjun) and initial greetings.")
    bullet("calls.db", "Embedded SQLite storage containing logged call history.")
    pdf.ln(3)

    # Section 5
    chapter_title("5. Critical Engineering Challenges & Solutions")
    body_text("Challenge 1: LLM Truncated / Reasoning-Only Outputs", bold=True)
    body_text(
        "Reasoning models like sarvam-105b sometimes return output inside 'reasoning_content' rather than 'content', "
        "or get cut off mid-stream. We engineered a 3-layer recovery mechanism: first parsing content, then falling back "
        "to searching reasoning traces for valid JSON, and finally running keyword/regex heuristics to guarantee zero UI crashes."
    )
    body_text("Challenge 2: Seamless Autoplay Without Manual Downloads", bold=True)
    body_text(
        "Standard audio elements require manual user clicks or downloading. We solved this by generating Base64-encoded "
        "audio embedded directly into an HTML5 <audio autoplay> tag, delivering a natural phone call experience."
    )
    body_text("Challenge 3: Accurate Timezone Handling", bold=True)
    body_text(
        "Server defaults stored UTC timestamps, causing confusion for local office staff. We explicitly configured "
        "datetime.now(timezone(timedelta(hours=5, minutes=30))) to ensure exact Indian Standard Time (IST) logging."
    )
    pdf.ln(3)

    # Section 6
    chapter_title("6. High-Frequency Technical Interview Questions")
    
    questions = [
        ("Q1: Walk me through the architecture of your Voice Receptionist.",
         "Answer: It follows an event-driven 5-stage pipeline: Audio Capture (Streamlit) -> STT (Sarvam Saaras v3) -> "
         "Information Extraction & Agent Reasoning (Sarvam 105B) -> Voice Synthesis (Sarvam Bulbul v3) -> "
         "Relational Storage (SQLite). The system is fully decoupled into modular Python services."),
        
        ("Q2: Why did you pick Sarvam AI instead of OpenAI Whisper/GPT-4?",
         "Answer: Sarvam AI is specifically trained and optimized for Indian accents, speech cadences, and code-mixed vocabulary. "
         "During testing, phone numbers spoken with Indian accents were captured with far higher fidelity, and it provides an integrated "
         "suite covering STT, Chat LLM, and TTS with Indian personas (e.g. Kavya, Shubh)."),
         
        ("Q3: How do you prevent LLM hallucinations on extracted phone numbers or names?",
         "Answer: In agent.py, we implement strict zero-shot system prompts instructing the model to assign 'null' if data is absent. "
         "Furthermore, we sanitize callback numbers using regex (r'\\D') and cross-verify with phone number patterns (10 digits starting 6-9)."),
         
        ("Q4: How does this project scale to handle thousands of concurrent calls in enterprise?",
         "Answer: In production: 1) Replace SQLite with PostgreSQL or managed cloud SQL. 2) Use Sarvam's Streaming/WebSocket or Batch APIs. "
         "3) Integrate Twilio/SIP telephony webhooks instead of browser mic. 4) Run the backend services inside containerized Docker/Kubernetes pods.")
    ]

    for q, a in questions:
        body_text(q, bold=True)
        body_text(a)
        pdf.ln(1)

    pdf.output(OUTPUT_PDF_PATH)
    print(f"[OK] Generated PDF at: {OUTPUT_PDF_PATH}")
    # Also save inside project directory
    local_pdf = os.path.join(PROJECT_DIR, PDF_FILENAME)
    pdf.output(local_pdf)
    print(f"[OK] Saved local PDF at: {local_pdf}")

def create_bundle_zip():
    print(f"Creating complete project archive: {OUTPUT_ZIP_PATH}...")
    # List of files to include
    include_extensions = {".py", ".bat", ".md", ".txt", ".sql", ".example", ".wav", ".db", ".pdf"}
    
    with zipfile.ZipFile(OUTPUT_ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # Exclude git internal folder and pycache
            if ".git" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith((".pyc", ".tmp")):
                    continue
                # Never bundle active private .env file for security, but include .env.example
                if file == ".env":
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, PROJECT_DIR)
                zipf.write(file_path, os.path.join("Blue_Eye_Voice_Reception_Agent", rel_path))
    print(f"[OK] Project zip archive created at: {OUTPUT_ZIP_PATH}")

if __name__ == "__main__":
    generate_pdf()
    create_bundle_zip()
