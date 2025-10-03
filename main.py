# main.py
import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# ---------------- CONFIG ---------------- #
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")          # Your Telegram Bot Token
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")          # Your Gemini API Key
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")         # Render External URL for webhook

# ---------------- INIT GEMINI ---------------- #
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")

# ---------------- USER DATA ---------------- #
user_sessions = {}

# ---------------- HANDLERS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_sessions[user_id] = []
    await update.message.reply_text(
        "🤖 JLPT N1 Study Bot Ready!\nUse commands:\n/vocab /grammar /dokkai /progress\nOr chat naturally!"
    )

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
        await update.message.reply_text("⚠️ Gemini API error. Please try again later.")

# ---------------- FLASK APP ---------------- #
app = Flask("JLPT_N1_Bot")
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Add Telegram handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

# Webhook route
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return "ok"

# Health check route
@app.route("/")
def index():
    return "JLPT N1 Bot is running ✅"

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    # Set webhook
    application.bot.set_webhook(f"{RENDER_URL}/{TELEGRAM_TOKEN}")
    
    # Run Flask server
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
