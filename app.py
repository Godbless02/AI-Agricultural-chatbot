from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from huggingface_hub import hf_hub_download
import numpy as np, pickle, json, os, re

app = Flask(__name__)
CORS(app)

REPO_ID = "Godbles02/agribot-gh"

# ── LOAD MODEL ────────────────────────────────────────────────────
print("Loading chatbot from Hugging Face...")
def hf(f): return hf_hub_download(repo_id=REPO_ID, filename=f)

with open(hf("en_vectorizer.pkl"),"rb") as f: en_vec = pickle.load(f)
with open(hf("tw_vectorizer.pkl"),"rb") as f: tw_vec = pickle.load(f)
with open(hf("en_questions.json"),"r",encoding="utf-8") as f: en_qs = json.load(f)
with open(hf("en_answers.json"), "r",encoding="utf-8") as f: en_as = json.load(f)
with open(hf("tw_questions.json"),"r",encoding="utf-8") as f: tw_qs = json.load(f)
with open(hf("tw_answers.json"), "r",encoding="utf-8") as f: tw_as = json.load(f)

en_vecs = en_vec.transform(en_qs)
tw_vecs = tw_vec.transform(tw_qs)
print(f"Ready! {len(en_qs)} EN + {len(tw_qs)} TW pairs loaded.")

# ── TOPICS ────────────────────────────────────────────────────────
# All 28 topics extracted from the dataset with their keywords,
# Twi names, suggested questions, and topic icons.

