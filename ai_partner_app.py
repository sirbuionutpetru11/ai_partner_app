import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from fpdf import FPDF
from openai import OpenAI


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Buna inteligenta artificala, dar mai buna iubirea umana",
    page_icon="🤖",
    layout="wide",
)

APP_TITLE = "🤖 Buna inteligenta artificala, dar mai buna iubirea umana"


# =============================================================================
# ACCESS CONTROL
# =============================================================================
def check_password() -> bool:
    """Simple password gate to protect API credits."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.title("🔐 Robotu' nostru - Access Required")
    pwd = st.text_input("Enter Passcode", type="password", key="password_input")

    if st.button("Unlock"):
        if pwd == st.secrets.get("APP_PASSWORD", ""):
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Incorrect password. Please try again.")

    st.stop()
    return False


# =============================================================================
# PDF EXPORT
# =============================================================================
def create_pdf(messages: list[dict]) -> bytes:
    """Generate a PDF transcript of the chat conversation."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Streamlit Cloud may not have system fonts; try DejaVu, then fallback.
    font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if Path(font_regular).exists() and Path(font_bold).exists():
        pdf.add_font("DejaVu", "", font_regular, uni=True)
        pdf.add_font("DejaVu", "B", font_bold, uni=True)
        family = "DejaVu"
    else:
        # Fallback: built-in core font (no full unicode)
        family = "Helvetica"

    pdf.set_font(family, "B", 16)
    pdf.cell(0, 10, "Robotu' nostru - Chat Transcript", ln=True, align="C")
    pdf.set_font(family, "", 10)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(5)

    for m in messages:
        if m["role"] in ("system", "developer"):
            continue

        pdf.set_font(family, "B", 12)
        role = "User" if m["role"] == "user" else "Assistant"
        pdf.cell(0, 8, f"{role}:", ln=True)

        pdf.set_font(family, "", 11)
        content = m.get("content", "")
        try:
            pdf.multi_cell(0, 6, content)
        except Exception:
            clean = content.encode("ascii", "ignore").decode("ascii")
            pdf.multi_cell(0, 6, clean)
        pdf.ln(3)

    # FPDF returns `str` when dest='S' in some versions; convert to bytes safely
    out = pdf.output(dest="S")
    return out.encode("latin-1", errors="ignore") if isinstance(out, str) else out


# =============================================================================
# HISTORY (STREAMLIT-DEPLOYMENT FRIENDLY)
# =============================================================================
# IMPORTANT: On Streamlit Cloud / multi-replica deployments, writing to disk is not
# a reliable “persistent database”. Use st.secrets + external storage for persistence.
# This refactor makes history seamless per-user session, and *optionally* attempts
# disk persistence when available.

HISTORY_DIR = Path.home() / ".ai_partner_history"
HISTORY_FILE = HISTORY_DIR / "chat_history.json"
MAX_CHATS = 50


def _history_storage_available() -> bool:
    """Best-effort check: local disk may be ephemeral or read-only in deployment."""
    try:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        # Touch a temp file to test writability
        test_file = HISTORY_DIR / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def load_chat_history_from_disk() -> list[dict]:
    if not _history_storage_available():
        return []
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_chat_history_to_disk(history: list[dict]) -> None:
    if not _history_storage_available():
        return
    try:
        HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        # Don't break the app because persistence isn't available.
        pass


def _chat_preview(messages: list[dict]) -> str:
    for msg in messages:
        if msg["role"] == "user":
            c = msg.get("content", "").strip()
            return (c[:50] + "...") if len(c) > 50 else (c or "New Chat")
    return "New Chat"


def upsert_current_chat_to_history() -> None:
    """Save/Update current session chat into st.session_state.chat_history (and disk if possible)."""
    msgs = st.session_state.messages
    if len(msgs) <= 1:
        return

    chat_data = {
        "id": st.session_state.chat_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "preview": _chat_preview(msgs),
        "messages": msgs,
        "mode": st.session_state.current_mode,
    }

    history: list[dict] = st.session_state.chat_history

    # Upsert by stable chat_id (fixes duplicates / “similar length” heuristics issues)
    for i, existing in enumerate(history):
        if existing.get("id") == st.session_state.chat_id:
            history[i] = chat_data
            break
    else:
        history.insert(0, chat_data)

    st.session_state.chat_history = history[:MAX_CHATS]
    save_chat_history_to_disk(st.session_state.chat_history)


def load_chat_from_history(index: int) -> None:
    history = st.session_state.chat_history
    if 0 <= index < len(history):
        chat = history[index]
        st.session_state.chat_id = chat.get("id") or f"chat_{datetime.now().timestamp()}"
        st.session_state.messages = chat["messages"]
        st.session_state.current_mode = chat.get("mode", st.session_state.current_mode)


def delete_chat_from_history(index: int) -> None:
    history = st.session_state.chat_history
    if 0 <= index < len(history):
        history.pop(index)
        st.session_state.chat_history = history
        save_chat_history_to_disk(history)


def new_chat() -> None:
    """Start a new chat while preserving the developer message."""
    dev = st.session_state.messages[0]
    st.session_state.chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    st.session_state.messages = [dev]


# =============================================================================
# MODEL CONFIGS
# =============================================================================
MODEL_CONFIGS = {
    "💻 Iubirelu' programelu'": {
        "model": "gpt-5.2",
        "description": "Deep reasoning for complex coding & analysis",
        "temperature": 1.0,
        "supports_streaming": True,
    },
    "⚡ Bun la tat": {
        "model": "gpt-5",
        "description": "Balanced intelligence for everyday tasks",
        "temperature": 1.0,
        "supports_streaming": True,
    },
    "📚 Bombonica studentica": {
        "model": "gpt-5-mini",
        "description": "Fast & affordable for quick corrections",
        "temperature": 1.0,
        "supports_streaming": True,
    },
}


