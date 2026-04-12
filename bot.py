import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ലൈബ്രറികൾ ഇംപോർട്ട് ചെയ്യുന്നു
try:
    import google.generativeai as genai
    from github import Github
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
except ImportError:
    print("Error: ആവശ്യമായ ലൈബ്രറികൾ ഇൻസ്റ്റാൾ ചെയ്തിട്ടില്ല!")

# --- 1. കോൺഫിഗറേഷൻ ---
TELEGRAM_BOT_TOKEN = "8667254663:AAFB1Ns9yivnoLkaInSe7g_461BtywSC1pM"
GEMINI_API_KEY = "AIzaSyBzML2i4oW-CuAJ3ZYCqbQHq0fZeAxUX2s"

# Render-ൽ സെറ്റ് ചെയ്ത ടോക്കൺ ഇവിടെ എടുക്കുന്നു
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
REPO_NAME = "aidatagithu-jpg/Ai"

# ഗ്ലോബൽ വേരിയബിൾ
repo = None

# --- 2. കണക്ഷനുകൾ ---

def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            print(f"GitHub Connected to {REPO_NAME} ✅")
            return True
        else:
            print("GITHUB_TOKEN കണ്ടെത്തിയില്ല! Render settings പരിശോധിക്കുക.")
            return False
    except Exception as e:
        print(f"GitHub Connection Error: {e}")
        return False

# തുടക്കത്തിൽ തന്നെ കണക്ട് ചെയ്യുന്നു
connect_github()

# Gemini 2.0 Flash സെറ്റപ്പ്
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# --- 3. Render Health Check (Web Server) ---
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
    if repo is None:
        if not connect_github(): return False, "GitHub Connection Failed"
    
    file_path = "data.txt"
    try:
        try:
            # നിലവിലുള്ള ഡാറ്റയിലേക്ക് പുതിയത് ചേർക്കുന്നു
            contents = repo.get_contents(file_path)
            old_data = contents.decoded_content.decode("utf-8")
            new_data = old_data + "\n" + text
            repo.update_file(contents.path, "update_bot", new_data, contents.sha)
        except:
            # ഫയൽ ഇല്ലെങ്കിൽ പുതിയത് നിർമ്മിക്കുന്നു
            repo.create_file(file_path, "create_bot", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

# --- 5. ബോട്ട് കമാൻഡ് ഹാൻഡ്ലേഴ്സ് ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! എ വൺ മ്യൂസിക് ബോട്ട് (Gemini 2.0 Flash) റെഡിയാണ്.\n\nവിവരങ്ങൾ ചേർക്കാൻ /add [text] എന്ന് ഉപയോഗിക്കുക.")

async def add_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = " ".join(context.args)
    if not user_data:
        await update.message.reply_text("സേവ് ചെയ്യേണ്ട വിവരങ്ങൾ നൽകുക. ഉദാഹരണം: /add സംശയങ്ങൾക്ക് റിഷാമിനെ വിളിക്കുക")
        return
    
    status_msg = await update.message.reply_text("സേവ് ചെയ്യുന്നു... ⏳")
    success, msg = save_to_github(user_data)
    
    if success:
        await status_msg.edit_text(f"വിജയകരമായി സേവ് ചെയ്തു ✅\nData: {user_data}")
    else:
        await status_msg.edit_text(f"സേവ് ചെയ്യാൻ പറ്റിയില്ല ❌\nError: {msg}")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    db_data = get_stored_data()
    
    # പ്രോംപ്റ്റ് സെറ്റിംഗ്സ്
    prompt = f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. താഴെ നൽകിയിരിക്കുന്ന ഡാറ്റ ഉപയോഗിച്ച് മറുപടി നൽകുക: {db_data}\n\nUser Question: {user_input}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"ജെമിനി ഇപ്പോൾ ലഭ്യമല്ല. എറർ: {str(e)}")

# --- 6. ബോട്ട് റൺ ചെയ്യുന്നു ---

if __name__ == '__main__':
    # Render-ന് വേണ്ടി വെബ് സെർവർ ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യുന്നു
    threading.Thread(target=run_health_check, daemon=True).start()
    
    # ബോട്ട് ആപ്ലിക്കേഷൻ സെറ്റപ്പ്
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # കമാൻഡുകൾ ആഡ് ചെയ്യുന്നു
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_info))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    
    print("Bot is Polling...")
    app.run_polling()
