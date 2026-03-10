from flask import Flask, request, render_template, jsonify
import requests
import json
import os

app = Flask(__name__)

# --- BULUT YAPILANDIRMASI ---
# Anahtar kodun içinde DEĞİL, çalıştırılan sistemin (Replit/Render) içinde olacak.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") 
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile" 
HISTORY_FILE = "sohbet_gecmisi.json"

def hafizayi_yukle():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []

def hafizayi_kaydet(gecmis):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(gecmis[-10:], f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    user_query = request.json.get('prompt', '')
    if not user_query:
        return jsonify({"response": "Sizi dinliyorum Hüseyin Bey."})

    if not GROQ_API_KEY:
        return jsonify({"response": "Hüseyin Bey, API anahtarı sisteme tanımlanmamış."})

    chat_history = hafizayi_yukle()
    
    messages = [
        {"role": "system", "content": "Sen DABI'sin. Hüseyin Bey'in asistanısın. Kısa ve zeki Türkçe cevaplar ver."}
    ]
    
    for chat in chat_history:
        messages.append({"role": "user", "content": chat['user']})
        messages.append({"role": "assistant", "content": chat['ai']})
    
    messages.append({"role": "user", "content": user_query})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.6
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=20)
        ai_response = response.json()['choices'][0]['message']['content'].strip()
        chat_history.append({"user": user_query, "ai": ai_response})
        hafizayi_kaydet(chat_history)
        return jsonify({"response": ai_response})
    except Exception as e:
        return jsonify({"response": "Bağlantı hatası oluştu."})

if __name__ == '__main__':
    # Hem Render hem Replit için portu otomatik ayarlar
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)