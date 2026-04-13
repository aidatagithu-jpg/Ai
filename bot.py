import os
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from github import Github, Auth
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8667254663:AAF30w1HLzLtmpeqWqjmWl7wVEf5vuOlnTA"
HF_TOKEN = "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"
API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
REPO_NAME = "aidatagithu-jpg/Ai"

repo = None

# --- 2. RENDER HEALTH CHECK ---
# Render-ലെ 'Port Binding' എറർ ഒഴിവാക്കാൻ ഇത് സഹായിക്കും
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"A One AI is Active")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 3. CONNECTIONS ---
def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            auth = Auth.Token(GITHUB_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(REPO_NAME)
            return True
        return False
    except:
        return False

connect_github()

# --- 4. DATABASE LOGIC ---
def get_stored_data():
    global repo
    if repo is None: connect_github()
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

# --- 5. AI LOGIC (PROFESSIONAL & MULTILINGUAL) ---
def get_ai_response(user_input, context_data):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # പ്രൊഫഷണൽ പേഴ്സണാലിറ്റി നിർദ്ദേശം
    system_instruction = (
        "You are A One AI, a high-quality professional assistant created by Risham. "
        "You can understand and speak all languages fluently. "
        "Always respond in the same language the user is speaking. "
        "If the user asks about specific facts, use this internal knowledge: " + context_data
    )
    
    prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_instruction}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 800, 
            "temperature": 0.4, 
            "top_p": 0.9,
            "return_full_text": False
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()[0]['generated_text']
        elif response.status_code == 503:
            return "AI is starting up. Please try again in a few seconds."
        else:
            return "Connection issues with AI. Please try later."
    except:
        return "I'm having trouble connecting right now."

# --- 6. BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **Welcome to A One AI**\n\n"
        "I am your professional multilingual assistant. "
        "I can help you with programming, general knowledge, and more.\n\n"
        "Developer: **Risham**"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    # Typing സ്റ്റാറ്റസ് കാണിക്കാൻ
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    db_data = get_stored_data()
    limit_data = db_data[-3000:] if len(db_data) > 3000 else db_data
    
    reply = get_ai_response(user_input, limit_data)
    await update.message.reply_text(reply)

# --- 7. START BOT ---
if __name__ == '__main__':
    # Health Check സെർവർ ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യുന്നു
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    
    print("A One AI (Professional Edition) is Running...")
    app.run_polling()
