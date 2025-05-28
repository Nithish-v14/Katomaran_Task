import streamlit as st
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import faiss
import numpy as np
import sqlite3
from datetime import datetime

# ---- Load face registration data ----
conn = sqlite3.connect('database/faces.db')
cursor = conn.cursor()
cursor.execute("SELECT name, timestamp FROM faces")
rows = cursor.fetchall()
conn.close()

# ---- Format timestamp
def format_timestamp(iso_str):
    dt = datetime.fromisoformat(iso_str)
    return dt.strftime("%B %d, %Y at %I:%M %p")

docs = [f"{name} was registered at {format_timestamp(timestamp)}" for name, timestamp in rows]

# ---- Embedding Model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
doc_embeddings = embedding_model.encode(docs, convert_to_numpy=True)

# ---- FAISS Index
dimension = doc_embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(doc_embeddings)

# ---- LLM
generator = pipeline("text2text-generation", model="google/flan-t5-base", tokenizer="google/flan-t5-base")

# ---- Keyword-Based Intent Detection
def is_registration_related(question):
    keywords = ["who", "registered", "how many", "when", "time", "name", "person"]
    return any(kw in question.lower() for kw in keywords)

# ---- Streamlit UI
st.title("💬 Chatbot: Ask About Registered Users or General AI Questions")

query = st.text_input("Enter your question")

if query:
    if is_registration_related(query):
        # RAG Path
        query_embedding = embedding_model.encode([query], convert_to_numpy=True)
        _, indices = index.search(query_embedding, k=3)
        relevant_docs = [docs[i] for i in indices[0]]
        context = "\n".join(relevant_docs)
        prompt = f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    else:
        # General question path
        prompt = f"Answer the following general question clearly:\n\n{query}"

    answer = generator(prompt, max_length=150, do_sample=False)[0]['generated_text']
    st.markdown(f"**Answer:** {answer}")
