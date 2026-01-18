import os
import re
import json
import sqlite3
import requests
from typing import TypedDict, Dict, Any

from fastapi import FastAPI, Query
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer, util
import torch

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found")

# --------------------------------------------------
# LLM
# --------------------------------------------------
llm = ChatGroq(
    model="qwen/qwen3-32b",
    api_key=GROQ_API_KEY,
    temperature=0.7
)

# --------------------------------------------------
# App setup
# --------------------------------------------------
app = FastAPI(title="Rick & Morty Characters Dialogue Engine")

embedder = SentenceTransformer("all-MiniLM-L6-v2")
BASE = "https://rickandmortyapi.com/api"
DB = "rm.db"

# --------------------------------------------------
# Persistence
# --------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            char1 TEXT,
            char2 TEXT,
            dialogue TEXT,
            embedding TEXT,
            scores TEXT,
            note TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            character_id INTEGER,
            note TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def fetch_character_by_id(cid: int) -> Dict[str, Any]:
    resp = requests.get(f"{BASE}/character/{cid}", timeout=10)
    resp.raise_for_status()
    return resp.json()

def strip_reasoning(text: str) -> str:
    return re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

# --------------------------------------------------
# LangGraph State
# --------------------------------------------------
class DialogueState(TypedDict, total=False):
    char1: Dict[str, Any]
    char2: Dict[str, Any]
    dialogue: str
    score: float

# --------------------------------------------------
# Graph Nodes
# --------------------------------------------------
def retrieve_characters(state: DialogueState) -> DialogueState:
    return state

def generate_dialogue(state: DialogueState) -> DialogueState:
    c1, c2 = state["char1"], state["char2"]

    prompt = f"""
You are a professional scriptwriter for Rick & Morty.

Write a short dialogue (8–10 turns) between:
- {c1['name']} ({c1['species']}, {c1['status']})
- {c2['name']} ({c2['species']}, {c2['status']})

Rules:
- Each line MUST start with the character's name
- Dark humor, sarcasm, sci-fi references
- DO NOT explain reasoning
- ONLY output dialogue
"""

    raw = llm.invoke(prompt).content
    dialogue = strip_reasoning(raw)

    return {**state, "dialogue": dialogue}

def evaluate_dialogue(state: DialogueState) -> DialogueState:
    anchor = f"{state['char1']['name']} {state['char2']['name']}"
    e1 = embedder.encode(anchor, convert_to_tensor=True)
    e2 = embedder.encode(state["dialogue"], convert_to_tensor=True)

    score = round(util.cos_sim(e1, e2).item(), 3)
    return {**state, "score": score}

# --------------------------------------------------
# Build LangGraph
# --------------------------------------------------
graph = StateGraph(DialogueState)
graph.add_node("retrieve", retrieve_characters)
graph.add_node("generate", generate_dialogue)
graph.add_node("evaluate", evaluate_dialogue)
graph.set_entry_point("retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", "evaluate")
graph.add_edge("evaluate", END)
dialogue_graph = graph.compile()

# --------------------------------------------------
# API Routes
# --------------------------------------------------
@app.get("/")
def home():
    return {"message": "Rick & Morty Dialogue API running 🚀"}

@app.get("/run-dialogue")
def run_dialogue(char1_id: int = Query(...), char2_id: int = Query(...)):
    char1 = fetch_character_by_id(char1_id)
    char2 = fetch_character_by_id(char2_id)

    result = dialogue_graph.invoke({"char1": char1, "char2": char2})

    return {
        "conversation": result["dialogue"],
        "semantic_score": result["score"],
    }

# ---------- SAVE ----------
@app.post("/save-conversation")
def save_conversation(payload: Dict[str, Any]):
    embedding = embedder.encode(payload["dialogue"]).tolist()

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        payload["conversation_id"],
        payload["timestamp"],
        payload["char1"]["name"],
        payload["char2"]["name"],
        payload["dialogue"],
        json.dumps(embedding),
        json.dumps(payload["scores"]),
        payload["note"]
    ))
    conn.commit()
    conn.close()

    return {"status": "saved"}

# ---------- LIST ----------
@app.get("/list-conversations")
def list_conversations():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT timestamp, char1, char2, dialogue, scores, note
        FROM conversations
        ORDER BY timestamp DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    return [
        {
            "timestamp": r[0],
            "char1": r[1],
            "char2": r[2],
            "dialogue": r[3],
            "scores": json.loads(r[4]),
            "note": r[5],
        }
        for r in rows
    ]

# ---------- SEMANTIC SEARCH (FIXED) ----------
@app.get("/search-conversations")
def search_conversations(q: str):
    q_emb = embedder.encode(q, convert_to_tensor=True)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT timestamp, char1, char2, dialogue, embedding, scores, note
        FROM conversations
    """).fetchall()
    conn.close()

    results = []
    for ts, c1, c2, dlg, emb_json, scores, note in rows:
        emb = torch.tensor(json.loads(emb_json))
        sim = util.cos_sim(q_emb, emb).item()

        results.append((sim, {
            "timestamp": ts,
            "char1": c1,
            "char2": c2,
            "dialogue": dlg,
            "scores": json.loads(scores),
            "note": note,
        }))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:10]]
