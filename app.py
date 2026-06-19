from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from huggingface_hub import hf_hub_download
import numpy as np
import pickle, json, os, sqlite3, random, string, hashlib, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'agribot-gh-secret-2024')
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5000","http://localhost:5000"])

REPO_ID            = "Godbles02/agribot-gh"
DB_PATH            = "agribot.db"
EMAIL_SENDER       = os.environ.get('EMAIL_USER', '')
EMAIL_PASS         = os.environ.get('EMAIL_PASS', '')
GOOGLE_CLIENT_ID   = os.environ.get('GOOGLE_CLIENT_ID', '')
OTP_EXPIRY_SECONDS = 60
LOCKOUT_MINUTES    = 10

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT,
            signup_method TEXT NOT NULL DEFAULT "email",
            google_id TEXT UNIQUE,
            verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            lockout_until TEXT,
            attempts INTEGER DEFAULT 0,
            used INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT "New Chat",
            language TEXT DEFAULT "en",
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            language TEXT DEFAULT "en",
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    conn.commit()
    conn.close()

init_db()

print("Loading chatbot from Hugging Face...")
def load_hf(f): return hf_hub_download(repo_id=REPO_ID, filename=f)

with open(load_hf("en_vectorizer.pkl"),"rb") as f: en_vectorizer=pickle.load(f)
with open(load_hf("tw_vectorizer.pkl"),"rb") as f: tw_vectorizer=pickle.load(f)
with open(load_hf("en_questions.json"),"r",encoding="utf-8") as f: en_questions=json.load(f)
with open(load_hf("en_answers.json"),"r",encoding="utf-8") as f: en_answers=json.load(f)
with open(load_hf("tw_questions.json"),"r",encoding="utf-8") as f: tw_questions=json.load(f)
with open(load_hf("tw_answers.json"),"r",encoding="utf-8") as f: tw_answers=json.load(f)

en_vectors = en_vectorizer.transform(en_questions)
tw_vectors = tw_vectorizer.transform(tw_questions)
print(f"Chatbot ready! {len(en_questions)} EN + {len(tw_questions)} TW pairs.")

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def gen_otp(): return ''.join(random.choices(string.digits, k=6))
def now(): return datetime.utcnow()

def get_current_user():
    uid = session.get('user_id')
    if not uid: return None
    conn = get_db()
    u = conn.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    conn.close()
    return u

def valid_password(pw):
    if len(pw) < 8: return False,"Password must be at least 8 characters."
    if not re.search(r'[A-Za-z]',pw): return False,"Password must contain letters."
    if not re.search(r'[0-9]',pw): return False,"Password must contain numbers."
    if not re.search(r'[^A-Za-z0-9]',pw): return False,"Password must contain at least one symbol (e.g. @, #, !)."
    return True,""

def send_otp_email(to_email, otp, username):
    if not EMAIL_SENDER:
        print(f"\n{'='*40}\nDEV MODE — OTP for {to_email}: {otp}\n{'='*40}\n")
        return True
    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = "AgriBotGH — Your Verification Code"
        msg['From'] = f"AgriBotGH <{EMAIL_SENDER}>"
        msg['To'] = to_email
        html = f"""<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto">
          <div style="background:#1B5E20;padding:24px;border-radius:12px 12px 0 0;text-align:center">
            <h2 style="color:white;margin:0">🌿 AgriBotGH</h2>
            <p style="color:#a5d6a7;margin:4px 0 0">Bilingual Agricultural Chatbot</p>
          </div>
          <div style="background:#f9f9f9;padding:28px;border-radius:0 0 12px 12px;border:1px solid #e0e0e0">
            <p style="font-size:15px;color:#333">Hello <strong>{username}</strong>,</p>
            <p style="color:#555">Your verification code is:</p>
            <div style="background:#1B5E20;color:white;font-size:40px;font-weight:bold;
                        text-align:center;padding:20px;border-radius:10px;letter-spacing:12px;margin:20px 0">
              {otp}
            </div>
            <p style="color:#e53935;font-weight:bold;font-size:13px">⏱ This code expires in <strong>1 minute</strong>.</p>
            <p style="color:#888;font-size:12px">If you did not request this, you can safely ignore this email.</p>
          </div></div>"""
        msg.attach(MIMEText(html,"html"))
        with smtplib.SMTP_SSL('smtp.gmail.com',465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASS)
            s.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

