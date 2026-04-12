import os
import google.generativeai as genai
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. സെറ്റിംഗ്സ് ---
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"
TELEGRAM_BOT_TOKEN = "8667254663:AAEOFGclaisKrfHGoVQUTgPE1ojU1WfDJUo"

# Render-ൽ നൽകിയ Environment Variable ഇവിടെ ഉപയോഗിക്കുന്നു
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
REPO_NAME = "aidatagithu-jpg/Ai" 

# ഗ്ലോബൽ വേരിയബിൾ
repo = None

# --- 2. GitHub കണക്ഷൻ സെറ്റപ്പ് ---
def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            print(f"GitHub Connected to {REPO_NAME} ✅")
        else:
            print("Error: GITHUB_TOKEN not found in Environment Variables!")
    except Exception as e:
        repo = None
        print(f"GitHub Connection Failed: {e}")

connect_github()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. Render Health Check ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 4. ഫംഗ്ഷനുകൾ ---

def get_info_from_github():
    global repo
    if repo is None:
        connect_github() # കണക്ഷൻ പോയെങ്കിൽ വീണ്ടും ശ്രമിക്കുന്നു
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

def save_info_to_github(text):
    global repo
    if repo is None:
        connect_github()
        if repo is None: return False, "Could not connect to GitHub"
    
    file_path = "data.txt"
    try:
        try:
            contents = repo.get_contents(file_path)
            old_data = contents.decoded_content.decode("utf-8")
            new_data = old_data + "\n" + text
            repo.update_file(contents.path, "bot_update", new_data, contents.sha)
        except:
            repo.create_file(file_path, "bot_create", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. ബോട്ട് കമാൻഡുകൾ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! ഗിറ്റ്‌ഹബ്ബ് എൻവയോൺമെന്റ് സെറ്റപ്പ് പൂർത്തിയായി. /add ഉപയോഗിച്ച് വിവരങ്ങൾ ചേർക്കാം.")

async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = " ".join(context.args)
    if not val:
        await update.message.reply_text("വിവരം ചേർക്കാൻ /add [text] എന്ന് നൽകുക.")
        return
    
    msg = await update.message.reply_text("സേവ് ചെയ്യുന്നു... ⏳")
    status, error_msg = save_info_to_github(val)
    
    if status:
        await msg.edit_text(f"വിജയകരമായി സേവ് ചെയ്തു! ✅\nData: {val}")
    else:
        await msg.edit_text(f"സേവ് ചെയ്യാൻ പറ്റിയില്ല ❌\nError: {error_msg}")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    stored_data = get_info_from_github()
    
    prompt = f"റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ് നീ. ഈ ഡാറ്റ ഉപയോഗിച്ച് മറുപടി നൽകുക: {stored_data}\n\nUser: {user_text}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except:
        await update.message.reply_text("ജെമിനിക്ക് മറുപടി നൽകാൻ കഴിയുന്നില്ല.")

# --- 6. മെയിൻ ---
if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_data))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_chat))
    
    print("Bot is Polling...")
    app.run_polling()
