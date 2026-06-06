import os
import re
import asyncio
import random
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from core.db import (
    save_user, save_message, is_blocked,
    get_setting, is_premium, is_flooding,
    schedule_delete, save_active_member
)
from core.brain import (
    find_reply, make_girl_reply,
    learn_from_reply, learn_from_conversation, learn_from_bot_reply,
    teach_pattern
)
from core.persona import (
    BOT_TRIGGERS, get_interjection, get_orphan_reply,
    get_nakhre, get_sticker, should_send_sticker
)

ADMIN_ID         = int(os.environ.get("ADMIN_ID", "0"))
FILE_LOG_CHANNEL = -1002085088955

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

# ── Recent messages tracker (in-memory per chat) ──────────────────────
# Format: {chat_id: [(user_id, message_id, text), ...]}
_recent_msgs: dict = {}

def _add_recent(chat_id, user_id, msg_id, text):
    if chat_id not in _recent_msgs:
        _recent_msgs[chat_id] = []
    _recent_msgs[chat_id].append((user_id, msg_id, text))
    # Sirf last 10 rakhо
    _recent_msgs[chat_id] = _recent_msgs[chat_id][-10:]

def _get_prev_msg(chat_id, exclude_user_id=None):
    """Ek pehle wala message do"""
    msgs = _recent_msgs.get(chat_id, [])
    for uid, mid, txt in reversed(msgs[:-1]):
        if uid != exclude_user_id and txt:
            return txt
    return None

# ── Typing delay ──────────────────────────────────────────────────────

async def typing_delay(context, chat_id, text=""):
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)

# ── Movie file obfuscation ────────────────────────────────────────────

def safe_text_maker(text):
    if not text:
        return "Movie_File"

    # Extension hatao
    name = re.sub(r'\.[a-zA-Z0-9]{2,5}$', '', text)
    name = name.replace('.', ' ').replace('_', ' ')

    replacements = {
        'a': '@', 'A': '@', 'i': '!', 'I': '!',
        's': '$', 'S': '$', 'o': '0', 'O': '0',
        'e': '£', 'E': '£', 't': '†', 'T': '†',
        'c': '(', 'C': '(', 'l': '\\'
    }

    obfuscated = "".join(
        replacements.get(char, char) if random.random() > 0.25 else char
        for char in name
    )

    # Episode pattern
    ep_match = re.search(r'[Ss](\d+)[Ee][Pp]?(\d+)', text)
    ep_str = f"$°{ep_match.group(1)}€P°{ep_match.group(2)}" if ep_match else ""

    # Quality
    q_match = re.search(r'(480p|720p|1080p|4K|2160p)', text, re.IGNORECASE)
    quality = q_match.group(1).replace('p', '°') if q_match else ""

    # Show name (pehle wale words)
    parts = obfuscated.split()
    name_parts = []
    for p in parts:
        if re.search(r'[Ss]\d+|[Ee][Pp]?\d+|\d{3,4}', p):
            break
        name_parts.append(p)
    main_name = "".join(name_parts) if name_parts else obfuscated[:15]

    # Extra codec info
    extra = []
    for kw in ['HEVC', 'x265', 'x264', 'WEB', 'DL', 'HDR', 'BluRay']:
        if kw.lower() in text.lower():
            extra.append(kw.replace('e', '£').replace('i', '!'))
    extra_str = " ".join(extra[:3])

    # Assemble
    parts_final = [f"🌸🏵{main_name}"]
    if ep_str:   parts_final.append(f"🌹💐 {ep_str}")
    if quality:  parts_final.append(quality)
    if extra_str: parts_final.append(f"#£V( {extra_str}")
    parts_final.append("🌺🥀")

    return " ".join(parts_final)

# ── Movie file handler ────────────────────────────────────────────────

async def movie_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat    = update.effective_chat

    # Sirf GROUP mein, PM mein nahi
    if not message or chat.type == "private":
        return

    if not (message.document or message.video):
        return

    # Sirf PREMIUM groups
    if not is_premium(chat.id):
        return

    if not get_setting(chat.id, "movie_on", True):
        return

    original_name = (
        (message.document.file_name if message.document else None)
        or (message.video.file_name if message.video else None)
        or "Movie_File"
    )
    file_id = message.document.file_id if message.document else message.video.file_id

    safe_name    = safe_text_maker(original_name)
    new_caption  = f"{safe_name}\n\n📥 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗱 𝘃𝗶𝗮 𝗕𝗼𝘁 (@asbhaibsr)"

    try:
        await message.delete()
        if message.document:
            sent = await context.bot.send_document(chat_id=chat.id, document=file_id, caption=new_caption)
        else:
            sent = await context.bot.send_video(chat_id=chat.id, video=file_id, caption=new_caption)

        # LOG channel forward
        try:
            await context.bot.forward_message(
                chat_id=FILE_LOG_CHANNEL,
                from_chat_id=chat.id,
                message_id=sent.message_id
            )
        except Exception as fe:
            print(f"[LOG] Forward fail: {fe}")

    except Exception as e:
        print(f"[ERROR] movie_file_handler: {e}")

