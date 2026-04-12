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
    print("Error: ആവശ്യമായ ലൈബ്രറികൾ ഇൻസ്റ്റാൾ ചെയ്തിട്ടില്ല!")

# --- 1. കോൺഫിഗറേഷൻ ---
TELEGRAM_BOT_TOKEN = "8667254663:AAHhMj4xanwUej6jv1a_J7z3dK-TZj7JQ78"
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
            print("GitHub Connected ✅")
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
        self.wfile.write(b"A One AI is Running")

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
            # പുതിയ ഡാറ്റ വരിയായി ചേർക്കുന്നു
            new_content = old_data + "\n" + text
            repo.update_file(contents.path, "bot_update", new_content, contents.sha)
        except:
            repo.create_file(file_path, "bot_create", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. ബോട്ട് കമാൻഡുകൾ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! ഞാൻ A One AI. റെൻഡറിൽ സപ്പോർട്ടായ പുതിയ കോഡ് അപ്ഡേറ്റ് ചെയ്തിട്ടുണ്ട്. ⚡")

async def add_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = " ".join(context.args)
    if not user_data:
        await update.message.reply_text("വിവരങ്ങൾ ചേർക്കാൻ /add [text] എന്ന് ടൈപ്പ് ചെയ്യുക.")
        return
    
    success, msg = save_to_github(user_data)
    if success:
        await update.message.reply_text("വിവരങ്ങൾ A One AI പഠിച്ചു കഴിഞ്ഞു ✅")
    else:
        await update.message.reply_text(f"എറർ: {msg}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    db_data = get_stored_data()
    
    # പ്രധാന മാറ്റം: ഡാറ്റയുടെ വലിപ്പം 3000 അക്ഷരങ്ങളായി ചുരുക്കുന്നു (Groq എറർ ഒഴിവാക്കാൻ)
    if len(db_data) > 3000:
        db_data = db_data[-3000:]

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"നിന്റെ പേര് A One AI. നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. മലയാളത്തിൽ മറുപടി നൽകുക. ഈ ഡാറ്റാബേസ് ഉപയോഗിക്കുക: {db_data}"
                },
                {
                    "role": "user",
                    "content": user_input,
                }
            ],
            model="llama-3-8b-8192", # ലിമിറ്റ് കൂടുതലുള്ള മോഡൽ
            temperature=0.7
        )
        await update.message.reply_text(chat_completion.choices[0].message.content)
    except Exception as e:
        # ടോക്കൺ ലിമിറ്റ് എറർ വന്നാൽ ഒരു ലളിതമായ മറുപടി നൽകുന്നു
        if "rate_limit_exceeded" in str(e).lower():
            await update.message.reply_text("ക്ഷമിക്കണം, ഡാറ്റാബേസ് വളരെ വലുതാണ്. ഞാൻ ഇപ്പോൾ കുറച്ച് വിവരങ്ങൾ മാത്രം ഉപയോഗിച്ച് മറുപടി നൽകാം.")
        else:
            await update.message.reply_text(f"എറർ സംഭവിച്ചു: {str(e)}")

# --- 6. റൺ ബോട്ട് ---

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_info))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    
    print("A One AI is Polling...")
    app.run_polling()
