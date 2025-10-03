# main.py
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# ---------------- CONFIG ---------------- #
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# ---------------- INIT GEMINI ---------------- #
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")

# ---------------- DATA ---------------- #
vocab_list = [{"kanji": "曖昧", "reading": "あいまい", "meaning": "ambiguous"}]
grammar_list = [{"point": "〜わけではない", "meaning": "it does not mean that ..."}]
dokkai_list = [{"question": "この文章の主題は何ですか？", "options": ["環境問題", "経済成長"], "answer": "環境問題"}]

user_sessions = {}

def get_user_id(update: Update):
    return str(update.effective_user.id)

# ---------------- COMMAND HANDLERS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    user_sessions[user_id] = []
    await update.message.reply_text(
        "🤖 JLPT N1 Bot Ready!\nUse /vocab /grammar /dokkai /progress\nOr chat naturally!"
    )

async def vocab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    item = vocab_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"vocab {item['kanji']}"]})
    await update.message.reply_text(
        f"Kanji: {item['kanji']}\nReading: {item['reading']}\nMeaning: {item['meaning']}"
    )

async def grammar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    item = grammar_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"grammar {item['point']}"]})
    await update.message.reply_text(f"Grammar Point: {item['point']}\nMeaning: {item['meaning']}")

async def dokkai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    item = dokkai_list[0]
    user_sessions.setdefault(user_id, []).append({"role": "user", "parts": [f"dokkai {item['question']}"]})
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(item['options'])])
    await update.message.reply_text(f"Question: {item['question']}\nOptions:\n{options_text}")

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
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("vocab", vocab))
application.add_handler(CommandHandler("grammar", grammar))
application.add_handler(CommandHandler("dokkai", dokkai))
application.add_handler(CommandHandler("progress", progress))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return "ok"

@app.route("/")
def index():
    return "JLPT N1 Bot is running ✅"

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    application.bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
