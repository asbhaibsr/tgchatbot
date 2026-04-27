from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.persona import (
    to_cursive, to_bold, get_shayari, get_joke,
    get_compliment, get_roast, BOT_NAME
)
from core.db import save_user

# ── HELP ─────────────────────────────────────────────────────────────

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 User Cmds", callback_data="help_user"),
            InlineKeyboardButton("👑 Admin Cmds", callback_data="help_admin")
        ],
        [InlineKeyboardButton("💘 About Bot", callback_data="about")]
    ])
    await update.message.reply_text(
        f"🌸 <b>{BOT_NAME}</b>\n\nKya jaanna chahte ho? 👇",
        parse_mode="HTML",
        reply_markup=btn
    )

# ── FONT ─────────────────────────────────────────────────────────────

async def font_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "Kuch text do na! 😅\n\nFormat: /font tumhara text\n\nStyles:\n"
            "/font1 = 𝓒𝓾𝓻𝓼𝓲𝓿𝓮\n/font2 = 𝗕𝗼𝗹𝗱"
        )
    text     = " ".join(context.args)
    cursive  = to_cursive(text)
    bold     = to_bold(text)
    await update.message.reply_text(
        f"✨ <b>Stylish Fonts:</b>\n\n"
        f"𝓒𝓾𝓻𝓼𝓲𝓿𝓮: {cursive}\n"
        f"𝗕𝗼𝗹𝗱: {bold}",
        parse_mode="HTML"
    )

# ── SHAYARI ──────────────────────────────────────────────────────────

async def shayari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_shayari())

# ── JOKE ─────────────────────────────────────────────────────────────

async def joke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_joke())

# ── COMPLIMENT ───────────────────────────────────────────────────────

async def compliment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"💘 {user.first_name} ke liye:\n\n{get_compliment()}"
    )

# ── ROAST ────────────────────────────────────────────────────────────

async def roast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.first_name
    elif context.args:
        target = context.args[0].lstrip("@")

    if not target:
        return await update.message.reply_text("Kisko roast karna hai? Reply karo ya @username do 😂")

    await update.message.reply_text(
        f"🔥 {target} ke liye:\n\n{get_roast()}"
    )

# ── ABOUT ────────────────────────────────────────────────────────────

async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💘 <b>{BOT_NAME}</b>\n\n"
        f"Main ek smart, self-learning group bot hoon~ 🌸\n\n"
        f"🧠 Self-learning: Haan!\n"
        f"🌍 Group + PM: Dono mein kaam karti hoon\n"
        f"💬 Language: Hinglish\n"
        f"🎭 Mood: Always fun!\n\n"
        f"Made with 💘 for amazing groups~",
        parse_mode="HTML"
    )

# ── ID ───────────────────────────────────────────────────────────────

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    text = (
        f"👤 <b>Tumhari Info:</b>\n"
        f"┌ Name: {user.full_name}\n"
        f"├ User ID: <code>{user.id}</code>\n"
        f"└ Username: @{user.username or 'N/A'}\n\n"
    )
    if chat.type != "private":
        text += (
            f"👥 <b>Group Info:</b>\n"
            f"┌ Name: {chat.title}\n"
            f"└ Chat ID: <code>{chat.id}</code>"
        )
    await update.message.reply_text(text, parse_mode="HTML")

# ── STICKER ──────────────────────────────────────────────────────────

async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.persona import get_sticker
    sticker_id = get_sticker("happy")
    try:
        await update.message.reply_sticker(sticker_id)
    except Exception:
        await update.message.reply_text("Sticker IDs set nahi hain abhi 😅 Admin se bolo!")
