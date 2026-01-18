# 🛸 Rick & Morty AI Explorer

A lightweight AI-powered application demonstrating structured data retrieval, AI-augmented generation, evaluation, persistence, and semantic search using the **Rick & Morty API**.

This project was built as part of the **Rick & Morty AI Challenge** to showcase end-to-end reasoning over structured and unstructured data, not just UI rendering.

---

## 🚀 Features Overview

- Location-based character selection (grounded in real API data)
- AI-generated dialogue between two characters
- Chat-style UI for conversations
- Persistent storage of conversations and feedback
- Embedding-based semantic search over past conversations
- Lightweight evaluation scaffolding (human + automated)

---

## 🏗️ Architecture

| Layer | Technology |
|-----|-----------|
| Frontend | Streamlit (`ui.py`) |
| Backend API | FastAPI (`app.py`) |
| LLM | Groq (`qwen/qwen3-32b`) |
| Orchestration | LangGraph |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) |
| Persistence | SQLite |
| External Data | Rick & Morty REST API |

---

## 1. Data Retrieval

### 1a. Locations & Residents

The application fetches and structures **locations** from the Rick & Morty API, including:

- Location name, type, and dimension
- Residents with:
  - Name
  - Species
  - Status
  - Gender
  - Origin
  - Image

**Flow enforced in UI:**
1. User selects a location
2. Only residents of that location are available for character selection

This ensures all downstream AI generation is **grounded in structured API data**, not random sampling.

---

### 1b. REST vs GraphQL – Design Choice

**Chosen:** REST API

**Reasoning:**
- Zero setup and schema overhead
- Clear pagination and predictable responses
- Faster iteration under time constraints
- Lower client-side complexity

While GraphQL could reduce over-fetching, REST provided better developer ergonomics for a lightweight demo.

---

## 2. Interaction & Notes

### 2a. Character Interaction

- Expandable panels show full character details
- AI-generated dialogue between two selected characters
- User feedback captured per conversation:
  - Character accuracy scores
  - Creativity score
  - Free-text notes

### 2b. Persistence Layer

**Chosen:** SQLite

**Why SQLite?**
- File-based and portable
- ACID-compliant
- Zero infrastructure overhead
- Ideal for local demos and prototypes

**Stored data includes:**
- Conversations
- User feedback scores
- Notes
- Precomputed embeddings

---

## 3. Generative Layer

### 3a. AI Feature

**Implemented feature:**  
> Generate a short, in-character dialogue between two residents of the same location.

**LLM:** `qwen/qwen3-32b` (via Groq)

**Why this model?**
- Strong reasoning + creative writing
- Low latency
- Open-model ecosystem
- Suitable for prototyping and demos

**LangGraph** is used to:
- Explicitly model generation steps
- Separate retrieval, generation, and evaluation
- Keep logic composable and debuggable

Reasoning traces (`<think>`) are defensively removed via prompt constraints and post-processing.

---

### 3b. Evaluation Scaffolding

#### i. Human-in-the-loop Evaluation
Users rate:
- Character 1 accuracy
- Character 2 accuracy
- Creativity
- Optional qualitative feedback

#### ii. Embedding-based Metric
A cosine similarity score between:
- Character anchor text
- Generated dialogue

This provides a **lightweight heuristic alignment score**, not a claim of ground-truth correctness.

---

## 4. Semantic Search (Bonus)

### AI-Augmented Search

- Each conversation is embedded at save time
- Embeddings are stored in SQLite as JSON
- Search queries are embedded and compared using cosine similarity
- Results are ranked by semantic relevance

⚠️ **Important:**  
This is **semantic ranking**, not strict keyword filtering.  
A query like `"Snuffles"` may reorder results based on relevance rather than returning only exact matches.

This aligns with the task requirement for **semantic or fuzzy retrieval powered by embeddings**.

---

## 🖥️ UI / UX Highlights

- Chat-style dialogue using `st.chat_message`
- Character avatars shown in chat bubbles
- Two-step selection (Location → Characters)
- Compact, non-intrusive feedback inputs
- Separate tab for history and semantic search

The UI prioritizes **clarity, grounding, and explainability**.

---

## ▶️ Running the Project

### Backend
```bash
uvicorn app:app --reload
```

### Frontend
```bash
streamlit run ui.py 
```
## Project Overview
This project is a lightweight AI-powered application built using the Rick & Morty API.
It demonstrates structured data retrieval, generative AI, lightweight evaluation,
persistent storage, and semantic search using embeddings.

## Project Structure
- app.py : FastAPI backend handling generation, storage, and search
- ui.py : Streamlit frontend for interaction
- rm.db : SQLite database (auto-created)
- README.md

## How to Run
1. Set GROQ_API_KEY in environment
2. Run backend: uvicorn app:app --reload
3. Run frontend: streamlit run ui.py

## Task Alignment
1. Data Retrieval
- Locations fetched via REST API
- Residents resolved with character details
2. Interaction & Notes
- Character detail view
- Persistent feedback stored in SQLite
3. Generative Layer
- LLM powered dialogue generation
- Evaluation using cosine similarity
4. Semantic Search
- Embedding-based retrieval over stored conversations

## Architecture Decisions
- REST over GraphQL for simplicity and clarity
- SQLite for lightweight persistence
- SentenceTransformers for embeddings
### Evaluation Strategy
- Human feedback scores
- Automated semantic similarity
