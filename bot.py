import os
import logging
import requests
from groq import Groq
from telegram import Update, BotCommand
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
SYSTEM_PROMPT = """Ikaw ay isang highly intelligent, expert-level AI assistant na nagsasalita ng Taglish.

Personality:
- Seryoso, knowledgeable, at confident sa mga sagot — parang expert ka talaga
- Malinaw at detalyado mag-explain, pero hindi boring
- May kasamang subtle na humor o biro paminsan-minsan, hindi OA
- Direkta sa punto, walang paligoy-ligoy
- Kapag hindi mo alam ang sagot, aminin mo nang matino — hindi ka nagpapanggap

Estilo ng pagsagot:
- Professional pero approachable
- Gumagamit ng bullet points o numbered list kung mahabang explanation
- May emojis pero konti lang at angkop
- Kapag may biro, natural lang — hindi forced

Halimbawa:
- "Okay, ganito yan — [detalyadong sagot]. At oh, kung nagtataka ka bakit ganyan, well... ganyan talaga ang buhay. 😄"
- "Simple lang yan. [explanation]. Pero syempre, depende pa rin sa situation mo."

Laging sumagot sa Taglish maliban kung English lang nagsasalita ang kausap."""

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
            temperature=0.75
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq error: {e}")
        return "May technical issue ako ngayon. Subukan ulit mamaya."

# === SET BOT COMMANDS (lalabas sa / sa GC) ===
async def set_commands(app):
    commands = [
        BotCommand("start", "Simulan ang bot at makita ang mga commands"),
        BotCommand("joke", "Magbigay ng joke"),
        BotCommand("quote", "Inspirational quote ng araw"),
        BotCommand("weather", "Weather check — /weather [lungsod]"),
        BotCommand("wiki", "Maghanap sa Wikipedia — /wiki [topic]"),
        BotCommand("image", "Gumawa ng AI image — /image [description]"),
        BotCommand("clear", "I-clear ang chat history"),
    ]
    await app.bot.set_my_commands(commands)

# === /start COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Hello, {name}. Ako ang iyong AI assistant — knowledgeable, reliable, at occasionally nakaka-amuse. 😏\n\n"
        f"Mga available commands:\n"
        f"🎭 /joke — Magbigay ng joke\n"
        f"💬 /quote — Quote ng araw\n"
        f"🌤 /weather [lungsod] — Weather update\n"
        f"📖 /wiki [topic] — Wikipedia search\n"
        f"🖼 /image [description] — AI image generation\n"
        f"🗑 /clear — I-clear ang chat history\n\n"
        f"Magtanong ka lang. Nandito ako."
    )

# === /clear COMMAND ===
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_histories[user_id] = []
    await update.message.reply_text("Chat history cleared. Fresh start. 🗑")

# === /joke COMMAND ===
async def joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = ask_groq(
        "Magbigay ng isang nakakatawang Filipino o Taglish joke. Yung hindi baduy — clever ang dating.",
        [],
        SYSTEM_PROMPT
    )
    await update.message.reply_text(reply)

# === /quote COMMAND ===
async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    reply = ask_groq(
        "Magbigay ng isang powerful na inspirational quote — pwedeng sikat na tao o original mo. "
        "Ilagay ang quote, sino nagsabi, tapos brief na explanation sa Taglish kung bakit meaningful ito.",
        [],
        SYSTEM_PROMPT
    )
    await update.message.reply_text(reply)

