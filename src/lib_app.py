from http import client
import streamlit as st
import pandas as pd
import os
import dotenv
from groq import Groq
import speech_recognition as sr
import time
from fuzzywuzzy import fuzz, process
from streamlit_option_menu import option_menu


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
# CONFIGURATION
# ------------------------
st.set_page_config(
    page_title="📚 University Library Chatbot",
    layout="wide",
    page_icon="📖"
)

# Check if running in cloud environment
IS_CLOUD = os.getenv('STREAMLIT_CLOUD', False)

# Determine data folder (works on both local + Cloud)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "../data")

BOOK_FILES = ["Total books.xlsx", "Book 22.xlsx", "processed_books.xlsx"]

# Load environment variables
dotenv.load_dotenv()

# Get keys
groq_key = os.getenv("GROQ_API_KEY")

# Initialize both clients
groq_client = Groq(api_key=groq_key)


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
def search_books(query, df_books):
    """
    Smart search function for the library chatbot.
    Supports partial matches, fuzzy matches, and typo tolerance.
    """

    query = query.strip().lower()

    # 1️⃣ Try to find exact or partial matches first
    mask = (
        df_books['title'].str.lower().str.contains(query, na=False) |
        df_books['author'].str.lower().str.contains(query, na=False) |
        df_books['isbn'].astype(str).str.contains(query, na=False)
    )
    results = df_books[mask]

    # 2️⃣ If nothing found, use fuzzy matching
    if results.empty:
        fuzzy_matches = []

        for i, row in df_books.iterrows():
            title_score = fuzz.partial_ratio(query, str(row['title']).lower())
            author_score = fuzz.partial_ratio(query, str(row['author']).lower())

            # pick those with at least 60% similarity
            if title_score > 60 or author_score > 60:
                fuzzy_matches.append(row)

        if fuzzy_matches:
            results = pd.DataFrame(fuzzy_matches)

    return results

# ------------------------
# SESSION STATE INIT
# ------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": ""}
    ]

# ------------------------
# PAGE CONFIGURATION
# ------------------------
st.set_page_config(page_title="📚 Library Assistant", page_icon="🤖", layout="centered")

# ------------------------
# THEME TOGGLE
# ------------------------
st.sidebar.title("⚙️ Settings")
theme = st.sidebar.radio("Choose theme", ["Light 🌤️", "Dark 🌙"])

# ------------------------
# CUSTOM CSS (STYLE)
# ------------------------
bg_color = "#E3E4E7" if theme.startswith("Light") else "#436AA9"
bot_color = "#ffffff" if theme.startswith("Light") else "#436AA9"
user_color = "#DCF8C6" if theme.startswith("Light") else "#060707"
text_color = "#000000" if theme.startswith("Light") else "#f5f5f5"
border_color = "#ddd" if theme.startswith("Light") else "#333"

st.markdown(f"""
<style>
body {{
    background-color: {bg_color};
    color: {text_color};
}}
.chat-container {{
    max-width: 700px;
    margin: auto;
    padding: 1rem;
    border-radius: 1rem;        
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    background-color: {bg_color};
}}
.user-bubble {{
    background-color: {user_color};
    color: {text_color};
    padding: 0.75rem 1rem;
    border-radius: 1rem 1rem 0 1rem;        
    margin: 0.5rem 0;
    width: fit-content;
    max-width: 80%;
    margin-left: auto;
    border: 1px solid {border_color};
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    animation: fadeInUp 0.4s ease;
}}

@keyframes fadeInUp {{
    from {{opacity: 0; transform: translateY(10px);}}
    to {{opacity: 1; transform: translateY(0);}}
}}

.typing-dots {{
    display: inline-block;
    animation: blink 1.5s infinite;
}}

@keyframes blink {{
    0% {{opacity: 0.2;}}
    20% {{opacity: 1;}}
    100% {{opacity: 0.2;}}
}}

.stTextInput>div>div>input {{
    border-radius: 1rem;
    padding: 0.75rem 1rem;
    border: 1.5px solid {border_color};
    background-color: {bot_color};
    color: {text_color};
}}

div[data-testid="baseButton-primary"] button {{
    border-radius: 1rem;
    padding: 0.6rem 1.5rem;
    background-color: #007bff;
    color: white;
    font-weight: 500;
}}

div[data-testid="baseButton-secondary"] button {{
    border-radius: 50%;
    height: 3rem;
    width: 3rem;
    font-size: 1.2rem;
}}

.book-card {{
    background-color: {bot_color};
    padding: 1rem;
    border: 1px solid {border_color};
    border-radius: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    margin-bottom: 1rem;
    animation: fadeInUp 0.4s ease;
}}
</style>
""", unsafe_allow_html=True)

