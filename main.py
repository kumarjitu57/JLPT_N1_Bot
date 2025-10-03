import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")

user_sessions = {}

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions[user_id] = []
    await update.message.reply_text("🤖 Bot ready!")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions.setdefault(user_id, [])
    user_input = update.message.text
    user_sessions[user_id].append({"role": "user", "parts": [user_input]})
    try:
        response = model.generate_content(user_sessions[user_id])
        reply_text = getattr(response, "text", str(response))
        user_sessions[user_id].append({"role": "model", "parts": [reply_text]})
        await update.message.reply_text(reply_text)
    except Exception:
        await update.message.reply_text("⚠️ Gemini API error.")

# Flask App
app = Flask("JLPT_N1_Bot")
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

# Webhook route
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.update_queue.put(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running ✅"

# Set webhook and run Flask
if __name__ == "__main__":
    application.bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
