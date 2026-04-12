import os
import google.generativeai as genai
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. സെറ്റിംഗ്സ് ---
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"
TELEGRAM_BOT_TOKEN = "8667254663:AAED7HDnMEYodIDqy-u7Z_7ffok4POicySQ"
# നിങ്ങളുടെ പുതിയ ടോക്കൺ
GITHUB_TOKEN = "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"
# നിങ്ങൾ പറഞ്ഞ ശരിയായ റിപ്പോസിറ്ററി പേര്
REPO_NAME = "aidatagithub-jpg/Ai" 

# --- 2. കണക്ഷൻ സെറ്റപ്പ് ---
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    print("GitHub കണക്ട് ആയി! ✅")
except Exception as e:
    print(f"GitHub Connection Error: {e}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. വെബ് സെർവർ (Render Web Service-ന് വേണ്ടി) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 4. GitHub ഡാറ്റാബേസ് ഫംഗ്ഷനുകൾ ---

def get_data_from_github():
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except Exception as e:
        print(f"Read Error: {e}")
        return ""

def save_to_github(new_text):
    file_path = "data.txt"
    try:
        try:
            # നിലവിലുള്ള ഫയൽ അപ്‌ഡേറ്റ് ചെയ്യുന്നു
            contents = repo.get_contents(file_path)
            old_data = contents.decoded_content.decode("utf-8")
            updated_data = old_data + "\n" + new_text
            repo.update_file(contents.path, "Bot updated data", updated_data, contents.sha)
        except:
            # ഫയൽ ഇല്ലെങ്കിൽ പുതിയത് ഉണ്ടാക്കുന്നു
            repo.create_file(file_path, "Initial commit", new_text)
        return True
    except Exception as e:
        print(f"Save Error: {e}")
        return False

# --- 5. ബോട്ട് കമാൻഡുകൾ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! എ വൺ മ്യൂസിക് ബോട്ട് ഇപ്പോൾ ഗിറ്റ്‌ഹബ്ബ് വഴി ഡാറ്റ സേവ് ചെയ്യാൻ റെഡിയാണ്.")

async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_add = " ".join(context.args)
    if not text_to_add:
        await update.message.reply_text("വിവരം ചേർക്കാൻ /add [വിവരം] എന്ന് ടൈപ്പ് ചെയ്യുക.")
        return
    
    msg = await update.message.reply_text("GitHub-ലേക്ക് സേവ് ചെയ്യുന്നു... ⏳")
    if save_to_github(text_to_add):
        await msg.edit_text(f"വിവരം വിജയകരമായി പഠിച്ചു! ✅\n\nസേവ് ചെയ്തത്: {text_to_add}")
    else:
        await msg.edit_text("ക്ഷമിക്കണം, ഡാറ്റ സേവ് ചെയ്യാൻ കഴിഞ്ഞില്ല. ലോഗ്സ് പരിശോധിക്കുക.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    # GitHub-ൽ നിന്ന് വിവരങ്ങൾ എടുക്കുന്നു
    stored_info = get_data_from_github()
    
    prompt = f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. താഴെ നൽകിയിട്ടുള്ള വിവരങ്ങൾ മാത്രം ഉപയോഗിച്ച് ചോദ്യങ്ങൾക്ക് മറുപടി നൽകുക. വിവരം ലഭ്യമല്ലെങ്കിൽ എനിക്കറിയില്ല എന്ന് പറയുക:\n\n{stored_info}\n\nചോദ്യം: {user_query}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        await update.message.reply_text("മറുപടി നൽകാൻ എനിക്ക് ഇപ്പോൾ സാധിക്കുന്നില്ല.")

# --- 6. മെയിൻ ഫംഗ്ഷൻ ---

if __name__ == '__main__':
    # Render-ന് വേണ്ടിയുള്ള വെബ് സർവർ ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യുന്നു
    threading.Thread(target=run_health_check, daemon=True).start()
    
    # ബോട്ട് ആപ്ലിക്കേഷൻ സെറ്റപ്പ്
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_data))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("ബോട്ട് പ്രവർത്തിച്ചു തുടങ്ങി...")
    app.run_polling()
