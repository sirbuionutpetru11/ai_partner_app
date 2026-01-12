import streamlit as st
from openai import OpenAI
from datetime import datetime
from fpdf import FPDF
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Partner", page_icon="🤖", layout="wide")

# --- 1. ACCESS CONTROL ---
def check_password():
    """Simple password check to protect API credits"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if not st.session_state.password_correct:
        st.title("🔐 AI Partner - Access Required")
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
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "AI Partner - Chat Transcript", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(5)
    
    # Chat messages
    for message in messages:
        if message["role"] != "system":
            # Role header
            pdf.set_font("Arial", "B", 12)
            role = "User" if message["role"] == "user" else "Assistant"
            pdf.cell(0, 8, role + ":", ln=True)
            
            # Message content
            pdf.set_font("Arial", "", 11)
            # Handle multi-line text
            content = message["content"]
            pdf.multi_cell(0, 6, content)
            pdf.ln(3)
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. MAIN APP ---
if check_password():
    # --- INITIALIZATION ---
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    
    if "messages" not in st.session_state:
        # The System Prompt defines the AI's persona
        st.session_state.messages = [
            {"role": "system", "content": (
                "You are an advanced dual-purpose AI assistant.\n\n"
                "IT MODE: Use Markdown code blocks with language tags, explain bug causes clearly, "
                "prioritize clean and maintainable code, and provide best practices.\n\n"
                "ACADEMIC MODE: Maintain a formal scholarly tone, focus on logical flow and coherence, "
                "provide clear rationales for rewrites, and cite relevant academic conventions when applicable.\n\n"
                "Always be concise, accurate, and helpful."
            )}
        ]
    
    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Model selection
        model_choice = st.selectbox(
            "Select Model:",
            ["gpt-5.2"],
            index=1,
            help="Choose the AI model. gpt-4o is more capable but costs more."
        )
        
        # Temperature slider
        temperature = st.slider(
            "Temperature:",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            help="Higher values make output more random, lower values more focused."
        )
        
        st.divider()
        
        # Chat management
        st.subheader("📝 Chat Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
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
        
        st.divider()
        
        # Stats
        st.subheader("📊 Stats")
        message_count = len([m for m in st.session_state.messages if m["role"] != "system"])
        st.metric("Messages", message_count)
        st.caption(f"Model: {model_choice}")
    
    # --- MAIN CHAT INTERFACE ---
    st.title("🤖 AI Partner")
    st.caption("Your intelligent assistant for IT and Academic tasks")
    
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] != "system":
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
                # STREAMING EFFECT
                stream = client.chat.completions.create(
                    model=model_choice,
                    messages=st.session_state.messages,
                    stream=True,
                    temperature=temperature,
                )
                response = st.write_stream(stream)
                
                # Add assistant response to history
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("Please check your API key and try again.")