# ------------------------
# CHAT DISPLAY
# ------------------------
st.markdown("<h2 style='text-align:center;'>📖 Library Chat Assistant</h2>", unsafe_allow_html=True)
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

# Display chat history
for msg in st.session_state.chat_history:
    if msg["role"] == "student":
        st.markdown(f"<div class='user-bubble'>{msg['text']}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='bot-bubble'>{msg.get('text', msg.get('content', ''))}</div>", unsafe_allow_html=True)


st.markdown("</div>", unsafe_allow_html=True)

# ------------------------
# CHAT INPUT AREA
# ------------------------
st.markdown("""
<style>
.bottom-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    padding: 0.75rem 2rem;
    box-shadow: 0 -3px 8px rgba(0,0,0,0.1);
    z-index: 100;
}
.bottom-input {
    border-radius: 1rem;
    padding: 0.6rem 1rem;
    width: 100%;
    border: 1.5px solid #ccc;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='bottom-bar'>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([2, 5, 1, 1])

with col1:
    # ✅ NEW DROPDOWN FILTER
    search_type = st.selectbox(
        "Search by",
        ["Subject", "Author", "ISBN" , "Keyword"],
        key="search_type"
    )

with col2:
    query = st.text_input(
        "Search Library:",
        key="query",
        placeholder="e.g., Artificial Intelligence, ISBN 978-1-4028-9462-6"
    )

with col3:
    search_clicked = st.button("🔍")

with col4:
    mic_clicked = st.button("🎙️")

st.markdown("</div>", unsafe_allow_html=True)

# ------------------------
# MODIFY SEARCH FUNCTION TO HANDLE FILTER TYPE
def search_books(query, df_books, search_type="Keyword"):
    query = query.strip().lower()
    if not query:
        return pd.DataFrame()

    df_books.columns = [c.strip().lower() for c in df_books.columns]

    if search_type == "Subject" and 'subject' in df_books.columns:
        mask = df_books['subject'].str.lower().str.contains(query, na=False)
    elif search_type == "Author" and 'author' in df_books.columns:
        mask = df_books['author'].str.lower().str.contains(query, na=False)
    elif search_type == "ISBN" and 'isbn' in df_books.columns:
        mask = df_books['isbn'].astype(str).str.contains(query, na=False)
    else:  # Keyword
        mask = (
            df_books['title'].str.lower().str.contains(query, na=False) |
            df_books['author'].str.lower().str.contains(query, na=False) |
            df_books['isbn'].astype(str).str.contains(query, na=False)
        )

    return df_books[mask]

    # # Fallback: fuzzy search if empty
    # if results.empty:
    #     fuzzy_matches = []
    #     for i, row in df_books.iterrows():
    #         title_score = fuzz.partial_ratio(query, str(row.get('title', '')).lower())
    #         author_score = fuzz.partial_ratio(query, str(row.get('author', '')).lower())
    #         if title_score > 60 or author_score > 60:
    #             fuzzy_matches.append(row)
    #     if fuzzy_matches:
    #         results = pd.DataFrame(fuzzy_matches)

    # return results


# ------------------------
# UPDATE SEARCH BUTTON ACTION
# ------------------------
if mic_clicked:
    voice_query = voice_to_text()
    if voice_query:
        st.session_state.chat_history.append({"role": "student", "text": voice_query})
        st.session_state.chat_history.append({"role": "assistant", "text": "Listening... 🎧"})
        st.rerun()

elif search_clicked and query:
    st.session_state.chat_history.append({"role": "student", "text": query})
    with st.spinner("Searching books..."):
        time.sleep(1)

    # ✅ pass search_type to new function
    results = search_books(query, df_books, search_type)

    if results.empty:
        answer = f"😕 No books found for *'{query}'*."
    else:
        answer = f"📚 Found *{len(results)}* book(s) for *'{query}'*. Showing top results below ⬇️"

    st.session_state.chat_history.append({"role": "assistant", "text": answer})
    st.rerun()
# ------------------------
# DISPLAY RESULTS (Modern Card Style)
# ------------------------
if st.session_state.chat_history:
    last_msg = st.session_state.chat_history[-1]
    message_content = last_msg.get("text", last_msg.get("content", ""))

    if "found" in message_content.lower():
        last_query = st.session_state.chat_history[-2].get("text", st.session_state.chat_history[-2].get("content", ""))
        results = search_books(last_query, df_books)

        if not results.empty:
            st.markdown("### 📘 Search Results")

            # --- Intelligent range detection based on user query ---
            lowered_query = last_query.lower()

            # --- Display Options ---
            view_option = st.selectbox(
                "📊 Choose which part of the results to view:",
                ("🔝 Top 5 Results", "🔹 Middle 5 Results", "🔽 Last 5 Results"),
                index=0  # default = Top
            )

            # --- Determine what to show based on user choice ---
            if view_option == "🔽 Last 5 Results":
                shown_results = results.tail(5)
            elif view_option == "🔹 Middle 5 Results":
                start = max(0, len(results)//2 - 2)
                shown_results = results.iloc[start:start+5]
            else:
                shown_results = results.head(5)

            # --- Caption for clarity ---
            st.caption(f"Showing: {view_option}")

            # --- Display results in styled cards ---
            for i, row in shown_results.iterrows():
                st.markdown(f"""
                <div class='book-card'>
                    <b>📖 {row.get('title', 'Unknown Title')}</b><br>
                    👩‍💼 <i>{row.get('author', 'Unknown Author')}</i><br>
                    🆔 ISBN: {row.get('isbn', 'N/A')}<br>
                    🏷️ Edition: {row.get('edition', 'N/A')}<br>
                    💰 Price: {row.get('price', 'N/A')}
                </div>
                """, unsafe_allow_html=True)

        suggestion = process.extractOne(last_query, df_books['title'].tolist())
        if suggestion and suggestion[1] > 60:
            st.info(f"🔍 Did you mean **{suggestion[0]}**?")
            suggested_results = df_books[df_books['title'].str.lower().str.contains(suggestion[0].lower(), na=False)]
        if not suggested_results.empty:
            for i, row in suggested_results.head(3).iterrows():
                st.markdown(f"""
                <div class='book-card'>
                    <b>📖 {row.get('title', 'Unknown Title')}</b><br>
                    👩‍💼 <i>{row.get('author', 'Unknown Author')}</i><br>
                    🆔 ISBN: {row.get('isbn', 'N/A')}<br>
                    💰 Price: {row.get('price', 'N/A')}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.warning("❌ No books found or related titles available.")
                st.rerun()
    
    if query:  # Add condition for handling user input
        # Check for custom message
        lowered_input = query.lower()
        if any(kw in lowered_input for kw in ["who made you", "who built you", "your creator"]):
            bot_reply = (
                "👩‍💻 This AI chatbot was developed by MCA (2nd Year) students at Chaudhary Ranbir Singh University, "
                "Jind. They used cutting-edge tools like **Streamlit**, **Groq**, and the **LLaMA 3.3-70B Versatile** model "
                "to create an intelligent library assistant. 🚀"
            )
        else:
            with st.spinner("Thinking..."):
                try:
                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "You are a helpful library assistant."},
                            {"role": "user", "content": query}
                        ]
                    )
                    bot_reply = response.choices[0].message.content.strip()
                except Exception as e:
                    bot_reply = f"❌ Something went wrong: {e}"

        if "❌" in bot_reply:
            st.error(bot_reply)

        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
        with st.chat_message("assistant"):
            st.markdown(bot_reply)

# ------------------------
# RESET BUTTON
# ------------------------
if st.button("🔄 Reset Chat"):
    st.session_state.chat_history = []
    st.rerun()
