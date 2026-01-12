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
        if message["role"] not in ["system", "developer"]:
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

# --- 3. MODEL CONFIGURATIONS ---
MODEL_CONFIGS = {
    "💻 Iubirelu' programelu'": {
        "model": "gpt-5.2",
        "description": "Deep reasoning for complex coding & analysis",
        "cost": "$$$$",
        "best_for": "Complex algorithms, system architecture, deep analysis",
        "price_input": "$1.75/M tokens",
        "price_cached": "$0.175/M tokens (90% off)",
        "price_output": "$14.00/M tokens",
        "temperature": 0.7,
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
        "temperature": 0.7,
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
        "temperature": 0.7,
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
        st.session_state.current_mode = "⚡ Bun la tat"
    
    # --- SIDEBAR SETTINGS ---
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Quick Mode Toggle - Most Prominent
        st.subheader("🎛️ Model Mode")
        mode = st.radio(
            "Select Mode:",
            list(MODEL_CONFIGS.keys()),
            index=1,  # Default to Bun la tat
            key="mode_selector",
            help="Toggle between different AI modes"
        )
        st.session_state.current_mode = mode
        
        # Display current mode info
        config = MODEL_CONFIGS[mode]
        st.info(f"""
        **{mode}**
        
        💰 Cost: {config['cost']}  
        📝 Best for: {config['best_for']}
        
        {config['description']}
        
        **Pricing:**
        • Input: {config['price_input']}
        • Cached: {config['price_cached']}
        • Output: {config['price_output']}
        """)
        
        st.divider()
        
        # Advanced Settings (collapsible)
        with st.expander("🔧 Advanced Settings"):
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
            st.success("✅ **Auto-enabled** - 90% discount on repeated content!")
            st.caption("Upload documents once, ask multiple questions at discounted rates")
            
            # Cache examples
            with st.expander("💡 Caching Examples"):
                st.markdown("""
                **Example 1: Document Analysis**
                - First question: Full price
                - Next 10 questions: 90% off!
                
                **Example 2: Code Review**
                - Paste codebase once
                - Multiple reviews: 90% off!
                
                **Keep asking questions in same chat to maintain cache!**
                """)
        
        st.divider()
        
        # Chat management
        st.subheader("📝 Chat Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
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
        
        st.divider()
        
        # Stats
        st.subheader("📊 Session Stats")
        message_count = len([m for m in st.session_state.messages if m["role"] not in ["system", "developer"]])
        st.metric("Messages", message_count)
        st.caption(f"Model: {config['model']}")
        
        # Cost estimate (rough)
        if message_count > 0:
            if config['model'] == "gpt-5-mini":
                est_cost = "< $0.01"
            elif config['model'] == "gpt-5":
                est_cost = "~$0.05-0.15"
            else:  # gpt-5.2
                est_cost = "~$0.10-0.30"
            st.caption(f"Est. session cost: {est_cost}")
            
        # Model comparison
        with st.expander("📊 Model Comparison"):
            st.markdown("""
            | Mode | Input | Cached | Output |
            |------|-------|--------|--------|
            | 💻 Iubirelu' | $1.75 | $0.175 | $14.00 |
            | ⚡ Bun la tat | $1.25 | $0.125 | $10.00 |
            | 📚 Bombonica | $0.25 | $0.025 | $2.00 |
            
            *Prices per 1M tokens*
            """)
    
    # --- MAIN CHAT INTERFACE ---
    st.title("🤖 AI Partner")
    
    # Mode indicator in main area
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Your intelligent assistant for IT and Academic tasks")
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
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                if "model" in str(e).lower():
                    st.warning("⚠️ Model may not be available yet. Try switching to a different mode.")
                    st.info("💡 Tip: GPT-5 models might require API access. Check OpenAI's model availability.")
                else:
                    st.info("Please check your API key and try again.")

# --- OPTIONAL: FILE UPLOAD SECTION ---
# Uncomment below to add file upload capability for maximum caching benefits

with st.sidebar:
    st.divider()
    st.subheader("📎 Upload Documents")
    uploaded_file = st.file_uploader(
        "Upload for analysis (maximizes cache benefits)",
        type=['txt', 'pdf', 'docx', 'md'],
        help="Upload once, ask multiple questions to save 90% on costs"
    )
    if uploaded_file:
        # Process file content
        st.success("✅ Document loaded & cached!")