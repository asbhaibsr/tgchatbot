# Smart Chat Handler + Movie File Obfuscation + Auto-Mod Guards

import os
import asyncio
import random
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from core.db import (
    save_user, save_message, is_blocked,
    increment_counter, reset_counter,
    get_setting, is_premium, is_flooding,
    schedule_delete, save_active_member
)
from core.brain import find_reply, learn_from_reply
from core.persona import (
    BOT_TRIGGERS, get_interjection, get_orphan_reply,
    get_nakhre, get_sticker, should_send_sticker
)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

BAD_WORDS = [
    "gandu", "chutiya", "madarchod", "bhenchod", "harami",
    "randi", "saali", "mc", "bc", "sala", "bhosdike"
]

_URL_RE = __import__("re").compile(
    r'(https?://\S+|www\.\S+|t\.me/\S+|\S+\.(com|net|org|io|gg|xyz)\S*)',
    __import__("re").IGNORECASE,
)

def has_url(text: str) -> bool:
    return bool(_URL_RE.search(text or ""))

# ── Typing delay (Vercel-safe, no long sleep) ──────────────────────────

async def typing_delay(context, chat_id, text=""):
    # Vercel ko fast rakhne ke liye minimal sleep
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

# ── Movie file name obfuscation ────────────────────────────────────────

def safe_text_maker(text):
    if not text:
        return ""
    replacements = {
        'a': '@', 'A': '@', 'i': '!', 'I': '!',
        's': '$', 'S': '$', 'o': '0', 'O': '0',
        'e': '£', 'E': '£', 't': '†', 'T': '†'
    }
    safe_name = "".join(
        replacements.get(char, char) if random.random() > 0.2 else char
        for char in text
    )
    return random.choice([" ⚡️ ", " 🎬 ", " ✨ ", " 🍿 "]).join(safe_name.split())

# ── Movie / Document file handler ─────────────────────────────────────

async def movie_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat    = update.effective_chat

    if not message or not (message.document or message.video):
        return

    # Settings check
    if not get_setting(chat.id, "movie_on", True):
        return

    original_name = (
        (message.document.file_name if message.document else None)
        or (message.video.file_name if message.video else None)
        or "Movie_File"
    )
    file_id = message.document.file_id if message.document else message.video.file_id

    safe_file_name = safe_text_maker(original_name)
    new_caption = (
        f"🎬 𝗙𝗶𝗹𝗲:\n{safe_file_name}\n\n"
        f"📥 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗱 𝘃𝗶𝗮 𝗕𝗼𝘁 (@asbhaibsr)"
    )

    try:
        await message.delete()
        if message.document:
            await context.bot.send_document(chat_id=chat.id, document=file_id, caption=new_caption)
        elif message.video:
            await context.bot.send_video(chat_id=chat.id, video=file_id, caption=new_caption)
    except Exception as e:
        print(f"[ERROR] movie_file_handler: {e}")