FARMING_KW = ['farm','crop','soil','plant','seed','fertilizer','pest','disease','harvest',
    'irrigation','water','maize','cassava','yam','tomato','plantain','rice','pepper',
    'onion','carrot','garden','fish','poultry','chicken','goat','sheep','cattle','cow',
    'weed','insect','fungus','spray','compost','manure','yield','profit','market',
    'sell','buy','loan','agric','okuafo','asase','aburoɔ','bankye','bayerɛ','ferefere',
    'adwummaker','nhaban','apataa','akoko','birekyie','oguan','nnwan','afuom','nnoa']

EN_GREET = ['hi','hello','hey','good morning','good afternoon','good evening']
TW_GREET = ['akwaaba','maakye','maaha','maadwo','ɛte sɛn']
NAME_PH  = ['my name is','i am ','i\'m ','call me ']
CASUAL   = ['how are you','i am fine','i\'m fine','thank you','thanks','okay','ok','nice']

def get_answer(question, language, username=None):
    q = question.lower().strip()
    nb = f", {username}" if username else ""
    for ph in NAME_PH:
        if q.startswith(ph):
            name = question[len(ph):].strip().split()[0].capitalize()
            return f"Nice to meet you, {name}! 🌱 I'm AgriBotGH. Ask me anything about farming!"
    if any(g in q for g in EN_GREET):
        return f"Hello{nb}! 🌿 I'm AgriBotGH, your bilingual farming assistant. What farming question can I help you with today?"
    if any(g in q for g in TW_GREET):
        return f"Akwaaba{nb}! 🌿 Yɛfrɛ me AgriBotGH. Asɛmmisa bɛn fa okuafo adwuma ho na wopɛ sɛ mebo wo aseɛ?"
    if any(c in q for c in CASUAL):
        return f"You're welcome{nb}! 😊 Feel free to ask me any farming questions anytime."
    if not any(kw in q for kw in FARMING_KW) and len(q) > 8:
        return f"Sorry{nb}, I'm a specialised agricultural assistant. I can only help with farming questions — crops, soil, pests, livestock, fish farming and more. 🌾"
    if language == "tw":
        vec=tw_vectorizer.transform([question]); scores=cosine_similarity(vec,tw_vectors)[0]; best=int(np.argmax(scores))
        if scores[best]<0.1: return "Kafra, me nni nsɛm a ɛfa saa asɛm yi ho. Yɛsrɛ wo kɔ wo MOFA okuafo ofisi ma mmoa."
        return tw_answers[best]
    else:
        vec=en_vectorizer.transform([question]); scores=cosine_similarity(vec,en_vectors)[0]; best=int(np.argmax(scores))
        if scores[best]<0.1: return "I'm sorry, I don't have information on that topic yet. Please consult your local MOFA agricultural extension officer."
        return en_answers[best]

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    d=request.get_json(); email=d.get('email','').strip().lower(); username=d.get('username','').strip()
    if not email or not username: return jsonify({"error":"Email and name are required."}),400
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$',email): return jsonify({"error":"Please enter a valid email address."}),400
    if len(username)<2: return jsonify({"error":"Name must be at least 2 characters."}),400
    conn=get_db()
    row=conn.execute('SELECT * FROM otp_codes WHERE contact=? ORDER BY id DESC LIMIT 1',(email,)).fetchone()
    if row and row['lockout_until'] and now()<datetime.fromisoformat(row['lockout_until']):
        mins=int((datetime.fromisoformat(row['lockout_until'])-now()).total_seconds()/60)+1
        conn.close(); return jsonify({"error":f"Too many attempts. Try again in {mins} minute(s).","locked":True}),429
    existing=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if existing and existing['verified']:
        conn.close(); return jsonify({"error":"Email already registered. Please log in."}),409
    otp=gen_otp(); expires=(now()+timedelta(seconds=OTP_EXPIRY_SECONDS)).isoformat()
    if existing: conn.execute('UPDATE users SET username=? WHERE email=?',(username,email))
    else: conn.execute('INSERT INTO users (username,email,signup_method,verified) VALUES (?,?,?,0)',(username,email,'email'))
    conn.execute('DELETE FROM otp_codes WHERE contact=?',(email,))
    conn.execute('INSERT INTO otp_codes (contact,code,expires_at) VALUES (?,?,?)',(email,otp,expires))
    conn.commit(); conn.close()
    send_otp_email(email,otp,username)
    return jsonify({"message":f"Verification code sent to {email}","dev_otp":otp if not EMAIL_SENDER else None})

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    d=request.get_json(); email=d.get('email','').strip().lower(); code=d.get('code','').strip()
    if not email or not code: return jsonify({"error":"Email and code are required."}),400
    conn=get_db()
    row=conn.execute('SELECT * FROM otp_codes WHERE contact=? AND used=0 ORDER BY id DESC LIMIT 1',(email,)).fetchone()
    if not row: conn.close(); return jsonify({"error":"No active code found. Please request a new one."}),400
    if row['lockout_until'] and now()<datetime.fromisoformat(row['lockout_until']):
        mins=int((datetime.fromisoformat(row['lockout_until'])-now()).total_seconds()/60)+1
        conn.close(); return jsonify({"error":f"Locked. Try again in {mins} minute(s).","locked":True}),429
    if now()>datetime.fromisoformat(row['expires_at']):
        conn.close(); return jsonify({"error":"Code expired. Please request a new one.","expired":True}),400
    attempts=row['attempts']+1
    if row['code']!=code:
        if attempts>=3:
            lock=(now()+timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
            conn.execute('UPDATE otp_codes SET attempts=?,lockout_until=? WHERE id=?',(attempts,lock,row['id']))
            conn.commit(); conn.close()
            return jsonify({"error":f"Too many wrong attempts. Locked for {LOCKOUT_MINUTES} minutes.","locked":True}),429
        conn.execute('UPDATE otp_codes SET attempts=? WHERE id=?',(attempts,row['id']))
        conn.commit(); conn.close()
        return jsonify({"error":f"Wrong code. {3-attempts} attempt(s) remaining."}),400
    conn.execute('UPDATE otp_codes SET used=1 WHERE id=?',(row['id'],))
    conn.commit(); conn.close()
    return jsonify({"message":"Email verified! Please set your password.","email":email})

@app.route('/api/auth/set-password', methods=['POST'])
def set_password():
    d=request.get_json(); email=d.get('email','').strip().lower(); password=d.get('password','').strip()
    ok,err=valid_password(password)
    if not ok: return jsonify({"error":err}),400
    conn=get_db()
    user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not user: conn.close(); return jsonify({"error":"User not found. Please start signup again."}),404
    conn.execute('UPDATE users SET password_hash=?,verified=1 WHERE email=?',(hash_pw(password),email))
    conn.commit()
    user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    session['user_id']=user['id']; session['username']=user['username']
    conn.close()
    return jsonify({"message":f"Welcome to AgriBotGH, {user['username']}! 🌱","user":{"id":user['id'],"username":user['username']}})

@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_otp():
    d=request.get_json(); email=d.get('email','').strip().lower()
    conn=get_db()
    row=conn.execute('SELECT * FROM otp_codes WHERE contact=? ORDER BY id DESC LIMIT 1',(email,)).fetchone()
    if row and row['lockout_until'] and now()<datetime.fromisoformat(row['lockout_until']):
        mins=int((datetime.fromisoformat(row['lockout_until'])-now()).total_seconds()/60)+1
        conn.close(); return jsonify({"error":f"Locked. Try again in {mins} minute(s).","locked":True}),429
    user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if not user: conn.close(); return jsonify({"error":"User not found."}),404
    otp=gen_otp(); expires=(now()+timedelta(seconds=OTP_EXPIRY_SECONDS)).isoformat()
    conn.execute('DELETE FROM otp_codes WHERE contact=?',(email,))
    conn.execute('INSERT INTO otp_codes (contact,code,expires_at) VALUES (?,?,?)',(email,otp,expires))
    conn.commit(); conn.close()
    send_otp_email(email,otp,user['username'])
    return jsonify({"message":"New code sent!","dev_otp":otp if not EMAIL_SENDER else None})

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    d=request.get_json(); token=d.get('credential','')
    if not token: return jsonify({"error":"No Google token."}),400
    try:
        import urllib.request
        with urllib.request.urlopen(f"https://oauth2.googleapis.com/tokeninfo?id_token={token}") as r:
            info=json.loads(r.read())
        google_id=info.get('sub'); email=info.get('email','').lower()
        username=info.get('given_name') or info.get('name','User').split()[0]
        if info.get('email_verified')!='true': return jsonify({"error":"Google email not verified."}),400
        conn=get_db()
        user=conn.execute('SELECT * FROM users WHERE google_id=? OR email=?',(google_id,email)).fetchone()
        if user:
            conn.execute('UPDATE users SET google_id=?,verified=1 WHERE id=?',(google_id,user['id']))
            conn.commit(); user=conn.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
        else:
            conn.execute('INSERT INTO users (username,email,google_id,signup_method,verified) VALUES (?,?,?,?,1)',(username,email,google_id,'google'))
            conn.commit(); user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        session['user_id']=user['id']; session['username']=user['username']
        conn.close()
        return jsonify({"message":f"Welcome, {user['username']}! 🌱","user":{"id":user['id'],"username":user['username']}})
    except Exception as e:
        print("Google auth error:",e); return jsonify({"error":"Google sign-in failed."}),500

@app.route('/api/auth/login', methods=['POST'])
def login():
    d=request.get_json(); email=d.get('email','').strip().lower(); password=d.get('password','').strip()
    if not email or not password: return jsonify({"error":"Email and password are required."}),400
    conn=get_db(); user=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); conn.close()
    if not user: return jsonify({"error":"No account found with this email. Please sign up first."}),404
    if not user['verified']: return jsonify({"error":"Email not verified. Please complete signup first."}),401
    if not user['password_hash']: return jsonify({"error":"This account uses Google sign-in. Please use Continue with Google."}),401
    if user['password_hash']!=hash_pw(password): return jsonify({"error":"Wrong password. Please try again."}),401
    session['user_id']=user['id']; session['username']=user['username']
    return jsonify({"message":f"Welcome back, {user['username']}! 🌱","user":{"id":user['id'],"username":user['username']}})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear(); return jsonify({"message":"Logged out."})

