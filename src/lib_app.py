import streamlit as st
import pandas as pd
import os
import time

# Try importing speech recognition safely (for local use only)
try:
    import speech_recognition as sr
except ImportError:
    sr = None

# ------------------------
# ENVIRONMENT CHECK
# ------------------------
IS_CLOUD = os.environ.get("STREAMLIT_RUNTIME", "") == "cloud"

# ------------------------
# SIDEBAR - CRSU Library Info
# ------------------------
with st.sidebar:
    st.image("src/logo-crsu.png", width=130)
    st.markdown("## 📖 CRSU Library Portal")
    st.markdown("""
    Welcome to the official **Chaudhary Ranbir Singh University Library Chatbot**.  
    Explore books, authors, or ISBNs and access digital resources.
    """)
    st.divider()

    st.markdown("### 🏛 About CRSU Library")
    st.markdown("""
    - **University:** Chaudhary Ranbir Singh University, Jind (Haryana)  
    - **Hours:** 9:00 AM – 5:00 PM (Mon–Sat)  
    - **Location:** Central Library Building, CRSU Campus  
    - **Contact:** library@crsu.ac.in  
    """)

    st.divider()
    st.markdown("### 🌐 Quick Links")
    st.link_button("🔗 CRSU Official Website", "https://www.crsu.ac.in/")
    st.link_button("📚 Digital Library (NDLI Access)", "https://ndl.iitkgp.ac.in/")
    st.link_button("💾 CRSU e-Resources", "https://www.crsu.ac.in/index.php/en/library")

    st.divider()
    st.caption("Powered by Neha Dhiman | Developed with ❤️ using Streamlit")

# ------------------------
# CONFIGURATION
# ------------------------
st.set_page_config(
    page_title="📚 University Library Chatbot",
    layout="wide",
    page_icon="📖"
)

# Determine data folder (works on both local + Streamlit Cloud)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "../data")

BOOK_FILES = ["Total books.xlsx", "Book 22.xlsx", "processed_books.xlsx"]

st.write("📂 Working directory:", os.getcwd())
st.write("📂 Data path:", DATA_PATH)
st.write("📂 Files in data:", os.listdir(DATA_PATH) if os.path.exists(DATA_PATH) else "Data folder not found")

# ------------------------
# STYLE
# ------------------------
st.markdown("""
<style>
body {background-color:#f7f9fc;}
h1 {color:#1e3d59;}
h2, h3 {color:#1e3d59;}
.stButton>button {background-color:#1e3d59;color:white;border-radius:8px;}
.chat-bubble {background:#e9f0ff;padding:10px;border-radius:12px;margin:5px 0;}
.user-bubble {background:#d1f7e1;padding:10px;border-radius:12px;margin:5px 0;text-align:right;}
.fade-in {animation: fadeIn 2s ease-in-out;}
@keyframes fadeIn {from {opacity: 0; transform: translateY(-10px);} to {opacity: 1; transform: translateY(0);}}
.fixed-header {
    position: fixed; top: 0; left: 0; width: 70%; left: 20%;
    background-color: #54ACBF; color: white; padding: 60px 10px;
    z-index: 1000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    font-size: 28px; font-weight: bold;
}
.header-placeholder { height: 60px; }
@media only screen and (max-width: 600px) {
    .fixed-header { font-size: 20px; padding: 10px 5px; }
    .header-placeholder { height: 50px; }
}
</style>
""", unsafe_allow_html=True)

# ------------------------
# LOAD BOOK DATA
# ------------------------
@st.cache_data
def load_books():
    df_all = pd.DataFrame()
    for file in BOOK_FILES:
        path = os.path.join(DATA_PATH, file)
        if os.path.exists(path):
            try:
                df = pd.read_excel(path) if file.endswith(".xlsx") else pd.DataFrame()
                df_all = pd.concat([df_all, df], ignore_index=True)
            except Exception as e:
                st.warning(f"Error reading {file}: {e}")
        else:
            st.warning(f"File not found: {file}")
    if not df_all.empty:
        df_all.fillna("", inplace=True)
    return df_all