TOPICS = {
    "Soil & Land Preparation": {
        "icon": "🌍",
        "keywords": ["soil","land","asase","ph","acidic","erosion","compost",
                     "organic","tillage","raised bed","nursery","transplant",
                     "germina","seed","planting","spacing","rotation","mulch","biochar"],
        "suggestions": [
            "How do I know if my soil is good for farming?",
            "How do I prevent soil erosion on my farm?",
            "How do I make compost at home?",
            "What is the best way to transplant seedlings?",
            "What is crop rotation and why is it important?"
        ]
    },
    "Fertilizer & Nutrients": {
        "icon": "🧪",
        "keywords": ["fertilizer","ferefere","npk","nutrient","manure",
                     "green manure","vermicompost","biochar","nitrogen",
                     "phosphorus","potassium","foliar","deficien"],
        "suggestions": [
            "What does NPK mean on a fertilizer bag?",
            "Can I use animal manure instead of chemical fertilizer?",
            "How do I know if my fertilizer is working?",
            "Can over-fertilizing damage my crops?",
            "What is green manure and how do I use it?"
        ]
    },
    "Maize": {
        "icon": "🌽",
        "keywords": ["maize","aburo","corn","armyworm","streak","aburow"],
        "suggestions": [
            "When is the best time to plant maize in Ghana?",
            "What fertilizer should I apply to maize and when?",
            "How do I identify a fall armyworm attack on my maize?",
            "How do I control weeds in my maize farm?",
            "How many bags of maize can I expect from one acre?"
        ]
    },
    "Cassava": {
        "icon": "🥔",
        "keywords": ["cassava","bankye","gari","mosaic","starch","fufu"],
        "suggestions": [
            "How do I select good cassava stems for planting?",
            "How do I process cassava into gari?",
            "What diseases affect cassava and how do I manage them?",
            "What is the best cassava variety for making fufu?",
            "How much profit can I make from one acre of cassava?"
        ]
    },
    "Plantain & Banana": {
        "icon": "🍌",
        "keywords": ["plantain","banana","boɔde","kwadu","sigatoka","sucker"],
        "suggestions": [
            "What type of sucker is best for planting plantain?",
            "How do I control black sigatoka disease in plantain?",
            "How do I know when plantain is ready to harvest?",
            "How do I make plantain chips for sale?",
            "What fertilizer is best for plantain?"
        ]
    },
    "Yam": {
        "icon": "🍠",
        "keywords": ["yam","bayerɛ","sett","mound","bayere"],
        "suggestions": [
            "How do I prepare yam setts for planting?",
            "What is the best time to plant yam in Ghana?",
            "How do I build a yam mound and why is it important?",
            "How do I store yam properly after harvest?",
            "Can I grow yam without mounds?"
        ]
    },
    "Cocoyam": {
        "icon": "🌿",
        "keywords": ["cocoyam","kɔkɔnte","kontomire","taro","eddoe"],
        "suggestions": [
            "How do I grow cocoyam successfully in Ghana?",
            "How do I store cocoyam after harvest?",
            "How do I add value to cocoyam for better income?",
            "What are the common pests and diseases of cocoyam?",
            "What are the marketing opportunities for cocoyam?"
        ]
    },
    "Tomatoes": {
        "icon": "🍅",
        "keywords": ["tomato","ntomate","blight","blossom","leaf miner"],
        "suggestions": [
            "How do I grow tomatoes in Ghana for good yield?",
            "How do I prevent tomato late blight?",
            "What causes tomato blossom end rot and how do I fix it?",
            "What is the best irrigation method for tomatoes?",
            "What fertilizer programme should I follow for tomatoes?"
        ]
    },
    "Pepper": {
        "icon": "🌶️",
        "keywords": ["pepper","mako","scotch bonnet","bell pepper"],
        "suggestions": [
            "How do I raise pepper seedlings?",
            "How do I prevent pepper root rot?",
            "How do I dry and preserve pepper for longer shelf life?",
            "How do I grow bell pepper for high value markets?",
            "What types of pepper are grown in Ghana?"
        ]
    },
    "Onion": {
        "icon": "🧅",
        "keywords": ["onion","gyene","abɔnkɔ","downy"],
        "suggestions": [
            "How do I grow onions in Ghana?",
            "What causes onion bulbs to be small?",
            "How do I control thrips on my onions?",
            "How do I cure and store onions after harvest?",
            "What are the main onion varieties grown in Ghana?"
        ]
    },
    "Carrot": {
        "icon": "🥕",
        "keywords": ["carrot"],
        "suggestions": [
            "How do I grow carrots in Ghana?",
            "What problems are common in carrot growing?",
            "How do I thin carrot seedlings?",
            "How do I harvest and clean carrots for market?",
            "What fertilizer does carrot need?"
        ]
    },
    "Garden Eggs": {
        "icon": "🍆",
        "keywords": ["garden egg","ntorɔ","eggplant","epilachna","ntoro"],
        "suggestions": [
            "How do I grow garden eggs in Ghana?",
            "What pests attack garden eggs and how do I control them?",
            "How do I manage water for garden eggs?",
            "How long does garden egg take from planting to harvest?",
            "How do I make garden egg farming profitable?"
        ]
    },
    "Palm Oil & Coconut": {
        "icon": "🌴",
        "keywords": ["palm","abɛ","coconut","kuuku","kernel"],
        "suggestions": [
            "How do I establish a palm oil plantation in Ghana?",
            "How do I harvest palm fruits properly?",
            "How do I process palm fruits into palm oil?",
            "How do I grow and care for coconut trees?",
            "How do I process coconut into various products?"
        ]
    },
    "Groundnut & Legumes": {
        "icon": "🥜",
        "keywords": ["groundnut","nkatie","cowpea","abɔdweɛ","soybean","legume"],
        "suggestions": [
            "How do I grow groundnuts in Ghana?",
            "How do I make peanut butter from groundnuts?",
            "What disease affects groundnuts?",
            "How do I grow soybean commercially?",
            "How long does cowpea take to mature?"
        ]
    },
    "Rice": {
        "icon": "🌾",
        "keywords": ["rice","ɔtɛ","striga"],
        "suggestions": [
            "When should I harvest rice?",
            "Which rice varieties perform best in Ghana?",
            "How do I control striga weed in rice?",
            "How do I protect my rice from birds?"
        ]
    },
    "Cocoa": {
        "icon": "🍫",
        "keywords": ["cocoa","kookoo","black pod","cacao"],
        "suggestions": [
            "How do I increase my cocoa yield?",
            "What causes cocoa black pod disease and how do I control it?",
            "How do I manage disease in my cocoa nursery?",
            "How do I grow cashew successfully?"
        ]
    },
    "Other Vegetables": {
        "icon": "🥦",
        "keywords": ["cucumber","watermelon","moringa","vegetable","nnuan","pineapple","mango","cashew"],
        "suggestions": [
            "Can I grow vegetables in the dry season?",
            "Can I plant different vegetables together in one plot?",
            "How do I grow moringa and what are its benefits?",
            "How do I grow pineapple commercially?",
            "How do I grow watermelon successfully?"
        ]
    },
    "Pest & Disease Control": {
        "icon": "🐛",
        "keywords": ["pest","disease","aphid","mite","fungus","nematode",
                     "weevil","armyworm","ipm","integrated","pesticide",
                     "neem","spray","adwummaker","yadeɛ"],
        "suggestions": [
            "How do I use pesticides safely on my farm?",
            "What is Integrated Pest Management (IPM)?",
            "How do I make neem pesticide spray at home?",
            "How do I identify spider mites and control them?",
            "What causes powdery mildew and how do I control it?"
        ]
    },
    "Irrigation & Water": {
        "icon": "💧",
        "keywords": ["irrigat","water","drip","borehole","flood",
                     "drainage","moisture","dam","quench","nsuo"],
        "suggestions": [
            "What is the best irrigation method for a small farm?",
            "How do I conserve water on my farm during the dry season?",
            "How do I build a small dam or water harvesting system?",
            "How do I manage waterlogging on my farm?",
            "How do I manage irrigation efficiently to save water?"
        ]
    },
    "Harvesting & Storage": {
        "icon": "🏪",
        "keywords": ["harvest","storage","store","guina","post-harvest",
                     "hermetic","silo","aflatoxin","mould","weevil","dry"],
        "suggestions": [
            "How do I store my maize to prevent aflatoxin?",
            "How do I properly dry my produce after harvesting?",
            "What is hermetic storage and can a small farmer use it?",
            "How do I preserve fresh fish without a fridge?",
            "How do I reduce post-harvest losses for vegetables?"
        ]
    },
    "Fish Farming": {
        "icon": "🐟",
        "keywords": ["fish","tilapia","catfish","apataa","pond","cage",
                     "fingerling","aqua","aquaculture"],
        "suggestions": [
            "How do I start a fish farm in Ghana?",
            "What is the best fish feed for tilapia?",
            "How do I maintain good water quality in my fish pond?",
            "How much does it cost to start a fish farm in Ghana?",
            "What is the difference between tilapia and catfish farming?"
        ]
    },
    "Poultry Farming": {
        "icon": "🐔",
        "keywords": ["poultry","chicken","broiler","layer","akoko",
                     "newcastle","litter","brooder","guinea fowl","egg"],
        "suggestions": [
            "How do I start a poultry farm in Ghana?",
            "How do I prevent Newcastle disease in my poultry?",
            "What should I feed my broiler chickens?",
            "How do I set up a brooder for day-old chicks?",
            "How do I reduce feed costs in poultry farming?"
        ]
    },
    "Goat Farming": {
        "icon": "🐐",
        "keywords": ["goat","abirekyi","birekyie","kid","doe","buck","dairy goat"],
        "suggestions": [
            "How do I start goat farming in Ghana?",
            "What diseases should I vaccinate my goats against?",
            "What do goats eat and how do I feed them?",
            "How often do goats give birth?",
            "How do I identify a healthy goat when buying?"
        ]
    },
    "Sheep Farming": {
        "icon": "🐑",
        "keywords": ["sheep","oguan","lamb","ewe","foot rot"],
        "suggestions": [
            "How do I start sheep farming in Ghana?",
            "How do I treat sheep for internal parasites?",
            "How do I build a simple sheep pen in Ghana?",
            "How do I market sheep for maximum profit?",
            "What shelter do sheep need in Ghana?"
        ]
    },
    "Cattle Farming": {
        "icon": "🐄",
        "keywords": ["cattle","cow","nnwan","bull","calf","trypanosomiasis","fodder"],
        "suggestions": [
            "How do I start cattle farming in Ghana?",
            "What vaccines do cattle need in Ghana?",
            "How do I deworm cattle and when should it be done?",
            "What fodder crops can I grow to feed my cattle?",
            "How do I manage grazing land for cattle sustainably?"
        ]
    },
    "Business & Marketing": {
        "icon": "💰",
        "keywords": ["market","sell","profit","income","loan","credit",
                     "cooperative","contract","export","insurance","budget",
                     "value","middlemen","record","business","social media"],
        "suggestions": [
            "How do I sell my farm produce at a better price?",
            "Where can I get agricultural loans in Ghana?",
            "What is contract farming and how does it benefit me?",
            "How do I write a simple farm business plan?",
            "What government support is available for young farmers?"
        ]
    },
    "Climate & Weather": {
        "icon": "🌦️",
        "keywords": ["climate","weather","drought","flood","rainfall",
                     "season","agroforestry","adaptation","change"],
        "suggestions": [
            "How does climate change affect farming in Ghana?",
            "How do I protect my farm during heavy rainfall?",
            "How do I prepare my farm for unpredictable weather?",
            "What crops are most resilient to climate change in Ghana?",
            "What is agroforestry and how does it benefit my farm?"
        ]
    },
    "Farm Management": {
        "icon": "📋",
        "keywords": ["manage","plan","map","labour","equipment",
                     "extension","mofa","record","efficiency","mechaniz"],
        "suggestions": [
            "How do I keep records for my farm?",
            "How do I prepare a simple farm budget?",
            "What equipment do I need to start a small farm?",
            "How do I access land for farming in Ghana?",
            "What training opportunities exist for farmers in Ghana?"
        ]
    },
}

