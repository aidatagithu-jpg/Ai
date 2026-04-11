import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, db
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- സെറ്റിംഗ്സ് ---
GEMINI_API_KEY = "AIzaSyBS31EaBWBCno_iEp2jr-URnzcvJ2_ZHDQ"
TELEGRAM_BOT_TOKEN = "8667254663:AAED7HDnMEYodIDqy-u7Z_7ffok4POicySQ"
FIREBASE_DB_URL = "https://a-one-chat-19ad6-default-rtdb.firebaseio.com"

# 1. Firebase Initialize
# serviceAccountKey.json ഫയൽ നിങ്ങളുടെ ഫോൾഡറിൽ ഉണ്ടെന്ന് ഉറപ്പുവരുത്തുക
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
    print("Firebase കണക്ട് ആയി! ✅")
except Exception as e:
    print(f"Firebase Error: {e}")

# 2. Gemini Setup
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ഡാറ്റ Firebase-ലേക്ക് സേവ് ചെയ്യാൻ (/add)
async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_to_add = " ".join(context.args)
    if not text_to_add:
        await update.message.reply_text("വിവരം ചേർക്കാൻ: /add വിവരം")
        return
    
    try:
        ref = db.reference('a_one_bot_data')
        ref.push().set(text_to_add)
        await update.message.reply_text("വിവരം ക്ലൗഡിൽ സേവ് ചെയ്തു! ☁️")
    except Exception as e:
        await update.message.reply_text(f"സേവ് ചെയ്യാൻ പറ്റിയില്ല: {e}")

# മറുപടി നൽകാൻ
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_query = update.message.text
    
    # Firebase-ൽ നിന്ന് എല്ലാ ഡാറ്റയും എടുക്കുന്നു
    ref = db.reference('a_one_bot_data')
    stored_data_dict = ref.get()
    
    stored_text = ""
    if isinstance(stored_data_dict, dict):
        stored_text = "\n".join(stored_data_dict.values())
    elif isinstance(stored_data_dict, list):
        # ലിസ്റ്റ് ആണെങ്കിൽ നള്ളുകൾ ഒഴിവാക്കി ജോയിൻ ചെയ്യുന്നു
        stored_text = "\n".join([str(i) for i in stored_data_dict if i is not None])

    prompt = f"നീ റിഷാമിന്റെ അസിസ്റ്റന്റ് ആണ്. താഴെ പറയുന്ന വിവരങ്ങൾ മാത്രം ഉപയോഗിച്ച് മറുപടി നൽകുക. ഇല്ലെങ്കിൽ 'എനിക്കറിയില്ല' എന്ന് പറയുക:\n\n{stored_text}\n\nചോദ്യം: {user_query}"
    
    try:
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("ക്ഷമിക്കണം, മറുപടി നൽകാൻ കഴിഞ്ഞില്ല.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("add", add_data))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("ബോട്ട് ഓൺ ആയി...")
    app.run_polling()