# ── Main message handler ───────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat

    if not message or not user or user.is_bot:
        return

    # Blocked user ignore
    if is_blocked(user.id):
        return

    text = message.text or message.caption or ""

    # Save user + message
    save_user(user)
    if text:
        save_message(chat.id, user.id, text)

    # Track active member for /tagall
    if chat.type != "private":
        save_active_member(chat.id, user.id)

    # ── ADMIN SELF-REPLY LEARNING ─────────────────────────────────────
    if (
        user.id == ADMIN_ID
        and message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == ADMIN_ID
    ):
        replied_text = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        )
        if replied_text and text:
            learned = learn_from_reply(replied_text, text, ADMIN_ID)
            if learned:
                await message.reply_text("✅ Seekh liya maine~ 🧠")
                return

    # ── PRIVATE CHAT ─────────────────────────────────────────────────
    if chat.type == "private":
        # Check premium conversation first
        from handlers.admin import pm_premium_conversation
        handled = await pm_premium_conversation(update, context)
        if handled:
            return
        await _send_smart_reply(update, context, text, chat.id)
        return

    # ── GROUP AUTO-MOD (premium) ──────────────────────────────────────
    if is_premium(chat.id):
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            user_is_admin = member.status in ("administrator", "creator")
        except Exception:
            user_is_admin = (user.id == ADMIN_ID)

        if not user_is_admin:
            # 1. Anti-link
            if get_setting(chat.id, "antilink_on", False) and has_url(text):
                try:
                    await message.delete()
                    notif = await context.bot.send_message(
                        chat.id,
                        f"🔗 {user.mention_html()} — Links allowed nahi hain is group mein!",
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(5)
                    await notif.delete()
                except Exception:
                    pass
                return

            # 2. Anti-forward
            if get_setting(chat.id, "antifwd_on", False) and (
                message.forward_from or message.forward_from_chat
            ):
                try:
                    await message.delete()
                    notif = await context.bot.send_message(
                        chat.id,
                        f"↪️ {user.mention_html()} — Forwarded messages allowed nahi!",
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(5)
                    await notif.delete()
                except Exception:
                    pass
                return

            # 3. Locked types
            locked = get_setting(chat.id, "locked_types", []) or []
            if locked:
                msg_type = None
                if message.sticker:
                    msg_type = "stickers"
                elif message.animation:
                    msg_type = "gifs"
                elif message.poll:
                    msg_type = "polls"
                elif message.photo or message.video or message.document:
                    msg_type = "media"
                if msg_type and msg_type in locked:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    return

            # 4. Flood control
            if get_setting(chat.id, "flood_on", False):
                flood_limit = get_setting(chat.id, "flood_limit", 5)
                if is_flooding(chat.id, user.id, limit=flood_limit, window=10):
                    try:
                        from telegram import ChatPermissions
                        until = datetime.now() + timedelta(minutes=5)
                        await context.bot.restrict_chat_member(
                            chat.id, user.id,
                            permissions=ChatPermissions(can_send_messages=False),
                            until_date=until
                        )
                        notif = await context.bot.send_message(
                            chat.id,
                            f"⚡ {user.mention_html()} — Flood ke liye <b>5 min muted!</b>",
                            parse_mode="HTML"
                        )
                        await asyncio.sleep(8)
                        try:
                            await notif.delete()
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return

    # ── FILE AUTO-DELETE (premium) ────────────────────────────────────
    if (
        is_premium(chat.id)
        and get_setting(chat.id, "autodel_on", False)
        and (message.document or message.video or message.audio)
    ):
        del_secs = get_setting(chat.id, "autodel_time", 3600)
        delete_at = datetime.now() + timedelta(seconds=del_secs)
        schedule_delete(chat.id, message.message_id, delete_at)

    # ── CHATBOT CHECK ─────────────────────────────────────────────────
    if not get_setting(chat.id, "chat_bot_on", True):
        return

    # ── GROUP CHATBOT LOGIC ───────────────────────────────────────────
    text_lower = text.lower()

    bot_username = context.bot.username or ""
    mentioned = (
        f"@{bot_username}".lower() in text_lower
        or any(t in text_lower for t in BOT_TRIGGERS)
    )

    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )

    has_bad_word = any(w in text_lower for w in BAD_WORDS)

    is_orphan = (
        not message.reply_to_message
        and not mentioned
        and not replied_to_bot
        and len(text) > 5
        and random.random() < 0.08
    )

    counter = increment_counter(chat.id)
    should_interject = False
    if counter >= random.randint(5, 7):
        should_interject = True
        reset_counter(chat.id)

    if has_bad_word and (mentioned or replied_to_bot):
        await typing_delay(context, chat.id, "nakhre")
        await message.reply_text(get_nakhre())

    elif mentioned or replied_to_bot:
        await _send_smart_reply(update, context, text, chat.id)

    elif is_orphan:
        await typing_delay(context, chat.id, "orphan")
        await message.reply_text(get_orphan_reply())

    elif should_interject and not mentioned:
        await typing_delay(context, chat.id, "interject")
        response = get_interjection()
        await context.bot.send_message(chat.id, response)

# ── Smart reply helper ─────────────────────────────────────────────────

async def _send_smart_reply(update, context, text, chat_id):
    message = update.effective_message
    reply = find_reply(text) if text else None
    if reply:
        await typing_delay(context, chat_id, reply)
        await message.reply_text(reply)
        if should_send_sticker():
            sticker_id = get_sticker("happy")
            try:
                await context.bot.send_sticker(chat_id, sticker_id)
            except Exception:
                pass
    else:
        if update.effective_chat.type == "private":
            await typing_delay(context, chat_id, "hmm")
            fallbacks = [
                "Hmm... samjha nahi main 😅 Kuch aur puchho~",
                "Yeh toh pata nahi mujhe 🥺 Kuch aur batao!",
                "Arey seedha batao kya chahiye 😄",
                "Main seekh rahi hoon abhi~ Thoda time do 🌸",
            ]
            await message.reply_text(random.choice(fallbacks))
