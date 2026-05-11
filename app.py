# AgriBotGH — Flask Backend
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from huggingface_hub import hf_hub_download
import numpy as np
import pickle
import json
import os
from flask import send_from_directory

app = Flask(__name__)
CORS(app)

# ── Load chatbot files from Hugging Face ─────────────────────────
REPO_ID = "Godbles02/agribot-gh"

print("Loading chatbot files from Hugging Face...")

def load_file(filename):
    path = hf_hub_download(repo_id=REPO_ID, filename=filename)
    return path

# Load vectorizers
with open(load_file("en_vectorizer.pkl"), "rb") as f:
    en_vectorizer = pickle.load(f)

with open(load_file("tw_vectorizer.pkl"), "rb") as f:
    tw_vectorizer = pickle.load(f)

# Load Q&A data
with open(load_file("en_questions.json"), "r", encoding="utf-8") as f:
    en_questions = json.load(f)

with open(load_file("en_answers.json"), "r", encoding="utf-8") as f:
    en_answers = json.load(f)

with open(load_file("tw_questions.json"), "r", encoding="utf-8") as f:
    tw_questions = json.load(f)

with open(load_file("tw_answers.json"), "r", encoding="utf-8") as f:
    tw_answers = json.load(f)

# Pre-compute vectors
en_vectors = en_vectorizer.transform(en_questions)
tw_vectors = tw_vectorizer.transform(tw_questions)

print(f"Chatbot ready! {len(en_questions)} English + {len(tw_questions)} Twi Q&A pairs loaded.")

# ── Chat function ─────────────────────────────────────────────────
def get_answer(question, language="en"):
    if language == "en":
        vec    = en_vectorizer.transform([question])
        scores = cosine_similarity(vec, en_vectors)[0]
        best   = np.argmax(scores)
        confidence = scores[best]
        if confidence < 0.1:
            return "I'm sorry, I don't have information on that topic yet. Please consult your local agricultural extension officer."
        return en_answers[best]
    else:
        vec    = tw_vectorizer.transform([question])
        scores = cosine_similarity(vec, tw_vectors)[0]
        best   = np.argmax(scores)
        confidence = scores[best]
        if confidence < 0.1:
            return "Kafra, me nni nsɛm a ɛfa saa asɛm yi ho. Yɛsrɛ wo kɔ wo okuafo ofisi."
        return tw_answers[best]

# ── API Routes ────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "status": "AgriBotGH is running!",
        "message": "Send POST request to /api/chat"
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data     = request.get_json()
    question = data.get("message", "").strip()
    language = data.get("language", "en")

    if not question:
        return jsonify({"error": "No message provided"}), 400

    answer = get_answer(question, language)

    return jsonify({
        "question": question,
        "response": answer,
        "language": language
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "pairs_loaded": len(en_questions)})

@app.route('/app')
def frontend():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)
# ── Run server ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)