# =============================================================================
# SESSION INITIALIZATION (single place = fewer rerun bugs)
# =============================================================================
def init_session_state() -> None:
    if "client" not in st.session_state:
        st.session_state.client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    if "current_mode" not in st.session_state:
        st.session_state.current_mode = "📚 Bombonica studentica"

    if "temperature" not in st.session_state:
        st.session_state.temperature = MODEL_CONFIGS[st.session_state.current_mode]["temperature"]

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "developer",
                "content": (
                    "You are an advanced dual-purpose AI assistant.\n\n"
                    "IT MODE: Use Markdown code blocks with language tags, explain bug causes clearly, "
                    "prioritize clean and maintainable code, and provide best practices.\n\n"
                    "ACADEMIC MODE: Maintain a formal scholarly tone, focus on logical flow and coherence, "
                    "provide clear rationales for rewrites, and cite relevant academic conventions when applicable.\n\n"
                    "Always be concise, accurate, and helpful."
                ),
            }
        ]

    # Stable ID prevents “duplicate history entries” when Streamlit reruns.
    if "chat_id" not in st.session_state:
        st.session_state.chat_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    if "chat_history" not in st.session_state:
        # Disk is best-effort; session always works.
        st.session_state.chat_history = load_chat_history_from_disk()

    # Keep a single place for “draft streaming text” if you want to persist partials
    if "streaming_buffer" not in st.session_state:
        st.session_state.streaming_buffer = ""


# =============================================================================
# OPENAI STREAMING (robust: always produce a string)
# =============================================================================
def stream_assistant_reply(messages: list[dict], model: str, temperature: float) -> str:
    """
    Streams the assistant response and returns the full text.

    Why this refactor:
    - st.write_stream() may return None or non-string depending on generator output.
    - We explicitly accumulate text to guarantee we can append to chat history.
    """
    client: OpenAI = st.session_state.client

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    chunks: list[str] = []
    placeholder = st.empty()
    text = ""

    for event in stream:
        delta = ""
        try:
            delta = event.choices[0].delta.content or ""
        except Exception:
            delta = ""

        if delta:
            chunks.append(delta)
            text = "".join(chunks)
            placeholder.markdown(text)

    return text.strip()


# =============================================================================
# MAIN APP
# =============================================================================
if check_password():
    init_session_state()

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("⚙️ Settings")

        st.subheader("🎛️ Model Mode")
        mode = st.radio(
            "Select Mode:",
            list(MODEL_CONFIGS.keys()),
            index=list(MODEL_CONFIGS.keys()).index(st.session_state.current_mode)
            if st.session_state.current_mode in MODEL_CONFIGS
            else 2,
            key="mode_selector",
        )
        st.session_state.current_mode = mode

        st.divider()

        # Chat history
        history = st.session_state.chat_history
        if history:
            with st.expander(f"📜 Chat History ({len(history)})"):
                for i, chat in enumerate(history):
                    col1, col2, col3 = st.columns([6, 2, 1])
                    with col1:
                        if st.button(f"💬 {chat.get('preview','')}", key=f"load_{i}"):
                            load_chat_from_history(i)
                            st.rerun()
                    with col2:
                        st.caption(str(chat.get("timestamp", ""))[-8:-3])
                    with col3:
                        if st.button("🗑️", key=f"del_{i}"):
                            delete_chat_from_history(i)
                            st.rerun()

            st.divider()

        # Advanced settings
        with st.expander("🔧 Advanced Settings"):
            cfg = MODEL_CONFIGS[mode]
            st.session_state.temperature = st.slider(
                "Temperature:",
                0.0,
                2.0,
                float(st.session_state.temperature),
                0.1,
            )
            st.caption("Prompt caching is handled server-side by the API when applicable.")

        st.divider()

        st.subheader("📝 Chat Management")
        c1, c2 = st.columns(2)

        with c1:
            if st.button("➕ New Chat", use_container_width=True):
                upsert_current_chat_to_history()
                new_chat()
                st.rerun()

        with c2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                upsert_current_chat_to_history()
                # Clear current chat but keep developer prompt and same chat_id
                st.session_state.messages = [st.session_state.messages[0]]
                st.rerun()

        if len(st.session_state.messages) > 1:
            pdf_bytes = create_pdf(st.session_state.messages)
            st.download_button(
                "📄 Save PDF",
                data=pdf_bytes,
                file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    # --- MAIN UI ---
    st.title(APP_TITLE)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Puiule, intreba si vei gasi raspuns. La el sau la mine")
    with col2:
        mode_display = " ".join(mode.split()[:2])
        st.caption(f"Mode: **{mode_display}**")

    # Render messages
    for m in st.session_state.messages:
        if m["role"] in ("system", "developer"):
            continue
        with st.chat_message(m["role"]):
            st.markdown(m.get("content", ""))

    # Input
    prompt = st.chat_input("Ask me anything...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        cfg = MODEL_CONFIGS[st.session_state.current_mode]
        model = cfg["model"]
        temperature = float(st.session_state.temperature)

        with st.chat_message("assistant"):
            try:
                assistant_text = stream_assistant_reply(
                    messages=st.session_state.messages,
                    model=model,
                    temperature=temperature,
                )
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})

                # Save after each turn (session + best-effort disk)
                upsert_current_chat_to_history()

            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.info("If this is a model access issue, switch to a different mode or verify API access.")