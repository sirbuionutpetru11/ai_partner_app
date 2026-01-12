import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF  # fpdf2
from openai import OpenAI


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Buna inteligenta artificiala, dar mai buna iubirea umana",
    page_icon="🤖",
    layout="wide",
)

APP_TITLE = "🤖 Buna inteligenta artificiala, dar mai buna iubirea umana"


# =============================================================================
# ACCESS CONTROL
# =============================================================================
def check_password() -> bool:
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.title("🔐 Robotu' nostru - Access Required")
    pwd = st.text_input("Enter Passcode", type="password")

    if st.button("Unlock"):
        if pwd == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Incorrect password")

    st.stop()


# =============================================================================
# PDF EXPORT (FPDF2 SAFE)
# =============================================================================
def create_pdf(messages: list[dict]) -> bytes:
    def safe_text(text: str) -> str:
        if not text:
            return ""
        return text.replace("\u0000", "")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    if Path(font_regular).exists():
        pdf.add_font("DejaVu", "", font_regular)
        pdf.add_font("DejaVu", "B", font_bold)
        family = "DejaVu"
    else:
        family = "Helvetica"

    pdf.set_font(family, "B", 16)
    pdf.cell(0, 10, "Robotu' nostru - Chat Transcript", new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font(family, "", 10)
    pdf.cell(
        0,
        8,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(5)

    for m in messages:
        if m["role"] in ("system", "developer"):
            continue

        role = "User" if m["role"] == "user" else "Assistant"

        pdf.set_font(family, "B", 12)
        pdf.cell(0, 8, f"{role}:", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font(family, "", 11)
        pdf.multi_cell(0, 6, safe_text(m.get("content", "")))
        pdf.ln(3)

    return pdf.output(dest="S")


# =============================================================================
# HISTORY
# =============================================================================
HISTORY_DIR = Path.home() / ".ai_partner_history"
HISTORY_FILE = HISTORY_DIR / "chat_history.json"
MAX_CHATS = 50


def _storage_ok() -> bool:
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        test = HISTORY_DIR / ".test"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return True
    except Exception:
        return False


def load_history() -> list[dict]:
    if not _storage_ok() or not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_history(history: list[dict]) -> None:
    if not _storage_ok():
        return
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def upsert_chat():
    msgs = st.session_state.messages
    if len(msgs) <= 1:
        return

    data = {
        "id": st.session_state.chat_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "preview": msgs[1]["content"][:50],
        "messages": msgs,
        "mode": st.session_state.current_mode,
    }

    history = st.session_state.chat_history
    for i, h in enumerate(history):
        if h["id"] == data["id"]:
            history[i] = data
            break
    else:
        history.insert(0, data)

    st.session_state.chat_history = history[:MAX_CHATS]
    save_history(st.session_state.chat_history)


def load_chat(index: int):
    chat = st.session_state.chat_history[index]
    st.session_state.chat_id = chat["id"]
    st.session_state.messages = chat["messages"]
    st.session_state.current_mode = chat.get("mode", st.session_state.current_mode)


def new_chat():
    dev = st.session_state.messages[0]
    st.session_state.chat_id = f"chat_{datetime.now().timestamp()}"
    st.session_state.messages = [dev]


# =============================================================================
# MODELS
# =============================================================================
MODEL_CONFIGS = {
    "📚 Bombonica studentica": {
        "model": "gpt-5-mini",
        "temperature": 1.0,
    },
    "⚡ Bun la tat": {
        "model": "gpt-5",
        "temperature": 1.0,
    },
    "💻 Iubirelu' programelu'": {
        "model": "gpt-5.2",
        "temperature": 1.0,
    },
}


# =============================================================================
# SESSION INIT
# =============================================================================
def init_state():
    if "client" not in st.session_state:
        st.session_state.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    if "current_mode" not in st.session_state:
        st.session_state.current_mode = "📚 Bombonica studentica"

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "developer",
                "content": (
                    "You are an advanced AI assistant. "
                    "Be concise, correct, and helpful."
                ),
            }
        ]

    if "chat_id" not in st.session_state:
        st.session_state.chat_id = f"chat_{datetime.now().timestamp()}"

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_history()


# =============================================================================
# STREAMING
# =============================================================================
def stream_reply(messages, model, temperature):
    stream = st.session_state.client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    out = ""
    placeholder = st.empty()

    for event in stream:
        delta = event.choices[0].delta.content or ""
        if delta:
            out += delta
            placeholder.markdown(out)

    return out.strip()


# =============================================================================
# APP
# =============================================================================
if check_password():
    init_state()

    with st.sidebar:
        st.subheader("🎛️ Model")
        mode = st.radio(
            "Select mode",
            list(MODEL_CONFIGS.keys()),
            index=list(MODEL_CONFIGS.keys()).index(st.session_state.current_mode),
        )
        st.session_state.current_mode = mode

        if st.button("➕ New Chat"):
            upsert_chat()
            new_chat()
            st.rerun()

        if st.session_state.chat_history:
            st.divider()
            for i, chat in enumerate(st.session_state.chat_history):
                if st.button(chat["preview"], key=f"h{i}"):
                    load_chat(i)
                    st.rerun()

        if len(st.session_state.messages) > 1:
            pdf = create_pdf(st.session_state.messages)
            st.download_button(
                "📄 Save PDF",
                pdf,
                "chat.pdf",
                "application/pdf",
            )

    st.title(APP_TITLE)

    for m in st.session_state.messages:
        if m["role"] in ("system", "developer"):
            continue
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Ask me anything…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        cfg = MODEL_CONFIGS[st.session_state.current_mode]
        with st.chat_message("assistant"):
            reply = stream_reply(
                st.session_state.messages,
                cfg["model"],
                cfg["temperature"],
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": reply}
            )
            upsert_chat()
