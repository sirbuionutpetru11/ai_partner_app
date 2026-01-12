import streamlit as st
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF
import io
import json
import os
from pathlib import Path

# --- PAGE CONFIG ---
st.set_page_config(page_title="Buna inteligenta artificala, dar mai buna iubirea umana", page_icon="🤖", layout="wide")

# --- 1. ACCESS CONTROL ---
def check_password():
    """Simple password check to protect API credits"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if not st.session_state.password_correct:
        st.title("🔐 Robotu' nostru - Access Required")
        pwd = st.text_input("Enter Passcode", type="password", key="password_input")
        if st.button("Unlock"):
            if pwd == st.secrets["APP_PASSWORD"]:  # Set this in Streamlit Secrets
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
        st.stop()
        return False
    return True

# --- 2. PDF EXPORT FUNCTION ---
def create_pdf(messages):
    """Generate a PDF of the chat conversation"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Add Unicode font support
    pdf.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
    
    # Title
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, "Robotu' nostru - Chat Transcript", ln=True, align="C")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(5)
    
    # Chat messages
    for message in messages:
        if message["role"] not in ["system", "developer"]:
            # Role header
            pdf.set_font("DejaVu", "B", 12)
            role = "User" if message["role"] == "user" else "Assistant"
            pdf.cell(0, 8, role + ":", ln=True)
            
            # Message content - handle encoding errors
            pdf.set_font("DejaVu", "", 11)
            content = message["content"]
            # Replace problematic characters if DejaVu font not available
            try:
                pdf.multi_cell(0, 6, content)
            except Exception as e:
                # Fallback: remove special characters
                clean_content = content.encode('ascii', 'ignore').decode('ascii')
                pdf.multi_cell(0, 6, clean_content)
            pdf.ln(3)
    
    return pdf.output(dest='S')

# --- 3. CHAT HISTORY FUNCTIONS (PERSISTENT) ---
# Storage directory
HISTORY_DIR = Path.home() / ".ai_partner_history"
HISTORY_FILE = HISTORY_DIR / "chat_history.json"

def ensure_history_dir():
    """Create history directory if it doesn't exist"""
    HISTORY_DIR.mkdir(exist_ok=True)

def load_chat_history_from_disk():
    """Load chat history from disk"""
    ensure_history_dir()
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Could not load chat history: {e}")
            return []
    return []

def save_chat_history_to_disk(history):
    """Save chat history to disk"""
    ensure_history_dir()
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Could not save chat history: {e}")

def save_chat_history():
    """Save current chat to history"""
    if len(st.session_state.messages) > 1:  # Only save if there are messages beyond system prompt
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Get first user message as preview
        preview = "New Chat"
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                break
        
        chat_data = {
            "timestamp": timestamp,
            "preview": preview,
            "messages": st.session_state.messages,
            "mode": st.session_state.current_mode
        }
        
        # Load existing history
        history = load_chat_history_from_disk()
        
        # Check if this chat already exists (same preview and similar length)
        is_duplicate = False
        for i, existing_chat in enumerate(history):
            if (existing_chat["preview"] == preview and 
                abs(len(existing_chat["messages"]) - len(st.session_state.messages)) < 3):
                # Update existing chat instead of adding new
                history[i] = chat_data
                is_duplicate = True
                break
        
        if not is_duplicate:
            # Add to history (limit to last 50 chats)
            history.insert(0, chat_data)
            history = history[:50]
        
        # Save to disk
        save_chat_history_to_disk(history)
        
        # Update session state
        st.session_state.chat_history = history

def load_chat_from_history(index):
    """Load a chat from history"""
    if "chat_history" in st.session_state and index < len(st.session_state.chat_history):
        chat_data = st.session_state.chat_history[index]
        st.session_state.messages = chat_data["messages"]
        st.session_state.current_mode = chat_data["mode"]

def delete_chat_from_history(index):
    """Delete a specific chat from history"""
    if "chat_history" in st.session_state and index < len(st.session_state.chat_history):
        st.session_state.chat_history.pop(index)
        save_chat_history_to_disk(st.session_state.chat_history)

# --- 4. MODEL CONFIGURATIONS ---
MODEL_CONFIGS = {
    "💻 Iubirelu' programelu'": {
        "model": "gpt-5.2",
        "description": "Deep reasoning for complex coding & analysis",
        "cost": "$$$$",
        "best_for": "Complex algorithms, system architecture, deep analysis",
        "price_input": "$1.75/M tokens",
        "price_cached": "$0.175/M tokens (90% off)",
        "price_output": "$14.00/M tokens",
        "temperature": 1.0,
        "supports_streaming": True
    },
    "⚡ Bun la tat": {
        "model": "gpt-5",
        "description": "Balanced intelligence for everyday tasks",
        "cost": "$$$",
        "best_for": "General tasks, analysis, creative work, coding",
        "price_input": "$1.25/M tokens",
        "price_cached": "$0.125/M tokens (90% off)",
        "price_output": "$10.00/M tokens",
        "temperature": 1.0,
        "supports_streaming": True
    },
    "📚 Bombonica studentica": {
        "model": "gpt-5-mini",
        "description": "Fast & affordable for quick corrections",
        "cost": "$",
        "best_for": "Grammar fixes, quick edits, simple questions, text corrections",
        "price_input": "$0.25/M tokens",
        "price_cached": "$0.025/M tokens (90% off)",
        "price_output": "$2.00/M tokens",
        "temperature": 1.0,
        "supports_streaming": True
    }
}

