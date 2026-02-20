import hashlib
import telebot
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIGURATION (Via Variables d'Environnement sur Render) ---
API_TOKEN = os.getenv('TELEGRAM_TOKEN', '7446621690:AAE5q_e3AzYcW2Uon9Wg6GuRbs2Tj8zCg50')
ADMIN_ID = int(os.getenv('ADMIN_ID', '5849867789'))
SECRET_SALT = "GAMING_PRO_SECURE_2026"

bot = telebot.TeleBot(API_TOKEN)

# --- SERVEUR WEB POUR RENDER (Health Check) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    port = int(os.getenv('PORT', '8080'))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- LOGIQUE DU BOT ---
def generate_license_key(hwid):
    data = hwid.strip() + SECRET_SALT
    sha256_hash = hashlib.sha256(data.encode()).hexdigest()
    return sha256_hash[:16].upper()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "👋 Bot de Licence en ligne sur le Cloud ! Envoyez-moi un Code Machine.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.from_user.id != ADMIN_ID:
        return
    hwid = message.text.strip()
    if len(hwid) < 5:
        bot.reply_to(message, "❌ Code invalide.")
        return
    try:
        key = generate_license_key(hwid)
        bot.send_message(message.chat.id, f"✅ *Clé :* `{key}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Erreur")

if __name__ == "__main__":
    # Lancer le serveur de santé dans un thread séparé pour Render
    threading.Thread(target=run_health_server, daemon=True).start()
    print("Bot en cours d'exécution sur le Cloud...")
    bot.infinity_polling()
