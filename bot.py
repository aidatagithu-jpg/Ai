import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

try:
    from groq import Groq
    from github import Github
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
except ImportError:
    print("Error: ആവശ്യമായ ലൈബ്രറികൾ ഇൻസ്റ്റാൾ ചെയ്തിട്ടില്ല!")

# --- 1. കോൺഫിഗറേഷൻ ---
TELEGRAM_BOT_TOKEN = "8667254663:AAHhMj4xanwUej6jv1a_J7z3dK-TZj7JQ78"
GROQ_API_KEY = "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"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
REPO_NAME = "aidatagithu-jpg/Ai"

repo = None
client = Groq(api_key=GROQ_API_KEY)

# --- 2. കണക്ഷനുകൾ ---
def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            print("GitHub Connected ✅")
            return True
        return False
    except Exception:
        return False

connect_github()

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

# --- 4. ഡാറ്റാബേസ് ---
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
            repo.update_file(contents.path, "update", old_data + "\n" + text, contents.sha)
        except:
            repo.create_file(file_path, "create", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. കമാൻഡുകൾ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! A One AI അപ്ഡേറ്റ് ആയിട്ടുണ്ട്. ⚡")

async def add_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = " ".join(context.args)
    if not user_data:
        await update.message.reply_text("/add [text] നൽകുക.")
        return
    success, msg = save_to_github(user_data)
    await update.message.reply_text("സേവ് ചെയ്തു ✅" if success else f"എറർ: {msg}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    db_data = get_stored_data()
    
    # ഡാറ്റ ലിമിറ്റ് മറികടക്കാൻ Slice ചെയ്യുന്നു
    limit_data = db_data[-3000:] if len(db_data) > 3000 else db_data

    try:
        # പുതിയ സ്റ്റേബിൾ മോഡൽ: llama-3.1-8b-instant
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"നീ A One AI ആണ്. റിഷാമിന്റെ അസിസ്റ്റന്റ്. മലയാളത്തിൽ മറുപടി നൽകുക. ഡാറ്റ: {limit_data}"},
                {"role": "user", "content": user_input}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        await update.message.reply_text(chat_completion.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"എറർ: {str(e)}")

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_info))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    app.run_polling()
