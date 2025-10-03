# main.py
# ---------------- CONFIG ---------------- #
#GEMINI_API_KEY = "AIzaSyDzzq2WYGyeGdF4kjfvCCv5aNZcGHHNd5k"        # 🔑 Replace with your Gemini API key
#TELEGRAM_TOKEN = "8473657110:AAHL7HPMCuy2FnjL9OA7e0PFjMAa-rAeVjU"    # 🔑 Replace with your Telegram bot token

import random
import os
import threading
import google.generativeai as genai
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- CONFIG ---------------- #
TELEGRAM_TOKEN = os.getenv("8473657110:AAHL7HPMCuy2FnjL9OA7e0PFjMAa-rAeVjU")  # set in Render Environment
GEMINI_API_KEY = os.getenv("AIzaSyDzzq2WYGyeGdF4kjfvCCv5aNZcGHHNd5k")  # set in Render Environment

# Init Gemini
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------- SAMPLE DATA ---------------- #
vocab_list = [
    {"kanji": "曖昧", "reading": "あいまい", "meaning": "ambiguous", "japanese_def": "はっきりしないこと"},
    {"kanji": "妥協", "reading": "だきょう", "meaning": "compromise", "japanese_def": "お互いに譲ること"},
    {"kanji": "懸念", "reading": "けねん", "meaning": "concern", "japanese_def": "心配すること"},
]

grammar_list = [
    {"point": "〜わけではない", "meaning": "it does not mean that ...", "example": "高い料理が必ず美味しいわけではない。"},
    {"point": "〜ざるを得ない", "meaning": "cannot help but ...", "example": "試験があるので勉強せざるを得ない。"},
]

dokkai_list = [
    {"question": "この文章の主題は何ですか？", "options": ["環境問題", "経済成長", "教育改革"], "answer": "環境問題"},
    {"question": "筆者の意見はどれですか？", "options": ["賛成", "反対", "中立"], "answer": "賛成"},
]

# ---------------- USER DATA ---------------- #
user_data = {}

def get_user_id(update: Update):
    return str(update.effective_user.id)

# ---------------- COMMANDS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 JLPT N1 Study Bot Ready!\n"
        "Use:\n"
        "🈶 /vocab → Vocabulary quiz\n"
        "📘 /grammar → Grammar quiz\n"
        "📖 /dokkai → Reading quiz\n"
        "📊 /progress → Check your learning progress\n"
        "💬 Or just chat with me in English/Japanese!"
    )

# ---------------- QUIZZES ---------------- #
async def vocab_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(vocab_list)
    context.user_data["current_vocab"] = q
    await update.message.reply_text(
        f"🈶 What is the meaning of {q['kanji']} ({q['reading']})?\n"
        f"日本語の説明: {q['japanese_def']}"
    )

async def grammar_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(grammar_list)
    context.user_data["current_grammar"] = q
    await update.message.reply_text(
        f"📘 Grammar point: {q['point']}\nMeaning?\nExample: {q['example']}"
    )

async def dokkai_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(dokkai_list)
    context.user_data["current_dokkai"] = q
    opts = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(q['options'])])
    await update.message.reply_text(
        f"📖 {q['question']}\n{opts}\n\n(Reply with 1/2/3)"
    )

# ---------------- PROGRESS ---------------- #
async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    data = user_data.setdefault(user_id, {"vocab_mastery": {}, "grammar_mastery": {}, "quiz_scores": []})

    total_vocab = len(vocab_list)
    mastered_vocab = sum(1 for v in vocab_list if data["vocab_mastery"].get(v["kanji"], 0) >= 2)

    total_grammar = len(grammar_list)
    mastered_grammar = sum(1 for g in grammar_list if data["grammar_mastery"].get(g["point"], 0) >= 2)

    vocab_pct = (mastered_vocab / total_vocab * 100) if total_vocab else 0
    grammar_pct = (mastered_grammar / total_grammar * 100) if total_grammar else 0

    text = (
        "📊 **Your JLPT N1 Progress** 📊\n\n"
        f"🈶 Vocabulary: {mastered_vocab}/{total_vocab} mastered ({vocab_pct:.1f}%)\n"
        f"📘 Grammar: {mastered_grammar}/{total_grammar} mastered ({grammar_pct:.1f}%)\n\n"
        "👉 Keep practicing with /vocab /grammar /dokkai!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------------- CHAT (Gemini AI) ---------------- #
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    try:
        response = gemini_model.generate_content(
            f"You are a JLPT N1 tutor. Explain in English + Japanese.\nUser asked: {user_input}"
        )
        reply_text = getattr(response, "text", str(response))
        await update.message.reply_text(reply_text)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Gemini API error: {e}")

# ---------------- MAIN ---------------- #
def run_telegram():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vocab", vocab_quiz))
    app.add_handler(CommandHandler("grammar", grammar_quiz))
    app.add_handler(CommandHandler("dokkai", dokkai_quiz))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🤖 Telegram Bot running...")
    app.run_polling()

# Flask server (for Render health check)
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "JLPT N1 Bot is running!"

if __name__ == "__main__":
    threading.Thread(target=run_telegram, daemon=True).start()
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
