import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ലൈബ്രറികൾ ഇംപോർട്ട് ചെയ്യുന്നു
try:
    from groq import Groq
    from github import Github
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
except ImportError:
    print("Error: ആവശ്യമായ ലൈബ്രറികൾ ഇൻസ്റ്റാൾ ചെയ്തിട്ടില്ല! (pip install groq PyGithub python-telegram-bot)")

# --- 1. കോൺഫിഗറേഷൻ ---
TELEGRAM_BOT_TOKEN = "8667254663:AAG9KWS64KCdXCJGgODp0yv9B0unuQ246Bk"
GROQ_API_KEY = "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"

# Render-ൽ സെറ്റ് ചെയ്ത GitHub ടോക്കൺ
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
REPO_NAME = "aidatagithu-jpg/Ai"

# ഗ്ലോബൽ വേരിയബിൾസ്
repo = None
client = Groq(api_key=GROQ_API_KEY)

# --- 2. കണക്ഷനുകൾ ---

def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            print(f"GitHub Connected ✅")
            return True
        return False
    except Exception as e:
        print(f"GitHub Error: {e}")
        return False

connect_github()

# --- 3. Render Health Check ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Groq Bot is Running")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 4. ഡാറ്റാബേസ് ഫംഗ്ഷനുകൾ ---

def get_stored_data():
    global repo
    if repo is None: connect_github()
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

def save_to_github(text):
    global repo
    if repo is None: connect_github()
    try:
        file_path = "data.txt"
        try:
            contents = repo.get_contents(file_path)
            old_data = contents.decoded_content.decode("utf-8")
            repo.update_file(contents.path, "bot_update", old_data + "\n" + text, contents.sha)
        except:
            repo.create_file(file_path, "bot_create", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. ബോട്ട് കമാൻഡുകൾ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! ഇപ്പോൾ ഞാൻ Groq AI ഉപയോഗിച്ചാണ് പ്രവർത്തിക്കുന്നത്. അതിവേഗത്തിൽ മറുപടികൾ ലഭിക്കും! ⚡")

async def add_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = " ".join(context.args)
    if not user_data:
        await update.message.reply_text("/add [വിവരം] നൽകുക.")
        return
    
    success, msg = save_to_github(user_data)
    if success:
        await update.message.reply_text(f"സേവ് ചെയ്തു ✅")
    else:
        await update.message.reply_text(f"എറർ ❌: {msg}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    db_data = get_stored_data()
    
    try:
        # Groq AI മറുപടി ജനറേറ്റ് ചെയ്യുന്നു
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. മലയാളത്തിൽ മറുപടി നൽകുക. ഈ ഡാറ്റ ഉപയോഗിക്കുക: {db_data}"
                },
                {
                    "role": "user",
                    "content": user_input,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        await update.message.reply_text(chat_completion.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"Groq എറർ: {str(e)}")

# --- 6. റൺ ബോട്ട് ---

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_info))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    
    print("Groq Bot is Polling...")
    app.run_polling()
