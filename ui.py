import streamlit as st
import requests
import uuid
from datetime import datetime

# --------------------------------------------------
# Config
# --------------------------------------------------
BACKEND = "http://localhost:8000"
RM_API = "https://rickandmortyapi.com/api"

st.set_page_config(
    page_title="Rick & Morty AI Explorer",
    layout="wide"
)
st.title("🛸 Rick & Morty AI Explorer")

# --------------------------------------------------
# API Helpers
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def fetch_locations():
    r = requests.get(f"{RM_API}/location", timeout=10).json()
    return r["results"]

@st.cache_data(show_spinner=False)
def fetch_character_by_url(url: str):
    r = requests.get(url, timeout=10)
    return r.json() if r.status_code == 200 else None

# --------------------------------------------------
# Render helpers
# --------------------------------------------------
def render_location(loc):
    with st.expander("📍 Location details"):
        st.write(f"**Name:** {loc['name']}")
        st.write(f"**Type:** {loc['type']}")
        st.write(f"**Dimension:** {loc['dimension']}")
        st.write(f"**Residents:** {len(loc['residents'])}")

def render_character(char):
    with st.expander(f"🧑 {char['name']} details"):
        st.image(char["image"], width=150)
        st.write(f"**Species:** {char['species']}")
        st.write(f"**Status:** {char['status']}")
        st.write(f"**Gender:** {char['gender']}")
        st.write(f"**Origin:** {char['origin']['name']}")

# --------------------------------------------------
# Session State
# --------------------------------------------------
st.session_state.setdefault("selected_location", None)
st.session_state.setdefault("char1", None)
st.session_state.setdefault("char2", None)
st.session_state.setdefault("current_conversation", None)

# --------------------------------------------------
# Tabs
# --------------------------------------------------
tab_chat, tab_history = st.tabs(
    ["💬 Conversation", "🗂 History & Search"]
)

# ==================================================
# TAB 1 — CONVERSATION
# ==================================================
with tab_chat:
    st.subheader("📍 Step 1: Select Location")

    locations = fetch_locations()
    loc_map = {loc["name"]: loc for loc in locations}

    location_name = st.selectbox(
        "Choose a location",
        options=list(loc_map.keys())
    )

    location = loc_map[location_name]
    st.session_state.selected_location = location
    render_location(location)

    # --------------------------------------------------
    st.divider()
    st.subheader("🧑 Step 2: Select Characters from Location")

    residents = [
        fetch_character_by_url(url)
        for url in location["residents"]
    ]
    residents = [r for r in residents if r]

    if len(residents) < 2:
        st.warning("This location has fewer than 2 residents.")
        st.stop()

    char_map = {c["name"]: c for c in residents}

    col1, col2 = st.columns(2)

    with col1:
        char1_name = st.selectbox("Character 1", char_map.keys())
        char1 = char_map[char1_name]
        st.session_state.char1 = char1
        render_character(char1)

    with col2:
        char2_name = st.selectbox(
            "Character 2",
            [n for n in char_map.keys() if n != char1_name]
        )
        char2 = char_map[char2_name]
        st.session_state.char2 = char2
        render_character(char2)

    # --------------------------------------------------
    st.divider()
    st.subheader("🧠 Step 3: Generate AI Dialogue")

    if st.button("💬 Generate AI Conversation"):
        with st.spinner("Generating dialogue..."):
            res = requests.get(
                f"{BACKEND}/run-dialogue",
                params={"char1_id": char1["id"], "char2_id": char2["id"]},
                timeout=60
            ).json()

            st.session_state.current_conversation = {
                "conversation_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "char1": char1,
                "char2": char2,
                "dialogue": res["conversation"],
                "semantic_score": res["semantic_score"],
            }

    # --------------------------------------------------
    # Render Dialogue (CHAT STYLE)
    conv = st.session_state.current_conversation

    if conv:
        st.markdown("### 🤖 Dialogue")

        lines = [
            line for line in conv["dialogue"].split("\n") if ":" in line
        ]

        for line in lines:
            speaker, text = line.split(":", 1)
            speaker = speaker.strip()
            text = text.strip()

            if speaker == conv["char1"]["name"]:
                role = "assistant"
                avatar = conv["char1"]["image"]
            else:
                role = "user"
                avatar = conv["char2"]["image"]

            with st.chat_message(role, avatar=avatar):
                st.markdown(text)

        st.metric("Semantic Alignment", conv["semantic_score"])

        # --------------------------------------------------
        # Feedback (COMPACT)
        st.subheader("🧪 Feedback")

        f1, f2, f3 = st.columns(3)

        with f1:
            c1_score = st.radio(
                f"{conv['char1']['name']}",
                [1, 2, 3, 4, 5],
                horizontal=True
            )

        with f2:
            c2_score = st.radio(
                f"{conv['char2']['name']}",
                [1, 2, 3, 4, 5],
                horizontal=True
            )

        with f3:
            creativity = st.radio(
                "Creativity",
                [1, 2, 3, 4, 5],
                horizontal=True
            )

        note = st.text_area("Optional feedback / observations")

        if st.button("💾 Save Conversation"):
            requests.post(
                f"{BACKEND}/save-conversation",
                json={
                    **conv,
                    "scores": {
                        "char1": c1_score,
                        "char2": c2_score,
                        "creativity": creativity,
                    },
                    "note": note,
                },
                timeout=30
            )
            st.success("Conversation saved ✅")

# ==================================================
# TAB 2 — HISTORY & SEARCH
# ==================================================
with tab_history:
    st.subheader("🔎 Semantic Search")

    query = st.text_input("Search past conversations")

    if query:
        results = requests.get(
            f"{BACKEND}/search-conversations",
            params={"q": query},
            timeout=30
        ).json()
    else:
        results = requests.get(
            f"{BACKEND}/list-conversations",
            timeout=30
        ).json()

    st.divider()

    if not results:
        st.info("No conversations found.")
    else:
        for conv in results[:10]:
            with st.expander(
                f"{conv['timestamp']} — {conv['char1']} & {conv['char2']}"
            ):
                st.write(conv["dialogue"])
                st.write("Scores:", conv["scores"])
                st.write("Note:", conv["note"])
