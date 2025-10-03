# main.py
import os
from flask import Flask, request
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- CONFIG ---------------- #
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")      # Set in Render Environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")      # Set in Render Environment

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Please set TELEGRAM_TOKEN and GEMINI_API_KEY in your environment variables!")

# ---------------- INIT GEMINI ---------------- #
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")  # Use your preferred model

# ---------------- SAMPLE DATA ---------------- #
vocab_list = [
    {"kanji": "曖昧", "reading": "あいまい", "meaning": "ambiguous", "japanese_def": "はっきりしないこと"}
]

grammar_list = [
    {"point": "〜わけではない", "meaning": "it does not mean that ...", "example": "高い料理が必ず美味しいわけではない。"}
]

dokkai_list = [
    {"question": "この文章の主題は何ですか？", "options": ["環境問題", "経済成長"], "answer": "環境問題"}
]

# ---------------- USER DATA ---------------- #
user_sessions = {}

def get_user_id(update: Update):
    return str(update.effective_user.id)

# ---------------- COMMAND HANDLERS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    user_sessions[user_id] = []
    await update.message.reply_text(
        "🤖 JLPT N1 Study Bot Ready!\n"
        "Use commands:\n/vocab /grammar /dokkai /progress\nOr chat naturally!"
    )

async def vocab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    item = vocab_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"vocab {item['kanji']}"]})
    text = f"Kanji: {item['kanji']}\nReading: {item['reading']}\nMeaning: {item['meaning']}\nJapanese Definition: {item['japanese_def']}"
    await update.message.reply_text(text)

async def grammar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    item = grammar_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"grammar {item['point']}"]})
    text = f"Grammar Point: {item['point']}\nMeaning: {item['meaning']}\nExample: {item['example']}"
    await update.message.reply_text(text)

async def dokkai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    item = dokkai_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"dokkai {item['question']}"]})
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(item['options'])])
    text = f"Question: {item['question']}\nOptions:\n{options_text}"
    await update.message.reply_text(text)

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    session = user_sessions.get(user_id, [])
    await update.message.reply_text(f"You have interacted {len(session)} times with the bot.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    user_sessions.setdefault(user_id, [])
    user_input = update.message.text
    user_sessions[user_id].append({"role": "user", "parts": [user_input]})
    try:
        response = model.generate_content(user_sessions[user_id])
        reply_text = getattr(response, "text", str(response))
        user_sessions[user_id].append({"role": "model", "parts": [reply_text]})
        await update.message.reply_text(reply_text)
    except Exception:
        await update.message.reply_text("⚠️ Gemini API error. Please try again later.")

# ---------------- FLASK APP ---------------- #
app = Flask("JLPT_N1_Bot")

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def index():
    return "JLPT N1 Bot is running ✅"

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("vocab", vocab))
    application.add_handler(CommandHandler("grammar", grammar))
    application.add_handler(CommandHandler("dokkai", dokkai))
    application.add_handler(CommandHandler("progress", progress))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    # Set webhook
    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
    if not RENDER_URL:
        raise ValueError("RENDER_EXTERNAL_URL not set in Render environment!")
    application.bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")

    # Run Flask server
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
