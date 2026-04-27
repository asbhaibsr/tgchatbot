import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from core.db import save_user, save_group, remove_group
from core.persona import get_welcome, get_goodbye, BOT_NAME

ADMIN_ID      = int(os.environ.get("ADMIN_ID", "0"))
LOG_CHANNEL   = os.environ.get("LOG_CHANNEL_ID", "")

async def send_log(context, text):
    if LOG_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=LOG_CHANNEL,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception:
            pass

# ── /start ────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    # Log channel mein bhejna
    username_link = f"@{user.username}" if user.username else f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    await send_log(
        context,
        f"👤 <b>New User Started Bot</b>\n"
        f"┌ Name: {user.full_name}\n"
        f"├ ID: <code>{user.id}</code>\n"
        f"└ Link: {username_link}"
    )

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💘 Help", callback_data="help"),
            InlineKeyboardButton("🌸 About", callback_data="about")
        ]
    ])
    await update.message.reply_text(
        f"Heyy! Main hoon {BOT_NAME} 💘\n\n"
        f"Group mein add karo mujhe aur maza karo~ 🌸\n"
        f"/help likhkar sab commands dekho!",
        reply_markup=btn
    )

# ── Bot group mein add hua / nikala ───────────────────────────────────

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat   = result.chat
    new    = result.new_chat_member

    # Bot add hua
    if new.status in ("member", "administrator"):
        save_group(chat)

        # Group link banao
        try:
            link = await context.bot.export_chat_invite_link(chat.id)
        except Exception:
            link = "N/A"

        await send_log(
            context,
            f"🟢 <b>Bot Added to Group</b>\n"
            f"┌ Group: {chat.title}\n"
            f"├ ID: <code>{chat.id}</code>\n"
            f"└ Link: {link}"
        )

        await context.bot.send_message(
            chat_id=chat.id,
            text=f"Heyy sab! Main hoon {BOT_NAME} 💘\n"
                 f"Ab is group mein maza aayega~ 🌸\n"
                 f"/help se sab commands dekho!"
        )

    # Bot hataaya gaya
    elif new.status in ("left", "kicked", "banned"):
        remove_group(chat.id)
        await send_log(
            context,
            f"🔴 <b>Bot Removed from Group</b>\n"
            f"┌ Group: {chat.title}\n"
            f"└ ID: <code>{chat.id}</code>"
        )

# ── Naya member group mein aaya ───────────────────────────────────────

async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message

    for member in message.new_chat_members:
        if member.is_bot:
            continue
        save_user(member)

        # Group invite link
        try:
            link = await context.bot.export_chat_invite_link(chat.id)
        except Exception:
            link = None

        welcome = get_welcome(member.full_name)
        if link:
            welcome += f"\n\n🔗 Group Link: {link}"

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Rules dekho", callback_data=f"rules_{chat.id}")]
        ])

        await message.reply_text(welcome, reply_markup=btn)

# ── Member group se gaya ──────────────────────────────────────────────

async def left_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    member  = message.left_chat_member
    if member and not member.is_bot:
        await message.reply_text(get_goodbye(member.full_name))

# ── Callback buttons ──────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "help":
        text = (
            "🌸 <b>Commands</b>\n\n"
            "👤 <b>User:</b>\n"
            "/start - Bot se milo\n"
            "/help - Help dekho\n"
            "/font [text] - Stylish font\n"
            "/shayari - Shayari suno\n"
            "/joke - Joke suno\n"
            "/compliment - Compliment lo\n"
            "/roast @user - Roast karo\n\n"
            "👑 <b>Admin:</b>\n"
            "/ban @user\n"
            "/unban @user\n"
            "/mute @user\n"
            "/unmute @user\n"
            "/kick @user\n"
            "/warn @user\n"
            "/pin\n"
            "/setwelcome [msg]\n"
            "/teach trigger | response\n"
            "/forget trigger\n"
            "/broadcast [msg]"
        )
        await query.edit_message_text(text, parse_mode="HTML")

    elif data == "about":
        text = (
            f"💘 <b>{BOT_NAME}</b>\n\n"
            "Main ek smart group bot hoon~\n"
            "Self-learning karta hoon 🧠\n"
            "Group manage bhi karta hoon 👑\n"
            "Aur sabse baat bhi karta hoon 🌸"
        )
        await query.edit_message_text(text, parse_mode="HTML")
