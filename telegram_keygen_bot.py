import hashlib
import telebot
import os
import threading
import time
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION ---
API_TOKEN = os.getenv('TELEGRAM_TOKEN', '7446621690:AAE5q_e3AzYcW2Uon9Wg6GuRbs2Tj8zCg50')
ADMIN_ID = int(os.getenv('ADMIN_ID', '5849867789'))

# Salts MUST match the ones in the Flutter apps
SALTS = {
    "elvago": "ELVAGO_MEXICAN_FOOD_2026",
    "gaming": "GAMING_PRO_SECURE_2026"
}

# In-memory session: {chat_id: {"app": str, "hwid": str, "type": str, "duration": int}}
user_sessions = {}

bot = telebot.TeleBot(API_TOKEN)

# --- WEB SERVER FOR HEALTH CHECK ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Keygen Bot is alive!")

def run_health_server():
    port = int(os.getenv('PORT', '8080'))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- VALIDATION LOGIC ---
def is_valid_uuid(uuid_str):
    """Checks if the string looks like a valid Windows Device ID / UUID."""
    # Pattern: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX or similar
    # Windows Device IDs can also be just hex strings. 
    # We strip {} in the app, so we expect a clean string here.
    pattern = re.compile(r'^[A-F0-9\-]{10,50}$', re.IGNORECASE)
    return bool(pattern.match(uuid_str))

# --- GENERATION LOGIC ---
def generate_license_key(hwid, app_type, expiry_ts):
    import base64
    salt = SALTS.get(app_type, SALTS["elvago"])
    # Format: HASH(ID + SALT + EXPIRY) - EXPIRY
    data = hwid.strip().upper() + salt + str(expiry_ts)
    sha256_hash = hashlib.sha256(data.encode()).hexdigest()
    hash_part = sha256_hash[:16].upper()
    
    raw_key = f"{hash_part}-{expiry_ts}"
    # Base64 encode for Recommendation 3
    encoded_key = base64.b64encode(raw_key.encode()).decode()
    return encoded_key

def get_app_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🌮 Elvago POS", callback_data="app_elvago"),
        InlineKeyboardButton("🎮 Gaming Pro", callback_data="app_gaming")
    )
    return markup

def get_license_type_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("♾️ Unlimited", callback_data="type_unlimited"),
        InlineKeyboardButton("⏳ Free Trial", callback_data="type_trial")
    )
    return markup

def get_trial_duration_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("1 Min (TEST)", callback_data="test_0.0166"), # 1/60th of an hour
        InlineKeyboardButton("5 Min (TEST)", callback_data="test_0.0833") 
    )
    markup.add(
        InlineKeyboardButton("1 Hour", callback_data="dur_1"),
        InlineKeyboardButton("2 Hours", callback_data="dur_2")
    )
    markup.add(
        InlineKeyboardButton("24 Hours", callback_data="dur_24"),
        InlineKeyboardButton("7 Days", callback_data="dur_168")
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    user_sessions[message.chat.id] = {}
    bot.send_message(message.chat.id, "👋 *License Manager*\nChoose the application:", 
                     reply_markup=get_app_buttons(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def handle_app_selection(call):
    app_type = call.data.split('_')[1]
    user_sessions[call.message.chat.id] = {"app": app_type}
    bot.edit_message_text(f"✅ App: *{app_type.upper()}*\n\nNow, send me the **Device ID**:", 
                         call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_id_input(message):
    if message.from_user.id != ADMIN_ID: return
    session = user_sessions.get(message.chat.id)
    
    if not session or "app" not in session:
        bot.reply_to(message, "⚠️ Start with /start")
        return

    hwid = message.text.strip().replace('{', '').replace('}', '').upper()
    
    if not is_valid_uuid(hwid):
        bot.reply_to(message, "❌ *Invalid Device ID!*\nIt must be a real hardware ID (numbers, letters, hyphens).", parse_mode='Markdown')
        return

    session["hwid"] = hwid
    bot.send_message(message.chat.id, f"💻 ID: `{hwid}`\nSelect license type:", 
                     reply_markup=get_license_type_buttons(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def handle_type_selection(call):
    session = user_sessions.get(call.message.chat.id)
    if not session: return

    lic_type = call.data.split('_')[1]
    session["type"] = lic_type

    if lic_type == "unlimited":
        final_generate(call.message.chat.id)
    else:
        bot.edit_message_text("🕒 Choose trial duration:", 
                             call.message.chat.id, call.message.message_id, 
                             reply_markup=get_trial_duration_buttons())

@bot.callback_query_handler(func=lambda call: call.data.startswith('dur_') or call.data.startswith('test_'))
def handle_duration_selection(call):
    session = user_sessions.get(call.message.chat.id)
    if not session: return

    # Parse hours (float supports 1 min as 0.0166)
    hours = float(call.data.split('_')[1])
    session["duration"] = hours
    final_generate(call.message.chat.id)

def final_generate(chat_id):
    session = user_sessions.get(chat_id)
    if not session: return

    expiry_ts = 0
    if session.get("type") == "trial":
        # Current time in ms + hours in ms
        expiry_ts = int((time.time() + (session["duration"] * 3600)) * 1000)

    key = generate_license_key(session["hwid"], session["app"], expiry_ts)
    
    app_label = "🌮 ELVAGO" if session["app"] == "elvago" else "🎮 GAMING PRO"
    type_label = "LIFETIME ♾️" if expiry_ts == 0 else f"TRIAL ({session['duration']}h) ⏳"

    response = (
        f"✅ *License Generated*\n\n"
        f"📱 *App:* {app_label}\n"
        f"💻 *ID:* `{session['hwid']}`\n"
        f"🏷️ *Type:* {type_label}\n\n"
        f"🔑 *KEY:*\n`{key}`"
    )
    bot.send_message(chat_id, response, parse_mode='Markdown')
    # Clear session
    user_sessions[chat_id] = {}

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("Bot License v2 online...")
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("Bot Multi-App lancé...")
    bot.infinity_polling()
