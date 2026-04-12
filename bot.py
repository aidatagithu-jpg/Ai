import os
import google.generativeai as genai
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. സെറ്റിംഗ്സ് ---
# നിങ്ങളുടെ പുതിയ ടെലിഗ്രാം ബോട്ട് ടോക്കൺ ഇവിടെ നൽകി
TELEGRAM_BOT_TOKEN = "8667254663:AAEOFGclaisKrfHGoVQUTgPE1ojU1WfDJUo"
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"

# Render Environment Variable-ൽ നിന്ന് ടോക്കൺ എടുക്കുന്നു
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "aidatagithu-jpg/Ai"

# ഗ്ലോബൽ വേരിയബിൾ
repo = None

# --- 2. GitHub കണക്ഷൻ ഫംഗ്ഷൻ ---
def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            print(f"GitHub Connected to {REPO_NAME} ✅")
            return True
        else:
            print("Error: GITHUB_TOKEN not found in Render Environment!")
            return False
    except Exception as e:
        repo = None
        print(f"GitHub Connection Failed: {e}")
        return False

# തുടക്കത്തിൽ തന്നെ കണക്ട് ചെയ്യാൻ ശ്രമിക്കുന്നു
connect_github()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. Render Health Check (Web Service) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 4. ഡാറ്റാബേസ് ഫംഗ്ഷനുകൾ ---

def get_data():
    global repo
    if repo is None: connect_github()
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

def save_data(text):
    global repo
    if repo is None:
        if not connect_github():
            return False, "GitHub Connection not established"
    
    file_path = "data.txt"
    try:
        try:
            # ഫയൽ ഉണ്ടെങ്കിൽ അപ്‌ഡേറ്റ് ചെയ്യുന്നു
            contents = repo.get_contents(file_path)
            old_data = contents.decoded_content.decode("utf-8")
            new_data = old_data + "\n" + text
            repo.update_file(contents.path, "bot_update", new_data, contents.sha)
        except:
            # ഫയൽ ഇല്ലെങ്കിൽ പുതിയത് ഉണ്ടാക്കുന്നു
            repo.create_file(file_path, "bot_create", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. ബോട്ട് കമാൻഡുകൾ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ! പുതിയ ടോക്കൺ സെറ്റപ്പ് പൂർത്തിയായി. /add [വിവരം] ഉപയോഗിച്ച് ഡാറ്റ ചേർക്കാം.")

async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = " ".join(context.args)
    if not val:
        await update.message.reply_text("സേവ് ചെയ്യാൻ /add കഴിഞ്ഞു വിവരം ടൈപ്പ് ചെയ്യുക.")
        return
    
    msg = await update.message.reply_text("GitHub-ലേക്ക് സേവ് ചെയ്യുന്നു... ⏳")
    status, error_msg = save_data(val)
    
    if status:
        await msg.edit_text(f"സേവ് ചെയ്തു! ✅\nData: {val}")
    else:
        # ഇവിടെ കൃത്യമായ എറർ മെസ്സേജ് കാണിക്കും
        await msg.edit_text(f"സേവ് ചെയ്യാൻ പറ്റിയില്ല ❌\nError: {error_msg}")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    stored_data = get_data()
    
    # ഡാറ്റ ഉണ്ടെങ്കിൽ അത് അസിസ്റ്റന്റിന് നൽകുന്നു
    prompt = f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. ഈ ഡാറ്റ ഉപയോഗിച്ച് മറുപടി നൽകുക: {stored_data}\n\nUser Question: {user_text}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except:
        await update.message.reply_text("ജെമിനി ഇപ്പോൾ ലഭ്യമല്ല.")

# --- 6. ബോട്ട് ലോഞ്ചിംഗ് ---

if __name__ == '__main__':
    # Render-ന് വേണ്ടി വെബ് സെർവർ സ്റ്റാർട്ട് ചെയ്യുന്നു
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_data))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_chat))
    
    print("Bot is Polling...")
    app.run_polling()
