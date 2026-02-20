import hashlib
import telebot

# --- CONFIGURATION ---
API_TOKEN = '7446621690:AAE5q_e3AzYcW2Uon9Wg6GuRbs2Tj8zCg50'
ADMIN_ID = 5849867789  # Seul cet ID pourra générer des clés
SECRET_SALT = "GAMING_PRO_SECURE_2026" # Doit correspondre exactement au sel dans l'App Flutter

bot = telebot.TeleBot(API_TOKEN)

def generate_license_key(hwid):
    # Même algorithme que dans lib/game_state.dart
    data = hwid.strip() + SECRET_SALT
    sha256_hash = hashlib.sha256(data.encode()).hexdigest()
    return sha256_hash[:16].upper()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Accès refusé. Vous n'êtes pas l'administrateur.")
        return
    bot.reply_to(message, "👋 Bienvenue ! Envoyez-moi le 'Code Machine' du client pour générer une clé de licence.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Accès refusé.")
        return
    
    hwid = message.text.strip()
    if len(hwid) < 5:
        bot.reply_to(message, "❌ Code Machine trop court ou invalide.")
        return
        
    try:
        license_key = generate_license_key(hwid)
        response = (
            f"✅ *Licence Générée*\n\n"
            f"🖥 *Code Machine :* `{hwid}`\n"
            f"🔑 *Clé de Licence :* `{license_key}`\n\n"
            f"Envoyez cette clé à votre client."
        )
        bot.send_message(message.chat.id, response, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Erreur : {str(e)}")

print("Bot Telegram en cours d'exécution...")
bot.infinity_polling()
