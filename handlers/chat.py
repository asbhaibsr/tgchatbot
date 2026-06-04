"""
Smart Chat Handler — Merged with ASGroupBot features
─────────────────────────────────────────────────────
1. Bot sirf tab bolegi jab:
   - Usse directly @mention kiya gaya ho
   - Uske trigger words aaye (cutie, cutie pie etc)
   - Koi bina kisi ke reply ke message aaye (orphan)
   - 5-6 messages ke baad kabhi kabhi (interjection)

2. Premium auto-moderation:
   - Anti-link, Anti-forward, Flood control
   - Locked message types
   - Auto-delete files (scheduled)

3. Movie File Obfuscation (settings se on/off)

4. 12% chance pe sticker bhi bhejti hai

5. Admin apne message ko khud reply kare → pattern sikha
"""

import os
import re
import asyncio
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction, ChatMemberStatus

from core.db import (
    save_user, save_message, is_blocked,
    increment_counter, reset_counter,
    get_group_setting, is_premium, is_flooding,
    schedule_delete, save_active_member, find_pattern
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

_URL_RE = re.compile(
    r'(https?://\S+|www\.\S+|t\.me/\S+|\S+\.(com|net|org|io|gg|xyz)\S*)',
    re.IGNORECASE,
)

def has_url(text: str) -> bool:
    return bool(_URL_RE.search(text or ""))

def safe_text_maker(text):
    if not text:
        return ""
    replacements = {
        'a': '@', 'A': '@', 'i': '!', 'I': '!', 's': '$', 'S': '$',
        'o': '0', 'O': '0', 'e': '£', 'E': '£', 't': '†', 'T': '†'
    }
    safe_name = "".join(
        replacements.get(char, char) if random.random() > 0.2 else char
        for char in text
    )
    return random.choice([" ⚡️ ", " 🎬 ", " ✨ ", " 🍿 "]).join(safe_name.split())

# ── Typing delay (Vercel ke liye fast) ────────────────────────────────

async def typing_delay(context, chat_id, text=""):
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

# ── Movie File Handler ─────────────────────────────────────────────────

async def movie_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat    = update.effective_chat

    if not message or not (message.document or message.video):
        return

    settings_movie = get_group_setting(chat.id, "movie_on", True)
    if not settings_movie:
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
        print(f"[ERROR] Movie file handler: {e}")

# ── Premium Auto-Moderation Guard ─────────────────────────────────────

async def group_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Premium auto-mod: anti-link, anti-fwd, lock types, flood, auto-delete"""
    message = update.effective_message
    chat    = update.effective_chat
    user    = update.effective_user

    if not message or not user or user.is_bot:
        return False

    chat_id = chat.id
    user_id = user.id

    # Save active member for tagall
    save_active_member(chat_id, user_id)

    if not is_premium(chat_id):
        return False

    # Check if user is admin (admins exempt)
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        user_is_admin = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER) or user_id == ADMIN_ID
    except Exception:
        user_is_admin = user_id == ADMIN_ID

    if user_is_admin:
        return False

    text = message.text or message.caption or ""

    # 1. Anti-link
    if get_group_setting(chat_id, "antilink_on", False):
        if has_url(text):
            try:
                await message.delete()
                notif = await context.bot.send_message(
                    chat_id,
                    f"🔗 {user.mention_html()} — Links allowed nahi hain is group mein!",
                    parse_mode="HTML"
                )
                await asyncio.sleep(5)
                await notif.delete()
            except Exception:
                pass
            return True

    # 2. Anti-forward
    if get_group_setting(chat_id, "antifwd_on", False):
        if message.forward_date:
            try:
                await message.delete()
                notif = await context.bot.send_message(
                    chat_id,
                    f"↪️ {user.mention_html()} — Forwarded messages allowed nahi!",
                    parse_mode="HTML"
                )
                await asyncio.sleep(5)
                await notif.delete()
            except Exception:
                pass
            return True

    # 3. Locked types
    locked = get_group_setting(chat_id, "locked_types", []) or []
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
            return True

    # 4. Flood control
    if get_group_setting(chat_id, "flood_on", False):
        flood_limit = get_group_setting(chat_id, "flood_limit", 5)
        if is_flooding(chat_id, user_id, limit=flood_limit, window=10):
            try:
                from telegram import ChatPermissions
                until = datetime.now() + timedelta(minutes=5)
                await context.bot.restrict_chat_member(
                    chat_id, user_id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until
                )
                notif = await context.bot.send_message(
                    chat_id,
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
            return True

    # 5. Auto-delete schedule
    if (get_group_setting(chat_id, "autodel_on", False)
            and (message.document or message.video or message.audio)):
        del_secs = get_group_setting(chat_id, "autodel_time", 3600)
        delete_at = datetime.now() + timedelta(seconds=del_secs)
        schedule_delete(chat_id, message.message_id, delete_at)

    return False

# ── Main message handler ───────────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat

    if not message or not user or user.is_bot:
        return

    if is_blocked(user.id):
        return

    text = message.text or message.caption or ""

    save_user(user)

    if text:
        save_message(chat.id, user.id, text)

    # Run premium auto-mod
    if chat.type != "private":
        blocked_by_mod = await group_guard(update, context)
        if blocked_by_mod:
            return

    # Check chatbot setting
    if chat.type != "private":
        if not get_group_setting(chat.id, "chat_bot_on", True):
            return

    # ── ADMIN LEARNING ────────────────────────────────────────────────
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

    # ── Private chat ──────────────────────────────────────────────────
    if chat.type == "private":
        await _send_smart_reply(update, context, text, chat.id)
        return

    # ── GROUP logic ───────────────────────────────────────────────────
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
