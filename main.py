import os
from flask import Flask, request
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# Flask app for Render health check + webhook
app = Flask(__name__)

# --- Telegram Bot Handlers ---
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! 🚀 Your bot is live on Render!")

async def echo(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"You said: {update.message.text}")

# --- Telegram Application ---
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# --- Flask Routes ---
@app.route("/", methods=["GET"])
def index():
    return "🤖 Bot is running on Render!", 200

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    application.update_queue.put_nowait(update)
    return "ok", 200

# --- Main Entrypoint ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{RENDER_URL}/{TELEGRAM_TOKEN}",
    )
    app.run(host="0.0.0.0", port=port)
