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
GROQ_API_KEY = "gsk_9PA1BYon?51GSmkXqS5rWGdyb3FYr4dHqRzrAZGFuGjpMyPihONv" # സുരക്ഷയ്ക്കായി കീ ശരിയാണോ എന്ന് പരിശോധിക്കുക

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
        self.wfile.write(b"A One AI is Running and Learning")

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
            # പുതിയ ഡാറ്റ താഴെ ചേർക്കുന്നു
            new_content = old_data + "\n" + text
            repo.update_file(contents.path, "bot_learning_update", new_content, contents.sha)
        except:
            repo.create_file(file_path, "bot_init_data", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. ബോട്ട് കമാൻഡുകൾ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! ഞാൻ A One AI. എനിക്ക് നൽകിയ ഡാറ്റ നോക്കി മറുപടി നൽകാൻ ഞാൻ ഇപ്പോൾ കൂടുതൽ ശ്രദ്ധിക്കും. ⚡")

async def add_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = " ".join(context.args)
    if not user_data:
        await update.message.reply_text("വിവരങ്ങൾ ചേർക്കാൻ /add [വിവരം] എന്ന് നൽകുക.")
        return
    
    success, msg = save_to_github(user_data)
    if success:
        await update.message.reply_text("ഈ വിവരം ഞാൻ പഠിച്ചു കഴിഞ്ഞു. ഇനി ഇതിനെക്കുറിച്ച് ചോദിക്കാം ✅")
    else:
        await update.message.reply_text(f"എറർ: {msg}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    db_data = get_stored_data()
    
    # ഫയലിലെ ഏറ്റവും പുതിയ 5000 അക്ഷരങ്ങൾ എടുക്കുന്നു (അവസാനത്തെ മാറ്റങ്ങൾക്കാണ് മുൻഗണന)
    limit_data = db_data[-5000:] if len(db_data) > 5000 else db_data

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"നിന്റെ പേര് A One AI. നീ റിഷാമിന്റെ (Risham) പേഴ്സണൽ അസിസ്റ്റന്റ് ആണ്. മലയാളത്തിൽ മറുപടി നൽകുക. താഴെ നൽകിയിരിക്കുന്ന ഡാറ്റയ്ക്ക് ഏറ്റവും ഉയർന്ന മുൻഗണന നൽകുക. ചോദ്യത്തിനുള്ള ഉത്തരം ഈ ഡാറ്റയിൽ ഉണ്ടെങ്കിൽ അത് മാത്രം പറയുക. ഡാറ്റ: {limit_data}"
                },
                {
                    "role": "user", 
                    "content": user_input
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1, # AI-യുടെ സ്വന്തം ഭാവന കുറയ്ക്കാൻ 0.1 ആക്കി
        )
        await update.message.reply_text(chat_completion.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"ക്ഷമിക്കണം, ഒരു എറർ വന്നു: {str(e)}")

# --- 6. റൺ ബോട്ട് ---

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_info))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    
    print("A One AI is Running...")
    app.run_polling()
