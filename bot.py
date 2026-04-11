import os
import google.generativeai as genai
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- സെറ്റിംഗ്സ് ---
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"
TELEGRAM_BOT_TOKEN = "8667254663:AAED7HDnMEYodIDqy-u7Z_7ffok4POicySQ"
GITHUB_TOKEN = "ghp_11CBUMCGI0eZQb8w0fykw4_1xSQECEePyGbDkOB7FMCGXIcnfEwH2uwwMEG8Woh62vGSXYLLV7bYSgwLsN"
# നിങ്ങളുടെ യൂസർനെയിമും റിപ്പോസിറ്ററി പേരും താഴെ നൽകുക
REPO_NAME = "Risham004/A-One-Bot" 

# GitHub കണക്ഷൻ
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    print("GitHub കണക്ട് ആയി! ✅")
except Exception as e:
    print(f"GitHub Error: {e}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- വെബ് സെർവർ (Render-ന് വേണ്ടി) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- ഫംഗ്ഷനുകൾ ---

def get_data_from_github():
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

def save_to_github(new_text):
    try:
        contents = repo.get_contents("data.txt")
        old_data = contents.decoded_content.decode("utf-8")
        updated_data = old_data + "\n" + new_text
        repo.update_file(contents.path, "Bot updated data", updated_data, contents.sha)
        return True
    except:
        # ഫയൽ ഇല്ലെങ്കിൽ പുതിയത് ഉണ്ടാക്കുന്നു
        repo.create_file("data.txt", "Initial commit", new_text)
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ഹലോ റിഷാം! എ വൺ മ്യൂസിക് ബോട്ട് റെഡിയാണ്.")

async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_add = " ".join(context.args)
    if not text_to_add:
        await update.message.reply_text("/add [വിവരം] നൽകുക")
        return
    
    msg = await update.message.reply_text("GitHub-ലേക്ക് സേവ് ചെയ്യുന്നു... ⏳")
    if save_to_github(text_to_add):
        await msg.edit_text("വിവരം സ്ഥിരമായി സേവ് ചെയ്തു! ✅")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    content = get_data_from_github()
    
    prompt = f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. താഴെ പറയുന്ന വിവരങ്ങൾ ഉപയോഗിച്ച് മറുപടി നൽകുക:\n\n{content}\n\nചോദ്യം: {user_query}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except:
        await update.message.reply_text("ക്ഷമിക്കണം, മറുപടി നൽകാൻ പറ്റിയില്ല.")

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_data))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("ബോട്ട് ലോഡ് ആയി...")
    app.run_polling()