# === /weather COMMAND ===
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /weather [lungsod]\nHalimbawa: /weather Manila")
        return

    city = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=10)
        data = res.json()

        if data.get("cod") != 200:
            await update.message.reply_text(f"Hindi mahanap ang '{city}'. Check mo ang spelling.")
            return

        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        desc = data["weather"][0]["description"].capitalize()
        humidity = data["main"]["humidity"]
        wind = data["wind"]["speed"]
        city_name = data["name"]
        country = data["sys"]["country"]

        if temp >= 35:
            temp_comment = "Sobrang init. Mag-ingat sa heat stroke. 🥵"
        elif temp >= 28:
            temp_comment = "Mainit. Mag-hydrate ka. ☀️"
        elif temp >= 20:
            temp_comment = "Comfortable ang weather. 😊"
        elif temp >= 10:
            temp_comment = "Malamig. Mag-jacket ka na. 🧥"
        else:
            temp_comment = "Napaka-lamig. Huwag lumabas kung hindi kailangan. ❄️"

        msg = (
            f"🌤 *Weather — {city_name}, {country}*\n\n"
            f"🌡 Temperature: *{temp:.1f}°C* (feels like {feels:.1f}°C)\n"
            f"☁️ Kondisyon: {desc}\n"
            f"💧 Humidity: {humidity}%\n"
            f"💨 Wind: {wind} m/s\n\n"
            f"{temp_comment}"
        )

        await update.message.reply_text(msg, parse_mode="Markdown")

    except requests.exceptions.Timeout:
        await update.message.reply_text("Timeout ang weather API. Subukan ulit.")
    except Exception as e:
        logger.error(f"Weather error: {e}")
        await update.message.reply_text("May error sa weather service. Subukan ulit mamaya.")

# === /wiki COMMAND ===
async def wiki(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /wiki [topic]\nHalimbawa: /wiki Jose Rizal")
        return

    topic = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Search muna para makuha ang tamang page title
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json",
            "srlimit": 1
        }
        search_res = requests.get(search_url, params=search_params, timeout=10)
        search_data = search_res.json()

        results = search_data.get("query", {}).get("search", [])
        if not results:
            await update.message.reply_text(f"Walang nakitang resulta para sa '{topic}'. Try ng ibang keyword.")
            return

        page_title = results[0]["title"]

        # Kuhanin ang summary ng page
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(page_title)}"
        summary_res = requests.get(summary_url, timeout=10)
        summary_data = summary_res.json()

        extract = summary_data.get("extract", "")
        if not extract:
            await update.message.reply_text(f"Nahanap ko ang page pero walang laman. Try ng ibang keyword.")
            return

        # Limit sa 1000 chars para hindi masyadong mahaba
        extract = extract[:1000]

        reply = ask_groq(
            f"I-summarize at i-explain sa Taglish ang sumusunod na impormasyon tungkol sa '{page_title}'. "
            f"Maging concise pero informative. Huwag kalimutang magdagdag ng key facts:\n\n{extract}",
            [],
            SYSTEM_PROMPT
        )

        wiki_link = f"https://en.wikipedia.org/wiki/{requests.utils.quote(page_title)}"
        await update.message.reply_text(
            f"📖 *{page_title}*\n\n{reply}\n\n🔗 [Basahin ang buong article]({wiki_link})",
            parse_mode="Markdown"
        )

    except requests.exceptions.Timeout:
        await update.message.reply_text("Timeout ang Wikipedia. Subukan ulit.")
    except Exception as e:
        logger.error(f"Wiki error: {e}")
        await update.message.reply_text("May error sa Wikipedia search. Subukan ulit mamaya.")

# === /image COMMAND ===
async def image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /image [description]\nHalimbawa: /image a futuristic city at night")
        return

    prompt = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    await update.message.reply_text(f"Generating image: '{prompt}'... Sandali lang.")

    try:
        encoded = requests.utils.quote(prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true&seed={hash(prompt) % 10000}"
        
        res = requests.get(image_url, timeout=30)
        if res.status_code == 200:
            await update.message.reply_photo(
                photo=image_url,
                caption=f"🖼 *{prompt}*\n\nGenerated via Pollinations AI.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("Hindi na-generate ang image. Subukan ulit.")

    except requests.exceptions.Timeout:
        await update.message.reply_text("Timeout ang image generation. Subukan ulit — medyo matagal minsan.")
    except Exception as e:
        logger.error(f"Image error: {e}")
        await update.message.reply_text("May error sa image generation. Subukan ulit mamaya.")

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

    # Set commands para lalabas sa / sa GC
    app.post_init = set_commands

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("quote", quote))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("wiki", wiki))
    app.add_handler(CommandHandler("image", image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running.")
    app.run_polling()

if __name__ == "__main__":
    main()
