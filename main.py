# main.py
# ---------------- CONFIG ---------------- #
#GEMINI_API_KEY = "AIzaSyDzzq2WYGyeGdF4kjfvCCv5aNZcGHHNd5k"        # 🔑 Replace with your Gemini API key
#TELEGRAM_TOKEN = "8473657110:AAHL7HPMCuy2FnjL9OA7e0PFjMAa-rAeVjU"    # 🔑 Replace with your Telegram bot token

# main.py
import os
from flask import Flask, request
import google.generativeai as genai
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters

# ---------------- CONFIG ---------------- #
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Set in Render Environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Set in Render Environment

# ---------------- INIT GEMINI ---------------- #
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")  # Adjust if needed

# ---------------- SAMPLE DATA ---------------- #
vocab_list = [
    {"kanji": "曖昧", "reading": "あいまい", "meaning": "ambiguous", "japanese_def": "はっきりしないこと"},
    {"kanji": "妥協", "reading": "だきょう", "meaning": "compromise", "japanese_def": "お互いに譲ること"},
]

grammar_list = [
    {"point": "〜わけではない", "meaning": "it does not mean that ...", "example": "高い料理が必ず美味しいわけではない。"},
]

dokkai_list = [
    {"question": "この文章の主題は何ですか？", "options": ["環境問題", "経済成長"], "answer": "環境問題"},
]

# ---------------- USER DATA ---------------- #
user_sessions = {}
current_quiz_type = {}
current_options = {}

# ---------------- TELEGRAM BOT ---------------- #
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# ---------------- HELPER ---------------- #
def get_user_id(update: Update):
    return str(update.effective_user.id)

# ---------------- COMMAND HANDLERS ---------------- #
def start(update, context):
    user_id = get_user_id(update)
    user_sessions[user_id] = []
    update.message.reply_text(
        "🤖 JLPT N1 Study Bot Ready!\n"
        "Use commands:\n/vocab /grammar /dokkai /progress\nOr chat naturally!"
    )

def vocab(update, context):
    user_id = get_user_id(update)
    item = vocab_list[0]  # Example: pick first vocab
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"vocab {item['kanji']}"]})
    text = f"Kanji: {item['kanji']}\nReading: {item['reading']}\nMeaning: {item['meaning']}\nJapanese Definition: {item['japanese_def']}"
    update.message.reply_text(text)

def grammar(update, context):
    user_id = get_user_id(update)
    item = grammar_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"grammar {item['point']}"]})
    text = f"Grammar Point: {item['point']}\nMeaning: {item['meaning']}\nExample: {item['example']}"
    update.message.reply_text(text)

def dokkai(update, context):
    user_id = get_user_id(update)
    item = dokkai_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"dokkai {item['question']}"]})
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(item['options'])])
    text = f"Question: {item['question']}\nOptions:\n{options_text}"
    update.message.reply_text(text)

def progress(update, context):
    user_id = get_user_id(update)
    session = user_sessions.get(user_id, [])
    update.message.reply_text(f"You have interacted {len(session)} times with the bot.")

# ---------------- CHAT FALLBACK ---------------- #
def chat(update, context):
    user_id = get_user_id(update)
    user_sessions.setdefault(user_id, [])
    user_input = update.message.text
    user_sessions[user_id].append({"role": "user", "parts": [user_input]})
    try:
        response = model.generate_content(user_sessions[user_id])
        reply_text = getattr(response, "text", str(response))
        user_sessions[user_id].append({"role": "model", "parts": [reply_text]})
        update.message.reply_text(reply_text)
    except Exception as e:
        update.message.reply_text("⚠️ Gemini API error. Please try again later.")

# ---------------- ADD HANDLERS ---------------- #
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("vocab", vocab))
dispatcher.add_handler(CommandHandler("grammar", grammar))
dispatcher.add_handler(CommandHandler("dokkai", dokkai))
dispatcher.add_handler(CommandHandler("progress", progress))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

# ---------------- FLASK APP ---------------- #
app = Flask("JLPT_N1_Bot")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "JLPT N1 Bot is running ✅"

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    # Set webhook on Render
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")

    # Run Flask server
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
