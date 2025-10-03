# main.py
# ---------------- CONFIG ---------------- #
#GEMINI_API_KEY = "AIzaSyDzzq2WYGyeGdF4kjfvCCv5aNZcGHHNd5k"        # 🔑 Replace with your Gemini API key
#TELEGRAM_TOKEN = "8473657110:AAHL7HPMCuy2FnjL9OA7e0PFjMAa-rAeVjU"    # 🔑 Replace with your Telegram bot token

import os
import threading
from flask import Flask
import random
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- CONFIG ---------------- #
GEMINI_API_KEY = os.getenv("AIzaSyDzzq2WYGyeGdF4kjfvCCv5aNZcGHHNd5k")       # Set this in Render Environment
TELEGRAM_TOKEN = os.getenv("8473657110:AAHL7HPMCuy2FnjL9OA7e0PFjMAa-rAeVjU")      # Set this in Render Environment

# ---------------- INIT GEMINI ---------------- #
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")  # Adjust based on available model

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
user_data = {}
current_quiz_type = {}
current_options = {}
user_sessions = {}

def get_user_id(update: Update):
    return str(update.effective_user.id)

# ---------------- COMMANDS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    user_sessions[user_id] = []
    await update.message.reply_text(
        "🤖 JLPT N1 Study Bot Ready!\n"
        "Use:\n/vocab /grammar /dokkai /progress\nOr chat naturally!"
    )

# ---------------- CHAT FALLBACK ---------------- #
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
    except Exception as e:
        await update.message.reply_text("⚠️ Gemini API error. Please try again later.")

# ---------------- TELEGRAM BOT RUN ---------------- #
def run_telegram():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("🤖 Telegram Bot running...")
    app.run_polling()

# ---------------- FLASK WRAPPER ---------------- #
flask_app = Flask("JLPT_N1_Bot")

@flask_app.route("/")
def index():
    return "JLPT N1 Bot is running ✅"

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    # Start Telegram bot in background thread
    threading.Thread(target=run_telegram, daemon=True).start()
    
    # Run Flask web server for Render
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
