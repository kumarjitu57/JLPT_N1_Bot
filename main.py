# main.py
import random
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------- CONFIG ---------------- #
GEMINI_API_KEY = "AIzaSyDzzq2WYGyeGdF4kjfvCCv5aNZcGHHNd5k"        # 🔑 Replace with your Gemini API key
TELEGRAM_TOKEN = "8473657110:AAHL7HPMCuy2FnjL9OA7e0PFjMAa-rAeVjU"    # 🔑 Replace with your Telegram bot token

# ---------------- INIT GEMINI ---------------- #
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5")  # supported model

# ---------------- SAMPLE DATA ---------------- #
vocab_list = [
    {"kanji": "曖昧", "reading": "あいまい", "meaning": "ambiguous", "japanese_def": "はっきりしないこと"},
    {"kanji": "妥協", "reading": "だきょう", "meaning": "compromise", "japanese_def": "お互いに譲ること"},
    {"kanji": "懸念", "reading": "けねん", "meaning": "concern", "japanese_def": "心配すること"},
    {"kanji": "精密", "reading": "せいみつ", "meaning": "precise", "japanese_def": "細かく正確なこと"},
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
user_data = {}        # progress tracking
user_sessions = {}    # conversation memory
current_quiz_type = {} # track current quiz type
current_options = {}   # store current multiple-choice options

def get_user_id(update: Update):
    return str(update.effective_user.id)

# ---------------- COMMANDS ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    user_sessions[user_id] = []  # reset chat memory
    await update.message.reply_text(
        "🤖 JLPT N1 Study Bot Ready!\n\n"
        "Use:\n"
        "🈶 /vocab → Vocabulary quiz\n"
        "📘 /grammar → Grammar quiz\n"
        "📖 /dokkai → Reading (dokkai) quiz\n"
        "📊 /progress → Check your learning progress\n"
        "💬 Or chat naturally about JLPT!"
    )

# ---------------- QUIZZES ---------------- #
def generate_options(correct_answer, pool, n=4):
    choices = [correct_answer]
    while len(choices) < n:
        choice = random.choice(pool)
        if choice not in choices:
            choices.append(choice)
    random.shuffle(choices)
    return choices

async def vocab_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(vocab_list)
    context.user_data["current_vocab"] = q
    current_quiz_type[get_user_id(update)] = "vocab"

    pool = [v["meaning"] for v in vocab_list if v != q]
    opts = generate_options(q["meaning"], pool)
    current_options[get_user_id(update)] = opts

    text_opts = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(opts)])
    await update.message.reply_text(
        f"🈶 What is the meaning of {q['kanji']} ({q['reading']})?\n"
        f"日本語の説明: {q['japanese_def']}\n{text_opts}\n\nReply with 1/2/3/4"
    )

async def grammar_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(grammar_list)
    context.user_data["current_grammar"] = q
    current_quiz_type[get_user_id(update)] = "grammar"

    pool = [g["meaning"] for g in grammar_list if g != q]
    opts = generate_options(q["meaning"], pool)
    current_options[get_user_id(update)] = opts

    text_opts = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(opts)])
    await update.message.reply_text(
        f"📘 Grammar point: {q['point']}\nExample: {q['example']}\n{text_opts}\n\nReply with 1/2/3/4"
    )

async def dokkai_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = random.choice(dokkai_list)
    context.user_data["current_dokkai"] = q
    current_quiz_type[get_user_id(update)] = "dokkai"
    opts = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(q['options'])])
    current_options[get_user_id(update)] = q['options']
    await update.message.reply_text(
        f"📖 {q['question']}\n{opts}\n\nReply with 1/2/3"
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
        "📊 *Your JLPT N1 Progress* 📊\n\n"
        f"🈶 Vocabulary: {mastered_vocab}/{total_vocab} mastered ({vocab_pct:.1f}%)\n"
        f"📘 Grammar: {mastered_grammar}/{total_grammar} mastered ({grammar_pct:.1f}%)\n\n"
        "👉 Keep practicing with /vocab /grammar /dokkai!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------------- INTERACTIVE ANSWER HANDLER ---------------- #
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    msg = update.message.text.strip()

    if user_id not in current_quiz_type:
        await chat(update, context)  # fallback conversation
        return

    quiz_type = current_quiz_type[user_id]
    data = user_data.setdefault(user_id, {"vocab_mastery": {}, "grammar_mastery": {}, "quiz_scores": []})
    opts = current_options.get(user_id, [])

    try:
        index = int(msg) - 1
        if index < 0 or index >= len(opts):
            raise ValueError
    except:
        await update.message.reply_text("❌ Invalid input. Reply with the correct option number!")
        return

    if quiz_type == "vocab":
        q = context.user_data.get("current_vocab")
        if opts[index] == q["meaning"]:
            await update.message.reply_text("✅ Correct!")
            data["vocab_mastery"][q["kanji"]] = data["vocab_mastery"].get(q["kanji"], 0) + 1
        else:
            await update.message.reply_text(f"❌ Wrong! Correct answer: {q['meaning']}")

    elif quiz_type == "grammar":
        q = context.user_data.get("current_grammar")
        if opts[index] == q["meaning"]:
            await update.message.reply_text("✅ Correct!")
            data["grammar_mastery"][q["point"]] = data["grammar_mastery"].get(q["point"], 0) + 1
        else:
            await update.message.reply_text(f"❌ Wrong! Correct answer: {q['meaning']}")

    elif quiz_type == "dokkai":
        q = context.user_data.get("current_dokkai")
        if opts[index] == q["answer"]:
            await update.message.reply_text("✅ Correct!")
        else:
            await update.message.reply_text(f"❌ Wrong! Correct answer: {q['answer']}")

    # clear current quiz session
    del current_quiz_type[user_id]
    del current_options[user_id]

# ---------------- CHAT FALLBACK ---------------- #
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = get_user_id(update)
    user_input = update.message.text
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"role": "user", "parts": [user_input]})

    try:
        response = model.generate_content(user_sessions[user_id])
        reply_text = getattr(response, "text", str(response))
        user_sessions[user_id].append({"role": "model", "parts": [reply_text]})
        await update.message.reply_text(reply_text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        await update.message.reply_text("⚠️ Sorry, I had trouble answering. Please try again.")

# ---------------- MAIN ---------------- #
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vocab", vocab_quiz))
    app.add_handler(CommandHandler("grammar", grammar_quiz))
    app.add_handler(CommandHandler("dokkai", dokkai_quiz))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    print("🤖 JLPT N1 Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
