"""
Smart Chat Handler
────────────────────────────────────────────
1. Bot sirf tab bolegi jab:
   - Usse directly @mention kiya gaya ho
   - Uske trigger words aaye (cutie, cutie pie etc)
   - Koi bina kisi ke reply ke message aaye (orphan)
   - 5-6 messages ke baad kabhi kabhi (interjection)

2. Typing indicator dikhti hai reply se pehle

3. 12% chance pe sticker bhi bhejti hai

4. Admin apne message ko khud reply kare → pattern sikha

5. Koi bura bolne pe nakhre wala reply
"""

import os
import asyncio
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from core.db import (
    save_user, save_message, is_blocked,
    increment_counter, reset_counter
)
from core.brain import find_reply, learn_from_reply
from core.persona import (
    BOT_TRIGGERS, get_interjection, get_orphan_reply,
    get_nakhre, get_sticker, should_send_sticker
)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# Gande / bure words — bot nakhre wala jawab degi
BAD_WORDS = [
    "gandu", "chutiya", "madarchod", "bhenchod", "harami",
    "randi", "saali", "mc", "bc", "sala", "bhosdike"
]

# ── Typing delay ───────────────────────────────────────────────────────

async def typing_delay(context, chat_id, text=""):
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    # Message ki length ke hisaab se delay
    delay = min(1.5 + len(text) * 0.02, 4.0)
    await asyncio.sleep(delay)

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

    # User save karo
    save_user(user)

    # Message save karo (memory ke liye)
    if text:
        save_message(chat.id, user.id, text)

    # ── ADMIN LEARNING: Admin ne apna hi message reply kiya ──────────
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

    # ── Private chat mein hamesha respond karo ────────────────────────
    if chat.type == "private":
        await _send_smart_reply(update, context, text, chat.id)
        return

    # ── GROUP logic ───────────────────────────────────────────────────

    text_lower = text.lower()

    # 1. Direct mention ya trigger word check
    bot_username = context.bot.username or ""
    mentioned = (
        f"@{bot_username}".lower() in text_lower
        or any(t in text_lower for t in BOT_TRIGGERS)
    )

    # 2. Reply to bot check
    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )

    # 3. Bura word aaya
    has_bad_word = any(w in text_lower for w in BAD_WORDS)

    # 4. Orphan message — koi bina kisi ke reply ke message aaye
    #    (sirf agar group mein recent messages mein koi reply chain nahi)
    is_orphan = (
        not message.reply_to_message
        and not mentioned
        and not replied_to_bot
        and len(text) > 5
        and random.random() < 0.08  # 8% chance orphan pe reply
    )

    # 5. Beech mein bolna — counter
    counter = increment_counter(chat.id)
    should_interject = False
    if counter >= random.randint(5, 7):
        should_interject = True
        reset_counter(chat.id)

    # ── RESPOND ────────────────────────────────────────────────────────

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

    # Pattern dhundo
    reply = find_reply(text) if text else None

    if reply:
        await typing_delay(context, chat_id, reply)
        await message.reply_text(reply)
        # Kabhi kabhi sticker bhi
        if should_send_sticker():
            sticker_id = get_sticker("happy")
            try:
                await context.bot.send_sticker(chat_id, sticker_id)
            except Exception:
                pass
    else:
        # Koi pattern nahi mila → chup raho (group mein)
        # PM mein generic reply
        if update.effective_chat.type == "private":
            await typing_delay(context, chat_id, "hmm")
            fallbacks = [
                "Hmm... samjha nahi main 😅 Kuch aur puchho~",
                "Yeh toh pata nahi mujhe 🥺 Kuch aur batao!",
                "Arey seedha batao kya chahiye 😄",
                "Main seekh rahi hoon abhi~ Thoda time do 🌸",
            ]
            await message.reply_text(random.choice(fallbacks))