df_books = load_books()

# ------------------------
# VOICE RECOGNITION (Auto Handles Cloud or Local)
# ------------------------
def voice_to_text():
    if IS_CLOUD or sr is None:
        st.info("🎙 Voice input via browser not supported here.")
        st.warning("Please type your query below instead.")
        return None
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎙 Speak now...")
            audio = recognizer.listen(source, timeout=5)
        text = recognizer.recognize_google(audio)
        st.success(f"🗣 You said: {text}")
        return text
    except sr.UnknownValueError:
        st.error("❌ Could not understand audio.")
    except sr.RequestError:
        st.error("⚠️ Voice service unavailable.")
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
    return None

# ------------------------
# SEARCH FUNCTION
# ------------------------
def search_books(query, df):
    query = query.lower()
    search_cols = [c for c in df.columns if c.lower() in ["title","author","edition","publishercde"]]
    if not search_cols:
        search_cols = df.columns
    mask = df.apply(lambda row: any(query in str(row[c]).lower() for c in search_cols), axis=1)
    return df[mask]

# ------------------------
# HEADER + GREETING
# ------------------------
st.markdown('<div class="fixed-header">📚 University Library Chatbot</div>', unsafe_allow_html=True)
st.markdown('<div class="header-placeholder"></div>', unsafe_allow_html=True)
st.markdown('<h3 class="fade-in">Hi there! 👋 I\'m your Library Assistant. Ask me about books, authors, ISBNs, or keywords.</h3>', unsafe_allow_html=True)

# ------------------------
# SESSION STATE INIT
# ------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "Hi! How can I help you today?"}
    ]

# ------------------------
# MAIN CHAT INPUT ROW
# ------------------------
col1, col2 = st.columns([8, 1])

with col1:
    query = st.text_input("Enter your query here")

with col2:
    if st.button("🎤"):
        voice_query = voice_to_text()
        if voice_query:
            st.session_state.chat_history.append({"role": "student", "text": voice_query})
            results = search_books(voice_query, df_books)
            if results.empty:
                answer = f"No books found for '{voice_query}'."
            else:
                answer = f"Found {len(results)} book(s) for '{voice_query}'. Showing top 10 results."
            st.session_state.chat_history.append({"role": "assistant", "text": answer})

# ------------------------
# TEXT SEARCH BUTTON
# ------------------------
if st.button("Search") and query:
    st.session_state.chat_history.append({"role": "student", "text": query})
    results = search_books(query, df_books)
    if results.empty:
        answer = f"No books found for '{query}'."
    else:
        answer = f"Found {len(results)} book(s) for '{query}'. Showing top 10 results."
    st.session_state.chat_history.append({"role": "assistant", "text": answer})

# ------------------------
# CHAT HISTORY DISPLAY
# ------------------------
st.markdown("### Chat History")
for msg in st.session_state.chat_history[::-1]:
    text = msg.get('text') or msg.get('content') or '[No text]'
    if msg.get("role") == "student":
        st.markdown(f"<div class='user-bubble'>{text}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='chat-bubble'>{text}</div>", unsafe_allow_html=True)

# ------------------------
# SEARCH RESULTS DISPLAY
# ------------------------
if st.session_state.chat_history:
    last_bot_msg = st.session_state.chat_history[-1]
    last_text = (last_bot_msg.get("text") or last_bot_msg.get("content") or "").lower()
    if last_bot_msg.get("role") == "assistant" and ("found" in last_text or "showing" in last_text):
        if len(st.session_state.chat_history) >= 2 and st.session_state.chat_history[-2].get("role") == "student":
            last_query = st.session_state.chat_history[-2]["text"]
            results = search_books(last_query, df_books)
            if not results.empty:
                display_cols = [c for c in ["title","author","isbn","edition","copyrigth date","pages","price","itemcallnumber","barcode","accessioned"] if c in results.columns]
                st.dataframe(results[display_cols].head(10))

# ------------------------
# RESET BUTTON
# ------------------------
if st.button("🔄 Reset Chat"):
    st.session_state.chat_history = []
    st.rerun()
