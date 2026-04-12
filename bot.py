import os
import google.generativeai as genai
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- സെറ്റിംഗ്സ് ---
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"
TELEGRAM_BOT_TOKEN = "8667254663:AAGrWr-lA7X-XXeQpFalF0FohhPT1jo7_Lw"
GITHUB_TOKEN = "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"
REPO_NAME = "aidatagithu-jpg/Ai" 

# GitHub കണക്ഷൻ
try:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    print("GitHub Connected! ✅")
except Exception as e:
    print(f"GitHub Auth Error: {e}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Render Health Check
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

def get_info():
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

def save_info(text):
    try:
        file_path = "data.txt"
        try:
            contents = repo.get_contents(file_path)
            old_data = contents.decoded_content.decode("utf-8")
            new_data = old_data + "\n" + text
            repo.update_file(contents.path, "update", new_data, contents.sha)
        except:
            repo.create_file(file_path, "create", text)
        return True, "Success"
    except Exception as e:
        return False, str(e)

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = " ".join(context.args)
    if not val:
        await update.message.reply_text("/add [വിവരം] നൽകുക")
        return
    
    status, msg = save_info(val)
    if status:
        await update.message.reply_text(f"സേവ് ചെയ്തു ✅: {val}")
    else:
        # ഇവിടെ കൃത്യമായ എറർ മെസ്സേജ് കാണിക്കും
        await update.message.reply_text(f"സേവ് ചെയ്യാൻ പറ്റിയില്ല ❌\nകാരണം: {msg}")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    data = get_info()
    prompt = f"Data: {data}\n\nUser: {txt}"
    try:
        res = model.generate_content(prompt)
        await update.message.reply_text(res.text)
    except:
        await update.message.reply_text("Gemini Error!")

if __name__ == '__main__':
    threading.Thread(target=run_health_check, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    app.run_polling()