@app.route('/api/auth/me', methods=['GET'])
def get_me():
    user=get_current_user()
    if not user: return jsonify({"error":"Not logged in"}),401
    return jsonify({"user":{"id":user['id'],"username":user['username']}})

@app.route('/api/chat', methods=['POST'])
def chat():
    d=request.get_json(); question=d.get('message','').strip(); language=d.get('language','en'); sid=d.get('session_id','')
    if not question: return jsonify({"error":"No message."}),400
    user=get_current_user(); username=user['username'] if user else None
    response=get_answer(question,language,username)
    if user and sid:
        conn=get_db()
        if not conn.execute('SELECT id FROM chat_sessions WHERE id=?',(sid,)).fetchone():
            title=question[:35]+('...' if len(question)>35 else '')
            conn.execute('INSERT INTO chat_sessions (id,user_id,title,language) VALUES (?,?,?,?)',(sid,user['id'],title,language))
        conn.execute('INSERT INTO chat_history (user_id,session_id,role,message,language) VALUES (?,?,?,?,?)',(user['id'],sid,'user',question,language))
        conn.execute('INSERT INTO chat_history (user_id,session_id,role,message,language) VALUES (?,?,?,?,?)',(user['id'],sid,'bot',response,language))
        conn.commit(); conn.close()
    return jsonify({"response":response,"language":language})

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    user=get_current_user()
    if not user: return jsonify({"error":"Not logged in"}),401
    conn=get_db()
    sessions=conn.execute('SELECT * FROM chat_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT 50',(user['id'],)).fetchall()
    conn.close()
    return jsonify({"sessions":[dict(s) for s in sessions]})