# ── CONVERSATION HELPERS ──────────────────────────────────────────
EN_GREET  = ['hi','hello','hey','good morning','good afternoon','good evening']
TW_GREET  = ['akwaaba','maakye','maaha','maadwo']
CASUAL    = ['how are you','i am fine','thank you','thanks','okay','ok','good','nice','great']
NAME_PH   = ['my name is','i am ','i\'m ','call me ']
VAGUE     = ['help','help me','i need help','i have a problem','i have a question',
             'i want to know','tell me','what can you do','what do you know']

def detect_topic(text):
    """Return the best matching topic for a given input text."""
    t = text.lower()
    best_topic, best_score = None, 0
    for topic, info in TOPICS.items():
        score = sum(1 for kw in info['keywords'] if kw in t)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic if best_score > 0 else None

def all_topics_list():
    """Return a formatted string listing all topics."""
    lines = [f"{info['icon']} {topic}" for topic, info in TOPICS.items()]
    return "\n".join(lines)

def topic_suggestions(topic):
    """Return suggestions for a given topic."""
    info = TOPICS.get(topic, {})
    icon = info.get('icon','🌱')
    suggestions = info.get('suggestions', [])
    lines = [f"  • {q}" for q in suggestions[:5]]
    return icon, "\n".join(lines)

