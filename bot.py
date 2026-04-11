import os
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- 1. സെറ്റിംഗ്സ് ---
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"
TELEGRAM_BOT_TOKEN = "8667254663:AAED7HDnMEYodIDqy-u7Z_7ffok4POicySQ"
FIREBASE_DB_URL = "https://a-one-chat-19ad6-default-rtdb.firebaseio.com"

# --- 2. ഫയർബേസ് കണക്ഷൻ ---
json_file = "serviceAccountKey.json"
try:
    if not firebase_admin._apps:
        if os.path.exists(json_file):
            cred = credentials.Certificate(json_file)
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
            print("Firebase കണക്ട് ആയി! ✅")
except Exception as e:
    print(f"Firebase Error: {e}")

# --- 3. ജെമിനി AI സെറ്റപ്പ് ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 4. വെബ് സെർവർ (Render Web Service-ന് വേണ്ടി) ---
# ഇത് ചെയ്തില്ലെങ്കിൽ Render ബോട്ട് ഓഫ് ആക്കും
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 5. ബോട്ട് ഫംഗ്ഷനുകൾ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! എ വൺ മ്യൂസിക് ബോട്ട് റെഡിയാണ്.")

async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_add = " ".join(context.args)
    if not text_to_add:
        await update.message.reply_text("/add [വിവരം] എന്ന് നൽകുക")
        return
    try:
        db.reference('a_one_bot_data').push().set(text_to_add)
        await update.message.reply_text(f"പഠിച്ചു കഴിഞ്ഞു ✅")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    try:
        ref = db.reference('a_one_bot_data')
        data = ref.get()
        stored_text = "\n".join(data.values()) if isinstance(data, dict) else ""
        prompt = f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. താഴെ ഉള്ള വിവരങ്ങൾ നോക്കി മാത്രം മറുപടി നൽകുക:\n\n{stored_text}\n\nചോദ്യം: {user_query}"
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except:
        await update.message.reply_text("ക്ഷമിക്കണം, മറുപടി നൽകാൻ പറ്റിയില്ല.")

# --- 6. ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുന്നു ---
if __name__ == '__main__':
    # വെബ് സെർവർ ഒരു സെപ്പറേറ്റ് ത്രെഡിൽ റൺ ചെയ്യുന്നു
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_data))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Web Service ബോട്ട് ഓൺ ആയി...")
    app.run_polling()
