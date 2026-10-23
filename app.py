"""MemoMate Streamlit app. Run: streamlit run app.py"""
import os

import streamlit as st
from dotenv import load_dotenv

import brain
import db
from embeddings import embed

load_dotenv()
st.set_page_config(page_title="MemoMate", page_icon="🧠")
st.title("🧠 MemoMate")

# Stop early with a clear message if a key is missing.
missing = [k for k in ("ANTHROPIC_API_KEY", "MONGODB_URI", "VOYAGE_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"Missing in .env: {', '.join(missing)}. Copy .env.example to .env and fill them in.")
    st.stop()


@st.cache_resource
def init_db():
    db.setup_indexes()  # runs once per app start


try:
    init_db()
except Exception as e:
    st.error(f"Can't connect to MongoDB. Check MONGODB_URI and your Atlas IP access list.\n\n{e}")
    st.stop()

# No login: the user name is the user_id. Change it to "switch user".
user_id = st.sidebar.text_input("User name", value="demo").strip() or "demo"

# --- Chat history ---
try:
    history = db.recent_messages(user_id)
except Exception as e:
    st.error(f"Couldn't load chat history from MongoDB: {e}")
    history = []

for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- New message ---
if prompt := st.chat_input("Write about your day, or ask me to plan..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    try:
        db.save_message(user_id, "user", prompt)
    except Exception as e:
        st.error(f"Couldn't save your message to MongoDB: {e}")

    # 1. Pull memories out of the message and save them.
    notices = []
    try:
        found = brain.extract_memories(prompt)
    except Exception as e:
        st.error(f"Memory extraction failed (Claude): {e}")
        found = []
    for mem in found:
        try:
            vector = embed(mem["content"])
            db.save_memory(user_id, mem, vector, prompt, brain.expires_at(mem, db.now()))
            notices.append(f"💾 Saved {mem['type']}: {mem['content']}")
        except Exception as e:
            st.error(f"Couldn't save memory \"{mem['content']}\" (Voyage or MongoDB): {e}")

    # 2. Reply using the user's memories.
    # ponytail: M1 sends ALL active memories; M2 swaps this for top-5 Vector Search.
    try:
        memories = db.list_memories(user_id)
    except Exception as e:
        st.error(f"Couldn't load memories: {e}")
        memories = []
    try:
        answer = brain.reply(history + [{"role": "user", "content": prompt}], memories)
    except Exception as e:
        st.error(f"Claude couldn't reply: {e}")
        answer = None

    if answer:
        with st.chat_message("assistant"):
            st.markdown(answer)
            for n in notices:
                st.caption(n)
        try:
            db.save_message(user_id, "assistant", answer)  # memories_used gets filled in M2
        except Exception as e:
            st.error(f"Couldn't save the reply to MongoDB: {e}")

# --- Sidebar: memories (drawn last so new memories show up right away) ---
st.sidebar.header("What I remember")
try:
    memories = db.list_memories(user_id)
except Exception as e:
    st.sidebar.error(f"Couldn't load memories: {e}")
    memories = []

if not memories:
    st.sidebar.caption("Nothing yet. Tell me about your day!")

for mem_type in brain.TYPES:
    group = [m for m in memories if m["type"] == mem_type]
    if not group:
        continue
    st.sidebar.subheader(mem_type.title() + "s")
    for m in group:
        expiry = m["expires_at"].strftime("%b %d") if m.get("expires_at") else "never"
        text_col, btn_col = st.sidebar.columns([5, 1])
        text_col.markdown(f"{m['content']}  \n:gray[expires: {expiry}]")
        if btn_col.button("🗑", key=str(m["_id"]), help="Delete this memory"):
            try:
                db.delete_memory(user_id, m["_id"])
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Couldn't delete: {e}")