# ── Main message handler ──────────────────────────────────────────────

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

    if chat.type != "private":
        save_active_member(chat.id, user.id)
        _add_recent(chat.id, user.id, message.message_id, text)

    # ── ADMIN SELF-REPLY LEARNING ─────────────────────────────────────
    if (
        user.id == ADMIN_ID
        and message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == ADMIN_ID
    ):
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        if replied_text and text:
            if learn_from_reply(replied_text, text, ADMIN_ID):
                await message.reply_text("✅ Seekh liya~ 🧠💘")
                return

    # ── PM — sirf premium conversation ───────────────────────────────
    if chat.type == "private":
        from handlers.admin import pm_premium_conversation
        handled = await pm_premium_conversation(update, context)
        if handled:
            return
        return

    # ── CONVERSATION LEARNING ─────────────────────────────────────────
    if text and message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""

        if replied_user and replied_text:
            if replied_user.id == context.bot.id:
                # Bot ko reply kiya → seekho
                learn_from_bot_reply(replied_text, text)
            elif replied_user.id != user.id:
                # Do users ke beech conversation → seekho
                learn_from_conversation(replied_text, text, replied_user.id, user.id)

    # ── GROUP AUTO-MOD (premium) ──────────────────────────────────────
    if is_premium(chat.id):
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            user_is_admin = member.status in ("administrator", "creator")
        except Exception:
            user_is_admin = (user.id == ADMIN_ID)

        if not user_is_admin:
            if get_setting(chat.id, "antilink_on", False) and has_url(text):
                try:
                    await message.delete()
                    notif = await context.bot.send_message(
                        chat.id,
                        f"🔗 {user.mention_html()} — Links allowed nahi! 🚫",
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(5)
                    await notif.delete()
                except Exception:
                    pass
                return

            if get_setting(chat.id, "antifwd_on", False) and (
                message.forward_from or message.forward_from_chat
            ):
                try:
                    await message.delete()
                    notif = await context.bot.send_message(
                        chat.id,
                        f"↪️ {user.mention_html()} — Forwarded messages nahi! 🚫",
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(5)
                    await notif.delete()
                except Exception:
                    pass
                return

            locked = get_setting(chat.id, "locked_types", []) or []
            if locked:
                msg_type = None
                if message.sticker:     msg_type = "stickers"
                elif message.animation: msg_type = "gifs"
                elif message.poll:      msg_type = "polls"
                elif message.photo or message.video or message.document:
                    msg_type = "media"
                if msg_type and msg_type in locked:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    return

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
                            f"⚡ {user.mention_html()} flood ke liye 5 min muted! 🔇",
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

    # ── FILE AUTO-DELETE ──────────────────────────────────────────────
    if (
        is_premium(chat.id)
        and get_setting(chat.id, "autodel_on", False)
        and (message.document or message.video or message.audio)
    ):
        del_secs  = get_setting(chat.id, "autodel_time", 3600)
        delete_at = datetime.now() + timedelta(seconds=del_secs)
        schedule_delete(chat.id, message.message_id, delete_at)

    # ── CHATBOT CHECK ─────────────────────────────────────────────────
    if not get_setting(chat.id, "chat_bot_on", True):
        return

    if not text:
        return

    text_lower = text.lower().strip()
    bot_username = (context.bot.username or "").lower()

    mentioned = (
        f"@{bot_username}" in text_lower
        or any(t in text_lower for t in BOT_TRIGGERS)
    )

    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )

    has_bad_word = any(w in text_lower for w in BAD_WORDS)

    # Koi reply nahi kar raha (orphan) — 80% chance
    is_orphan = (
        not message.reply_to_message
        and not mentioned
        and not replied_to_bot
        and len(text) > 3
        and random.random() < 0.80
    )

    # ── RESPOND ───────────────────────────────────────────────────────

    if has_bad_word and (mentioned or replied_to_bot):
        await typing_delay(context, chat.id)
        await message.reply_text(get_nakhre())
        return

    if mentioned or replied_to_bot:
        await _send_smart_reply(update, context, text, chat.id)
        return

    if is_orphan:
        await typing_delay(context, chat.id)
        reply = find_reply(text)
        if reply:
            await message.reply_text(reply)
        else:
            await message.reply_text(make_girl_reply(text))
        return

    # Reply chain mein kabhi kabhi participate karo (15% chance)
    if (
        message.reply_to_message
        and not replied_to_bot
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id != context.bot.id
        and random.random() < 0.15
    ):
        reply = find_reply(text)
        if reply:
            await typing_delay(context, chat.id)
            await message.reply_text(reply)

# ── Smart reply sender ─────────────────────────────────────────────────

async def _send_smart_reply(update, context, text, chat_id):
    message = update.effective_message
    reply   = find_reply(text) or make_girl_reply(text)
    await typing_delay(context, chat_id)
    await message.reply_text(reply)
    if should_send_sticker():
        try:
            await context.bot.send_sticker(chat_id, get_sticker("happy"))
        except Exception:
            pass
