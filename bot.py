import os
import logging
import requests
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIG ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
MODEL = "llama-3.1-8b-instant"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === GROQ CLIENT ===
client = Groq(api_key=GROQ_API_KEY)

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """Ikaw si "Shenru AI" - isang super friendly, masaya, at matalinong AI assistant na nagsasalita ng Taglish (mix ng Tagalog at English).

Personality mo:
- Palaging masaya at may energy! Gumagamit ng emojis pero hindi OA
- Parang kaibigan ang dating, hindi parang robot o seryosong AI
- May sense of humor at pwedeng magpatawa
- Helpful at caring sa mga tao
- Kapag hindi mo alam ang sagot, aminin mo nang may humor lang

Style ng pagsagot:
- "Uy, magandang tanong yan! 😄 So ganito yan..."
- "Haha gets kita! Basically..."
- "Ay wait, hindi ako 100% sure dyan ah, pero based sa alam ko..."
- "Sige, tulungan kita dyan! 💪"

Laging sumagot sa Taglish maliban kung ang kausap ay English lang nagsasalita."""

# === CHAT HISTORY per user ===
chat_histories = {}

# === GROQ API CALL ===
def ask_groq(user_message: str, chat_history: list, system: str = SYSTEM_PROMPT) -> str:
    try:
        messages = [{"role": "system", "content": system}]
        messages.extend(chat_history[-10:])
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "Ay sorry, may error ako ngayon! 😅 Subukan ulit mamaya ha!"

# === /start COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Heyy {name}! 👋😄 Ako si Shenru AI, ang iyong pinaka-friendly na AI assistant!\n\n"
        f"Pwede kang magtanong ng kahit ano sa akin! Nandito lang ako para sa'yo 💪\n\n"
        f"Mga commands ko:\n"
        f"🎭 /joke - Magpatawa ako sayo!\n"
        f"💬 /quote - Inspirational quote para sa'yo\n"
        f"🌤 /weather [lungsod] - Weather check\n"
        f"📖 /wiki [topic] - Maghanap sa Wikipedia\n"
        f"🖼 /image [description] - Gumawa ng image\n"
        f"🗑 /clear - I-clear ang chat history\n\n"
        f"So ano'ng maitutulong ko sayo? 😊"
    )

# === /clear COMMAND ===
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text("Na-clear na! Fresh start tayo! 🔄😄")

# === /joke COMMAND ===
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = ask_groq(
        "Magbigay ng isang nakakatawang Filipino joke o Taglish joke. Yung talaga nakakatawa ha!",
        [],
        SYSTEM_PROMPT
    )
    await update.message.reply_text(reply)

# === /quote COMMAND ===
async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = ask_groq(
        "Magbigay ng isang magandang inspirational quote. Pwedeng English yung quote pero mag-explain ka sa Taglish. May emoji!",
        [],
        SYSTEM_PROMPT
    )
    await update.message.reply_text(reply)

# === /weather COMMAND ===
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uy, sabihin mo kung saang lugar! 😄\nHalimbawa: /weather Manila")
        return

    city = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url)
        data = res.json()

        if data.get("cod") != 200:
            await update.message.reply_text(f"Ay, hindi ko mahanap ang '{city}'! 😅 Baka may typo? Try ulit!")
            return

        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        desc = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        city_name = data["name"]

        msg = (
            f"🌤 Weather sa **{city_name}**:\n\n"
            f"🌡 Temperature: {temp}°C (feels like {feels}°C)\n"
            f"☁️ Kondisyon: {desc.capitalize()}\n"
            f"💧 Humidity: {humidity}%\n\n"
        )

        if temp >= 35:
            msg += "Grabe ka init! Mag-ingat sa init, laging may tubig ha! 🥵"
        elif temp >= 28:
            msg += "Mainit pero okay pa! Mag-sunscreen ka na! ☀️"
        elif temp >= 20:
            msg += "Medyo malamig! Perfect na weather! 😊"
        else:
            msg += "Malamig! Mag-jacket ka na! 🧥"

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("Ay may error sa weather! 😅 Subukan ulit mamaya!")

# === /wiki COMMAND ===
async def wiki(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Sabihin mo kung ano'ng hahanapin! 😄\nHalimbawa: /wiki Rizal")
        return

    topic = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        res = requests.get(url)
        data = res.json()

        if "extract" not in data:
            await update.message.reply_text(f"Ay, wala akong nakitang info tungkol sa '{topic}'! 😅 Try ng ibang keyword!")
            return

        extract = data["extract"][:800]
        title = data.get("title", topic)

        reply = ask_groq(
            f"I-summarize mo ito sa Taglish, friendly at may emojis:\n\nTungkol sa {title}:\n{extract}",
            [],
            SYSTEM_PROMPT
        )

        await update.message.reply_text(f"📖 **{title}**\n\n{reply}", parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Wiki error: {e}")
        await update.message.reply_text("May error sa Wikipedia search! 😅 Subukan ulit!")

# === /image COMMAND ===
async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Sabihin mo kung anong image gusto mo! 😄\nHalimbawa: /image cute cat in space")
        return

    prompt = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    await update.message.reply_text(f"Okay! Gagawa ako ng image ng '{prompt}'! Sandali lang! 🎨")

    try:
        encoded = requests.utils.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true"
        await update.message.reply_photo(photo=image_url, caption=f"🎨 '{prompt}'\n\nKamusta, maganda ba? 😄")

    except Exception as e:
        logger.error(f"Image error: {e}")
        await update.message.reply_text("Ay may error sa image generation! 😅 Subukan ulit!")

# === MESSAGE HANDLER ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        user_message = user_message.replace(f"@{bot_username}", "").strip()

    if user_id not in chat_histories:
        chat_histories[user_id] = []

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    reply = ask_groq(user_message, chat_histories[user_id])

    chat_histories[user_id].append({"role": "user", "content": user_message})
    chat_histories[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("wiki", wiki))
    app.add_handler(CommandHandler("image", image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
    
