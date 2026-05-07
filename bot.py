import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIG ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-8b-8192"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """Ikaw ay isang helpful, friendly, at matalinong AI assistant. 
Sumasagot ka sa kahit anong tanong nang malinaw at tapat. 
Pwede kang sumagot sa Filipino, Tagalog, o English depende sa tanong."""

# === GROQ API CALL ===
def ask_groq(user_message: str, chat_history: list) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(chat_history[-10:])  # last 10 messages lang para hindi masyadong malaki
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "Sorry, may error sa AI. Subukan ulit mamaya!"

# === CHAT HISTORY per user ===
chat_histories = {}

# === /start COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kamusta! Ako ang iyong AI assistant. Magtanong ka lang ng kahit ano! 🤖"
    )

# === /clear COMMAND ===
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text("Na-clear na ang iyong chat history! Fresh start! 🔄")

# === MESSAGE HANDLER ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore kung walang message
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_message = update.message.text
    chat_type = update.message.chat.type

    # Sa group/channel, sumasagot lang kung may @mention o reply sa bot
    if chat_type in ["group", "supergroup", "channel"]:
        bot_username = context.bot.username
        is_mentioned = f"@{bot_username}" in user_message
        is_reply_to_bot = (
            update.message.reply_to_message and
            update.message.reply_to_message.from_user.id == context.bot.id
        )
        if not is_mentioned and not is_reply_to_bot:
            return
        # Tanggalin ang mention sa message
        user_message = user_message.replace(f"@{bot_username}", "").strip()

    # Init chat history
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    # Typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    # Kumuha ng sagot mula sa Groq
    reply = ask_groq(user_message, chat_histories[user_id])

    # I-save sa history
    chat_histories[user_id].append({"role": "user", "content": user_message})
    chat_histories[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
