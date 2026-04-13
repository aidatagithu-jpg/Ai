import os
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from github import Github
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- 1. കോൺഫിഗറേഷൻ ---
TELEGRAM_BOT_TOKEN = "8667254663:AAHn5yjPzs948JkUeDtci_hMiC62LXSh-Rg"
HF_TOKEN = "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"
# കൂടുതൽ മികച്ച Llama 3.1 8B മോഡൽ
API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3.1-8B-Instruct"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") 
REPO_NAME = "aidatagithu-jpg/Ai"

repo = None

# --- 2. കണക്ഷനുകൾ ---
def connect_github():
    global repo
    try:
        if GITHUB_TOKEN:
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(REPO_NAME)
            return True
        return False
    except:
        return False

connect_github()

# --- 3. ഡാറ്റാബേസ് ഫംഗ്ഷനുകൾ ---
def get_stored_data():
    global repo
    if repo is None: connect_github()
    try:
        contents = repo.get_contents("data.txt")
        return contents.decoded_content.decode("utf-8")
    except:
        return ""

# --- 4. പ്രൊഫഷണൽ AI ലോജിക് ---
def get_ai_response(user_input, context_data, user_name):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # പ്രൊഫഷണൽ സിസ്റ്റം ഇൻസ്ട്രക്ഷൻ
    system_prompt = (
        f"You are A One AI, a professional multilingual assistant developed by Risham. "
        f"Respond in the same language the user uses. Be helpful, polite, and accurate. "
        f"Use the following knowledge base if relevant: {context_data}"
    )
    
    prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 800, 
            "temperature": 0.4, # സംഭാഷണം കൂടുതൽ സ്വാഭാവികമാക്കാൻ
            "top_p": 0.9,
            "return_full_text": False
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()[0]['generated_text']
        elif response.status_code == 503: # മോഡൽ ലോഡ് ആകുന്നുണ്ടെങ്കിൽ
            return "AI is warming up. Please try again in 10 seconds."
        else:
            return "I am experiencing some technical difficulties. Please try again later."
    except:
        return "Connection error. Please check your internet."

# --- 5. ബോട്ട് ഹാൻഡ്‌ലേഴ്‌സ് ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Welcome to **A One AI**!\n\n"
        "I am your professional assistant, capable of understanding multiple languages. "
        "How can I help you today?\n\n"
        "Developed by **Risham**."
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_name = update.effective_user.first_name
    
    # ടൈപ്പിംഗ് സ്റ്റാറ്റസ് കാണിക്കാൻ
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    db_data = get_stored_data()
    limit_data = db_data[-3000:] if len(db_data) > 3000 else db_data
    
    reply = get_ai_response(user_input, limit_data, user_name)
    await update.message.reply_text(reply)

# --- 6. റൺ ബോട്ട് ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
    
    print("A One AI Professional is Live...")
    app.run_polling()