# --- 4. MAIN APP ---
if check_password():
    # --- INITIALIZATION ---
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    
    if "messages" not in st.session_state:
        # The System Prompt defines the AI's persona
        # Using "developer" role for better caching (stays constant)
        st.session_state.messages = [
            {"role": "developer", "content": (
                "You are an advanced dual-purpose AI assistant.\n\n"
                "IT MODE: Use Markdown code blocks with language tags, explain bug causes clearly, "
                "prioritize clean and maintainable code, and provide best practices.\n\n"
                "ACADEMIC MODE: Maintain a formal scholarly tone, focus on logical flow and coherence, "
                "provide clear rationales for rewrites, and cite relevant academic conventions when applicable.\n\n"
                "Always be concise, accurate, and helpful."
            )}
        ]
    
    if "current_mode" not in st.session_state:
        st.session_state.current_mode = "📚 Bombonica studentica"
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_chat_history_from_disk()
    
    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # 1. Mode Toggle (first)
        st.subheader("🎛️ Model Mode")
        mode = st.radio(
            "Select Mode:",
            list(MODEL_CONFIGS.keys()),
            index=2,  # Default to Bombonica studentica (index 2)
            key="mode_selector",
            help="Toggle between different AI modes"
        )
        st.session_state.current_mode = mode
        
        st.divider()
        
        # 2. Chat History section (second)
        if "chat_history" in st.session_state and len(st.session_state.chat_history) > 0:
            with st.expander(f"📜 Chat History ({len(st.session_state.chat_history)})"):
                for i, chat in enumerate(st.session_state.chat_history):
                    col1, col2, col3 = st.columns([5, 1, 1])
                    with col1:
                        if st.button(
                            f"💬 {chat['preview'][:35]}...",
                            key=f"load_chat_{i}",
                            help=f"From: {chat['timestamp']}"
                        ):
                            load_chat_from_history(i)
                            st.rerun()
                    with col2:
                        st.caption(chat['timestamp'].split()[1][:5])  # Show time only
                    with col3:
                        if st.button("🗑️", key=f"delete_chat_{i}", help="Delete"):
                            delete_chat_from_history(i)
                            st.rerun()
            st.divider()
        
        # 3. Upload Documents (third)
        st.subheader("📎 Upload Documents")
        uploaded_file = st.file_uploader(
            "Upload for analysis",
            type=['txt', 'pdf', 'docx', 'md'],
            help="Upload once, ask multiple questions to maximize cache benefits"
        )
        if uploaded_file:
            st.success("✅ Document loaded!")
        
        st.divider()
        
        # 4. Stats section (fourth)
        st.subheader("📊 Session Stats")
        message_count = len([m for m in st.session_state.messages if m["role"] not in ["system", "developer"]])
        st.metric("Messages", message_count)
        
        st.divider()
        
        # 5. Advanced Settings (fifth - collapsible)
        with st.expander("🔧 Advanced Settings"):
            config = MODEL_CONFIGS[mode]
            # Temperature
            temperature = st.slider(
                "Temperature:",
                min_value=0.0,
                max_value=2.0,
                value=config['temperature'],
                step=0.1,
                help="Higher = more creative, Lower = more focused"
            )
            
            # Caching info
            st.markdown("### 💾 Prompt Caching")
            st.success("✅ Auto-enabled - 90% discount!")
            st.caption("Upload documents once, ask multiple questions at discounted rates")
        
        st.divider()
        
        # 6. Chat management (last)
        st.subheader("📝 Chat Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                # Save current chat before clearing
                save_chat_history()
                # Keep the system message
                st.session_state.messages = [st.session_state.messages[0]]
                st.rerun()
        
        with col2:
            # PDF export
            if len(st.session_state.messages) > 1:  # Only show if there are messages
                pdf_bytes = create_pdf(st.session_state.messages)
                st.download_button(
                    label="📄 Save PDF",
                    data=pdf_bytes,
                    file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    # --- MAIN CHAT INTERFACE ---
    st.title("🤖 Buna inteligenta artificala, dar mai buna iubirea umana")
    
    # Mode indicator in main area
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Puiule, intreba si vei gasi raspuns. La el sau la mine")
    with col2:
        # Show mode emoji and short name
        mode_display = mode.split()[0] + " " + mode.split()[1]
        st.caption(f"Mode: **{mode_display}**")
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] not in ["system", "developer"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            try:
                config = MODEL_CONFIGS[st.session_state.current_mode]
                
                # Prepare API parameters
                api_params = {
                    "model": config["model"],
                    "messages": st.session_state.messages,
                    "temperature": temperature if 'temperature' in locals() else config["temperature"],
                    "stream": config["supports_streaming"]
                }
                
                # STREAMING EFFECT
                if config["supports_streaming"]:
                    stream = client.chat.completions.create(**api_params)
                    response = st.write_stream(stream)
                else:
                    # Non-streaming fallback
                    api_params.pop("stream")
                    response_obj = client.chat.completions.create(**api_params)
                    response = response_obj.choices[0].message.content
                    st.markdown(response)
                
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Auto-save after each response
                save_chat_history()
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                if "model" in str(e).lower():
                    st.warning("⚠️ Model may not be available yet. Try switching to a different mode.")
                    st.info("💡 Tip: GPT-5 models might require API access. Check OpenAI's model availability.")
                else:
                    st.info("Please check your API key and try again.")