@app.route('/api/sessions/<sid>', methods=['GET'])
def get_session(sid):
    user=get_current_user()
    if not user: return jsonify({"error":"Not logged in"}),401
    conn=get_db()
    msgs=conn.execute('SELECT * FROM chat_history WHERE user_id=? AND session_id=? ORDER BY timestamp ASC',(user['id'],sid)).fetchall()
    conn.close()
    return jsonify({"messages":[dict(m) for m in msgs]})

@app.route('/api/sessions/<sid>', methods=['DELETE'])
def delete_session(sid):
    user=get_current_user()
    if not user: return jsonify({"error":"Not logged in"}),401
    conn=get_db()
    conn.execute('DELETE FROM chat_history WHERE user_id=? AND session_id=?',(user['id'],sid))
    conn.execute('DELETE FROM chat_sessions WHERE user_id=? AND id=?',(user['id'],sid))
    conn.commit(); conn.close()
    return jsonify({"message":"Deleted."})

@app.route('/') 
def root(): return send_from_directory('.','auth.html')
@app.route('/app')
def chatapp(): return send_from_directory('.','index.html')
@app.route('/auth')
def authpage(): return send_from_directory('.','auth.html')
@app.route('/<path:filename>')
def static_files(filename): return send_from_directory('.',filename)
@app.route('/api/health')
def health(): return jsonify({"status":"ok","pairs":len(en_questions)})

if __name__=='__main__':
    app.run(debug=True,port=5000)