def get_answer(question, lang, username=None):
    q  = question.strip()
    ql = q.lower()
    nb = f", {username}" if username else ""

    # ── Name introduction ──────────────────────────────────────────
    for ph in NAME_PH:
        if ql.startswith(ph):
            name = q[len(ph):].strip().split()[0].capitalize()
            return {
                "type": "answer",
                "text": f"Nice to meet you, {name}! 🌱 I am AgriBotGH. Ask me anything about farming and I will help you!"
            }

    # ── Greetings ──────────────────────────────────────────────────
    if any(g in ql for g in EN_GREET) and len(ql) < 30:
        return {
            "type": "answer",
            "text": f"Hello{nb}! 🌿 I am AgriBotGH, your bilingual farming assistant. What farming question can I help you with today?"
        }
    if any(g in ql for g in TW_GREET) and len(ql) < 30:
        return {
            "type": "answer",
            "text": f"Akwaaba{nb}! 🌿 Yɛfrɛ me AgriBotGH. Asɛmmisa bɛn fa okuafo adwuma ho na wopɛ sɛ mebo wo aseɛ?"
        }

    # ── Casual chat ────────────────────────────────────────────────
    if any(ql == c for c in CASUAL):
        return {
            "type": "answer",
            "text": f"You're welcome{nb}! 😊 I am always here to help with your farming questions. What would you like to know?"
        }

    # ── Vague / too short ──────────────────────────────────────────
    if any(ql.strip() == v for v in VAGUE) or len(ql.strip()) < 6:
        return {
            "type": "topics",
            "text": (
                f"Hello{nb}! 😊 I am AgriBotGH — a farming assistant for Ghanaian farmers.\n\n"
                "I can help you with many topics. Please select one that interests you:"
            ),
            "topics": list(TOPICS.keys()),
            "topic_icons": {t: TOPICS[t]['icon'] for t in TOPICS}
        }

    # ── Detect topic from input ────────────────────────────────────
    detected_topic = detect_topic(ql)

    # ── Run retrieval ──────────────────────────────────────────────
    CONFIDENCE_THRESHOLD = 0.18

    if lang == "tw":
        vec    = tw_vec.transform([q])
        scores = cosine_similarity(vec, tw_vecs)[0]
        best   = int(np.argmax(scores))
        conf   = float(scores[best])
        if conf >= CONFIDENCE_THRESHOLD:
            return {"type": "answer", "text": tw_as[best]}
    else:
        vec    = en_vec.transform([q])
        scores = cosine_similarity(vec, en_vecs)[0]
        best   = int(np.argmax(scores))
        conf   = float(scores[best])
        if conf >= CONFIDENCE_THRESHOLD:
            return {"type": "answer", "text": en_as[best]}

    # ── Below threshold — but topic was detected ──────────────────
    if detected_topic:
        icon, sugg = topic_suggestions(detected_topic)
        return {
            "type": "low_confidence",
            "text": (
                f"I can see you are asking about **{detected_topic}** {icon} — "
                f"that is one of the topics I cover! However, I do not have a specific answer "
                f"to your exact question yet.\n\n"
                f"This could be because:\n"
                f"• The question is too specific for my current training\n"
                f"• I may need more details to understand what you need\n\n"
                f"Here are some related questions I **can** help you with on {detected_topic}:"
            ),
            "suggestions": TOPICS[detected_topic]['suggestions'][:5],
            "topic": detected_topic
        }

    # ── No topic detected — off-topic ─────────────────────────────
    return {
        "type": "off_topic",
        "text": (
            f"Sorry{nb}, I am AgriBotGH — a specialised agricultural assistant for Ghanaian farmers. "
            f"I can only help with farming-related topics. 🌾\n\n"
            f"Please select a topic below and I will show you what I can help you with:"
        ),
        "topics": list(TOPICS.keys()),
        "topic_icons": {t: TOPICS[t]['icon'] for t in TOPICS}
    }

# ── ROUTES ────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    d        = request.get_json()
    question = d.get('message','').strip()
    language = d.get('language','en')
    username = d.get('username', None)
    if not question:
        return jsonify({"error": "No message provided"}), 400
    result = get_answer(question, language, username)
    return jsonify(result)

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Return all topics with their icons and suggestions."""
    return jsonify({
        topic: {
            "icon": info['icon'],
            "suggestions": info['suggestions']
        }
        for topic, info in TOPICS.items()
    })

@app.route('/api/topic-suggestions', methods=['POST'])
def topic_suggestions_route():
    """Return suggestions for a selected topic."""
    d     = request.get_json()
    topic = d.get('topic','')
    if topic not in TOPICS:
        return jsonify({"error": "Topic not found"}), 404
    info = TOPICS[topic]
    return jsonify({
        "topic": topic,
        "icon": info['icon'],
        "suggestions": info['suggestions']
    })

@app.route('/api/health')
def health():
    return jsonify({"status":"ok","en_pairs":len(en_qs),"tw_pairs":len(tw_qs),"topics":len(TOPICS)})

@app.route('/')
def index(): return send_from_directory('.','index.html')

@app.route('/<path:f>')
def static_files(f): return send_from_directory('.',f)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
