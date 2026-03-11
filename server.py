from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import json
import os
import urllib3
from dotenv import load_dotenv # API Gizlemek için eklendi

# .env dosyasındaki verileri yükle
load_dotenv()

# SSL uyarılarını gizle
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "varsayilan_anahtar_4876")

# --- YAPILANDIRMA (Artık Gizli) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# 429 hatasını azaltmak için daha stabil olan modele geçtik:
MODEL_NAME = "llama-3.1-8b-instant" 
USER_FILE = "kullanicilar.json"

# --- VERİ FONKSİYONLARI ---
def veri_oku(dosya, varsayilan=None):
    if varsayilan is None: varsayilan = {}
    if os.path.exists(dosya):
        with open(dosya, "r", encoding="utf-8") as f:
            try:
                content = f.read().strip()
                return json.loads(content) if content else varsayilan
            except: return varsayilan
    return varsayilan

def veri_yaz(dosya, veri):
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# --- SİSTEM BAŞLATMA ---
with app.app_context():
    users = veri_oku(USER_FILE)
    admin_user = "HscAdmin"
    admin_pass = "4876Hsc487634544800"
    if admin_user not in users:
        users[admin_user] = {"password": generate_password_hash(admin_pass), "is_admin": True}
        veri_yaz(USER_FILE, users)
        print(f">>> {admin_user} Sistemi Aktif Edildi.")

# --- ROUTERLAR ---
@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('index.html', username=session['username'], is_admin=session.get('is_admin'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        users = veri_oku(USER_FILE)
        if u in users and check_password_hash(users[u]['password'], p):
            session['username'] = u
            session['is_admin'] = users[u].get('is_admin', False)
            return redirect(url_for('index'))
        return "Giriş başarısız."
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username', '').strip()
        p = request.form.get('password', '').strip()
        users = veri_oku(USER_FILE)
        if u in users: return "Bu kullanıcı zaten mevcut."
        users[u] = {"password": generate_password_hash(p), "is_admin": False}
        veri_yaz(USER_FILE, users)
        return 'Kayıt başarılı! <a href="/login">Giriş Yap</a>'
    return render_template('register.html')

@app.route('/admin/chats')
def admin_chats():
    if not session.get('is_admin'):
        return "Yetkisiz erişim.", 403
    files = [f for f in os.listdir('.') if f.startswith('history_') and f.endswith('.json')]
    all_data = {f.replace('history_', '').replace('.json', ''): veri_oku(f, []) for f in files}
    return render_template('admin.html', all_chats=all_data)

@app.route('/get_history')
def get_history():
    if 'username' not in session: return jsonify([])
    return jsonify(veri_oku(f"history_{session['username']}.json", []))

@app.route('/reset', methods=['POST'])
def reset_history():
    if 'username' not in session: return jsonify({"success": False})
    veri_yaz(f"history_{session['username']}.json", [])
    return jsonify({"success": True})

# --- DABI ZEKA MERKEZİ ---
@app.route('/ask', methods=['POST'])
def ask():
    if 'username' not in session: return jsonify({"response": "Oturum açmalısınız."})
    if not GROQ_API_KEY: return jsonify({"response": "API Anahtarı bulunamadı!"})
    
    user_query = request.json.get('prompt', '').strip()
    username = session['username']
    history_file = f"history_{username}.json"
    history = veri_oku(history_file, [])

    # Papağanlığı önlemek için sistem mesajı düzeltildi
    messages = [{"role": "system", "content": "Senin adın DABI. Hüseyin Bey'in asistanısın. Kısa ve öz cevap ver."}]
    for chat in history[-10:]:
        messages.append({"role": "user", "content": chat['user']})
        messages.append({"role": "assistant", "content": chat['ai']})
    messages.append({"role": "user", "content": user_query})

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL_NAME, "messages": messages, "temperature": 0.7}

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60, verify=False)
        if response.status_code == 200:
            ai_res = response.json()['choices'][0]['message']['content'].strip()
            history.append({"user": user_query, "ai": ai_res})
            veri_yaz(history_file, history)
            return jsonify({"response": ai_res})
        elif response.status_code == 429:
            return jsonify({"response": "Hüseyin Bey, şu an çok yoğunum. Lütfen 10 saniye sonra tekrar sorun."})
        else:
            return jsonify({"response": f"DABI şu an meşgul (Hata: {response.status_code})"})
    except Exception as e:
        return jsonify({"response": "Bağlantı hatası oluştu."})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)