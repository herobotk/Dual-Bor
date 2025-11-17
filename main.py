import os
import re
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from humanize import naturalsize

from filters import FILTERS
from config import (
    API_ID, API_HASH,
    BOT_TOKEN_1, BOT_TOKEN_2,
    KILLME_CHANNELS,
    REPLYBOT_GROUP,
    GROUP_EXCLUDED_IDS
)


# ============================================================
#           HEALTH CHECK (KOYEB MUST HAVE THIS)
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Alive!")

threading.Thread(
    target=lambda: HTTPServer(("", 8080), HealthHandler).serve_forever(),
    daemon=True
).start()


# ============================================================
#                    COMMON FUNCTIONS
# ============================================================

def clean_filename(filename: str) -> str:
    keep = "@movie_talk_backup"
    filename = filename.replace(keep, "KEEP_NAME")
    filename = re.sub(r'@\w+', '', filename)
    filename = re.sub(r'https?://\S+|www\.\S+|\S+\.(com|in|net|org|me)', '', filename)
    filename = re.sub(r't\.me/\S+', '', filename)
    filename = re.sub(r'[^\w\s.\-()_]', '', filename)
    filename = re.sub(r'\s+', ' ', filename).strip()
    return filename.replace("KEEP_NAME", keep)


def generate_caption(file_name, file_size):
    cleaned = clean_filename(file_name)
    return f"""{cleaned}
⚙️ Size ~ [{file_size}]
⚜️ Post by ~ MOVIE TALK

⚡ Join Us ~ ❤️
➦『 @movie_talk_backup 』"""


async def send_filter(bot, chat_id, msg_id, data):
    text = data.get("text")
    image = data.get("image")
    buttons = data.get("buttons")

    keyboard = None
    if buttons:
        rows = [
            [InlineKeyboardButton(btn["text"], url=btn["url"]) for btn in row]
            for row in buttons
        ]
        keyboard = InlineKeyboardMarkup(rows)

    if image:
        return await bot.send_photo(chat_id, image, caption=text, reply_to_message_id=msg_id, reply_markup=keyboard)
    else:
        return await bot.send_message(chat_id, text or "", reply_to_message_id=msg_id, reply_markup=keyboard)


# ============================================================
#                BOT 1 — KillMe + Manual Filter
# ============================================================

bot1 = Client(
    "bot1_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN_1
)

# ---- START / HELP ----
@bot1.on_message(filters.command("start"))
async def start_b1(_, m):
    await m.reply("Hello! I am BOT 1 (Kill-Me + Manual Filter).")

@bot1.on_message(filters.command("help"))
async def help_b1(_, m):
    await m.reply("BOT 1:\n• Kill-Me Bot\n• Manual Filter\n• /start\n• /help")


# ---- KILL ME BOT ----
@bot1.on_message(filters.channel & ~filters.me)
async def kill_me(_, message: Message):
    if message.chat.id not in KILLME_CHANNELS:
        return

    media = message.document or message.video or message.audio
    caption_orig = message.caption or ""

    if media and media.file_name:
        fname = media.file_name
        fsize = naturalsize(media.file_size)
        caption = generate_caption(fname, fsize)
    else:
        caption = clean_filename(caption_orig)

    try:
        await message.copy(chat_id=message.chat.id, caption=caption)
        await message.delete()

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.copy(chat_id=message.chat.id, caption=caption)
        await message.delete()


# ---- MANUAL FILTER (REPLY MODE) ----
@bot1.on_message(filters.group & filters.reply & filters.text & ~filters.command(""))
async def filter_reply(_, message: Message):
    t = message.text.lower().strip()
    if t not in FILTERS:
        return

    original = message.reply_to_message
    await send_filter(bot1, original.chat.id, original.id, FILTERS[t])
    message.stop_propagation()


# ---- MANUAL FILTER (DIRECT MODE) ----
@bot1.on_message(filters.group & ~filters.reply & filters.text & ~filters.command(""))
async def filter_direct(_, message: Message):
    t = message.text.lower().strip()
    if t not in FILTERS:
        return

    await send_filter(bot1, message.chat.id, message.id, FILTERS[t])
    message.stop_propagation()



# ============================================================
#               BOT 2 — Reply Bot Only
# ============================================================

bot2 = Client(
    "bot2_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN_2
)

user_messages = {}

# ---- START / HELP ----
@bot2.on_message(filters.command("start"))
async def start_b2(_, m):
    await m.reply("Hello! I am BOT 2 (Reply Bot Only).")

@bot2.on_message(filters.command("help"))
async def help_b2(_, m):
    await m.reply("BOT 2:\n• Auto Reply System\n• /start\n• /help")


# ---- REPLY BOT ----
@bot2.on_message(filters.group & filters.text & ~filters.command(""))
async def reply_bot(_, message: Message):

    if message.chat.id not in REPLYBOT_GROUP:
        return

    if message.sender_chat and message.sender_chat.id == message.chat.id:
        return

    if message.from_user and message.from_user.id in GROUP_EXCLUDED_IDS:
        return

    user = message.from_user
    if not user:
        return

    uid = user.id
    txt = message.text.strip()
    now = datetime.utcnow()

    old = user_messages.get(uid)

    if old:
        if old["text"] == txt and now - old["time"] < timedelta(minutes=60):
            try:
                await bot2.delete_messages(message.chat.id, old["bot_msg_id"])
            except:
                pass

            sent = await message.reply("ᴀʟʀᴇᴀᴅʏ ɴᴏᴛᴇᴅ ✅\nᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ⏳...")
        else:
            sent = await message.reply("ʀᴇQᴜᴇꜱᴛ ʀᴇᴄᴇɪᴠᴇᴅ ✅\nᴜᴘʟᴏᴀᴅ ꜱᴏᴏɴ...✨")

    else:
        sent = await message.reply("ʀᴇQᴜᴇꜱᴛ ʀᴇᴄᴇɪᴠᴇᴅ ✅\nᴜᴘʟᴏᴀᴅ ꜱᴏᴏɴ...✨")

    user_messages[uid] = {"text": txt, "bot_msg_id": sent.id, "time": now}



# ============================================================
#               RUN BOTH BOTS (IMPORTANT)
# ============================================================

if __name__ == "__main__":
    bot1.start()
    bot2.start()
    asyncio.get_event_loop().run_forever()
