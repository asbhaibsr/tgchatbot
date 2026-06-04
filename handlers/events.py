# Event Handlers — Welcome/Goodbye, Bot Add/Remove, Callbacks (help/about/settings/premium)

import os
import asyncio
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from core.db import save_user, save_group, remove_group, get_setting
from core.persona import BOT_NAME

ADMIN_ID      = int(os.environ.get("ADMIN_ID", "0"))
LOG_CHANNEL   = os.environ.get("LOG_CHANNEL_ID", "")
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"

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

    username_link = f"@{user.username}" if user.username else f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    await send_log(
        context,
        f"👤 <b>New User Started Bot</b>\n"
        f"┌ Name: {user.full_name}\n"
        f"├ ID: <code>{user.id}</code>\n"
        f"└ Link: {username_link}"
    )

    me = await context.bot.get_me()
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 ʜᴇʟᴘ", callback_data="help_main"),
            InlineKeyboardButton("ℹ️ ᴀʙᴏᴜᴛ", callback_data="about"),
        ],
        [InlineKeyboardButton("👑 ɢᴇᴛ ᴘʀᴇᴍɪᴜᴍ", callback_data="prem_info")],
        [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇꜱ", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}")],
    ])
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"<b>Heyy {user.first_name}! 🌸</b>\n\n"
            f"Main hoon <b>{BOT_NAME}</b> — tumhara powerful Telegram group manager!\n\n"
            "🛡 <b>Features:</b>\n"
            "• Full moderation — ban, mute, kick, warn\n"
            "• Anti-spam, anti-link, flood control\n"
            "• Custom welcome & goodbye\n"
            "• Premium subscription system\n"
            "• Pattern-based self-learning chat bot\n"
            "• Movie file copyright protection\n\n"
            "👇 Group mein add karo aur /settings se sab set karo!",
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        await update.message.reply_text(
            f"<b>Heyy! Main hoon {BOT_NAME} 🌸</b>\n"
            "Admin commands ke liye /help karo!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "💬 ᴘᴍ ꜰᴏʀ ʜᴇʟᴘ",
                    url=f"https://t.me/{me.username}?start=help"
                )
            ]])
        )

# ── Bot group mein add hua / nikala ───────────────────────────────────

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat   = result.chat
    new    = result.new_chat_member

    if new.status in ("member", "administrator"):
        save_group(chat)
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
            text=(
                f"<b>Heyy sab! Main hoon {BOT_NAME} 🌸</b>\n\n"
                "Group management ke liye ready hoon!\n\n"
                "👮 Admin /settings karo sab configure karne ke liye.\n"
                "👑 Premium features ke liye /premium dekhna."
            ),
            parse_mode="HTML"
        )
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

    if not get_setting(chat.id, "welcome_on", True):
        return

    for member in message.new_chat_members:
        if member.is_bot:
            continue
        save_user(member)

        custom_msg = get_setting(chat.id, "welcome_msg", None)
        if custom_msg:
            text = custom_msg.replace("{name}", member.full_name)
            text = text.replace("{group}", chat.title or "")
        else:
            text = (
                f"<b>Heyy {member.full_name}! 🌸</b>\n\n"
                f"Welcome to <b>{chat.title}</b>!\n"
                "Enjoy karo aur rules follow karo~ 💘\n"
                "/rules se group rules dekho."
            )
        await message.reply_text(text, parse_mode="HTML")

# ── Member group se gaya ──────────────────────────────────────────────

async def left_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    member  = message.left_chat_member
    if not member or member.is_bot:
        return
    if not get_setting(update.effective_chat.id, "goodbye_on", True):
        return
    custom_msg = get_setting(update.effective_chat.id, "goodbye_msg", None)
    if custom_msg:
        text = custom_msg.replace("{name}", member.full_name)
    else:
        text = f"<b>{member.full_name} chale gaye!</b> 👋\nMiss karenge~"
    await message.reply_text(text, parse_mode="HTML")

# ── Master callback handler ────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    # Route to admin callbacks first (settings, premium, unban, etc.)
    admin_cb_data = (
        "unban_", "unmute_", "resetwarn_",
        "prem_", "tog_", "cycle_", "settings_", "prem_locked",
        "close", "rep_warn_", "rep_mute_", "rep_ban_"
    )
    admin_prefixes = (
        "unban_", "unmute_", "resetwarn_",
        "prem_", "tog_", "cycle_", "settings_",
        "rep_"
    )
    admin_exact = ("prem_locked", "close", "prem_info", "prem_start")

    is_admin_cb = data in admin_exact or any(data.startswith(p) for p in admin_prefixes)

    if is_admin_cb:
        from handlers.admin import admin_callback_handler
        return await admin_callback_handler(update, context)

    # User callbacks
    user_cb = ("help_main", "help_admin", "help_user")
    if data in user_cb:
        from handlers.user import user_callback_handler
        return await user_callback_handler(update, context)

    # about
    if data == "about":
        await query.answer()
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Channel", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}"),
                InlineKeyboardButton("👤 Owner",   url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"),
            ],
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data="help_main")],
        ])
        from core.persona import BOT_NAME
        await query.edit_message_text(
            f"🤖 <b>{BOT_NAME}</b>\n\n"
            "Powerful Telegram Group Manager 🌸\n\n"
            f"👨‍💻 Owner: {OWNER_USERNAME}\n"
            f"📢 Channel: {UPDATE_CHANNEL}",
            parse_mode="HTML",
            reply_markup=markup
        )
        return

    await query.answer()
