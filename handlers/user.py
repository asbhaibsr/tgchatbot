# User-facing commands and fun features.

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.persona import (
    to_cursive, to_bold, get_shayari, get_joke,
    get_compliment, get_roast, BOT_NAME
)
from core.db import save_user
import random
import os

ADMIN_ID       = int(os.environ.get("ADMIN_ID", "0"))
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"

HELP_ADMIN = (
    "👑 <b>Premium Commands</b> <i>(group must have premium)</i>\n\n"
    "/ban @user [reason] — Ban karo\n"
    "/unban @user — Unban karo\n"
    "/mute @user [1h/30m] — Mute karo (timed bhi)\n"
    "/unmute @user — Unmute karo\n"
    "/kick @user — Kick karo\n"
    "/warn @user [reason] — Warn karo\n"
    "/warns @user — Warn count dekho\n"
    "/resetwarn @user — Warns reset karo\n"
    "/purge [n] — Last N msgs delete karo\n"
    "/promote @user — Admin banao\n"
    "/demote @user — Admin hatao\n"
    "/tagall [msg] — Sabko tag karo\n"
    "/lock links/stickers/media/gifs — Lock karo\n"
    "/unlock &lt;type&gt; — Unlock karo\n"
    "/setwelcome [text] — Custom welcome\n"
    "/setgoodbye [text] — Custom goodbye\n"
    "/setrules [text] — Rules set karo\n\n"
    "🆓 <b>Free Admin Commands</b>\n\n"
    "/pin — Reply wala pin karo\n"
    "/unpin — Unpin karo\n"
    "/del — Reply wala delete karo\n"
    "/adminlist — Admins list\n"
    "/teach trigger | reply — Bot sikhaao\n"
    "/forget trigger — Pattern bhulao\n"
    "/patterns — Sikhe hue patterns\n"
    "/settings — Group settings panel\n"
    "/broadcast msg — Sab ko message (Owner only)"
)

HELP_USER = (
    "📌 <b>General Commands</b>\n\n"
    "/start — Bot start karo\n"
    "/help — Ye message\n"
    "/id — User ya Chat ID\n"
    "/about — Bot info\n"
    "/rules — Group rules dekhna\n"
    "/premium — Premium plan dekho\n\n"
    "🎭 <b>Fun</b>\n\n"
    "/font [text] — Stylish font banao\n"
    "/shayari — Random shayari\n"
    "/joke — Random joke\n"
    "/compliment — Compliment pao\n"
    "/roast @user — Roast karo 🔥\n"
    "/sticker — Random sticker\n"
    "/report — Msg report karo admins ko"
)

# ── HELP ─────────────────────────────────────────────────────────────

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👮 ᴀᴅᴍɪɴ ᴄᴍᴅꜱ", callback_data="help_admin"),
            InlineKeyboardButton("👤 ᴜꜱᴇʀ ᴄᴍᴅꜱ", callback_data="help_user"),
        ],
        [InlineKeyboardButton("👑 ᴘʀᴇᴍɪᴜᴍ", callback_data="prem_info")],
        [InlineKeyboardButton("✖️ ᴄʟᴏꜱᴇ", callback_data="close")],
    ])
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"📖 <b>{BOT_NAME} — Help Menu</b>\n\nNeeche category choose karo:",
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        me = await context.bot.get_me()
        await update.message.reply_text(
            f"📖 <b>Help</b>\n\nFull help PM mein milega 👇",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "📩 ᴏᴘᴇɴ ʜᴇʟᴘ",
                    url=f"https://t.me/{me.username}?start=help"
                )
            ]])
        )

# ── FONT ─────────────────────────────────────────────────────────────

async def font_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "Kuch text do na! 😅\n\nFormat: /font tumhara text"
        )
    text    = " ".join(context.args)
    cursive = to_cursive(text)
    bold    = to_bold(text)
    await update.message.reply_text(
        f"✨ <b>Stylish Fonts:</b>\n\n"
        f"𝓒𝓾𝓻𝓼𝓲𝓿𝓮: {cursive}\n"
        f"𝗕𝗼𝗹𝗱: {bold}",
        parse_mode="HTML"
    )

# ── SHAYARI ──────────────────────────────────────────────────────────

async def shayari_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shayaris = [
        "🌸 Mohabbat ki raah mein kaanton se daro na,\nJo dil se chaho use kabhi chhodna mat ~",
        "💘 Aankhon mein teri sapne hain mere,\nDil mein teri yaadon ka dera hai ~",
        "🌸 Zindagi teri mehfil mein aakar,\nKhud ko paa liya maine ~",
        "💘 Tu hai toh yeh duniya rangeen hai,\nTere bina sab sunsaan hai ~",
        "🌹 Kuch rishtey ankahi baaton se bante hain,\nKuch yaadein bina wajah ke yaad aati hain ~",
    ]
    await update.message.reply_text(random.choice(shayaris))

# ── JOKE ─────────────────────────────────────────────────────────────

async def joke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    jokes = [
        "Teacher: Future tense mein likho\nStudent: Main so jaaunga 😂\nTeacher: Bahut achha!\nStudent: Shukriya, ab sone do 💤",
        "Doctor: Aap bilkul theek hain\nMeri pocket: Hum nahi hain 😭",
        "Mummy: Beta kab aayega ghar?\nMain: Aa raha hoon\n3 ghante baad: Main woh hoon jo aa raha tha 😂",
        "Exam ke baad:\nPaper: Hard tha?\nMain: Woh main hi tha paper mein 💀",
    ]
    await update.message.reply_text(random.choice(jokes))

# ── COMPLIMENT ───────────────────────────────────────────────────────

async def compliment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    compliments = [
        "Tum bahut achhe insaan ho 🌸 Seriously!",
        "Tumhari smile toh mast hogi definitely 💘",
        "Tumse baat karke acha lagta hai 😊",
        "Tum kafi smart ho yaar 💅",
        "Tumhara vibe top tier hai 🔥",
    ]
    target = (
        update.message.reply_to_message.from_user
        if update.message.reply_to_message
        else update.effective_user
    )
    await update.message.reply_text(
        f"{target.full_name} ke liye:\n\n{random.choice(compliments)}"
    )

# ── ROAST ────────────────────────────────────────────────────────────

async def roast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roasts = [
        "Beta jao pehle aaina dekho 😂",
        "Sach mein? Sachhi? Wah re wah 🤣",
        "Main toh kehti hoon chup raho behtar lagoge 💅",
        "Arey yaar itna kuch tha toh ghar pe hi rehte na 😭",
        "Tameez seekho pehle phir aana 😤",
    ]
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.first_name
    elif context.args:
        target = context.args[0].lstrip("@")
    if not target:
        return await update.message.reply_text("Kisko roast karna hai? Reply karo ya @username do 😂")
    await update.message.reply_text(f"🔥 {target} ke liye:\n\n{random.choice(roasts)}")

# ── ABOUT ────────────────────────────────────────────────────────────

async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Channel", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("👤 Owner",   url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")],
    ])
    await update.message.reply_text(
        f"💘 <b>{BOT_NAME}</b>\n\n"
        f"Main ek smart group manager bot hoon~ 🌸\n\n"
        f"👑 <b>Owner:</b> {OWNER_USERNAME}\n"
        f"📢 <b>Updates:</b> {UPDATE_CHANNEL}\n\n"
        "🔰 <b>Features:</b>\n"
        "• Full group moderation\n"
        "• Premium subscription model\n"
        "• Anti-spam & flood control\n"
        "• Self-learning chat bot\n"
        "• Movie file copyright protection",
        parse_mode="HTML",
        reply_markup=markup
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

# ── REPORT ───────────────────────────────────────────────────────────

async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "🚨 Jis message ko report karna hai usse <b>reply</b> karke /report likho!",
            parse_mode="HTML"
        )
    reported_msg  = update.message.reply_to_message
    reported_user = reported_msg.from_user
    if not reported_user:
        return await update.message.reply_text("❌ Ye message kisi user ka nahi hai!")
    if reported_user.id == update.effective_user.id:
        return await update.message.reply_text("Apne aap ko report? 😂")
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ ᴡᴀʀɴ", callback_data=f"rep_warn_{reported_user.id}"),
            InlineKeyboardButton("🔇 ᴍᴜᴛᴇ", callback_data=f"rep_mute_{reported_user.id}"),
            InlineKeyboardButton("🔨 ʙᴀɴ",  callback_data=f"rep_ban_{reported_user.id}"),
        ],
        [InlineKeyboardButton("✖️ ᴅɪꜱᴍɪꜱꜱ", callback_data="close")],
    ])
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        admin_mentions = " ".join(
            f'<a href="tg://user?id={a.user.id}">{a.user.first_name}</a>'
            for a in admins if not a.user.is_bot
        )
    except Exception:
        admin_mentions = "Admins"
    await update.message.reply_text(
        f"🚨 <b>Report Alert!</b> {admin_mentions}\n\n"
        f"👤 Reported: {reported_user.full_name} (<code>{reported_user.id}</code>)\n"
        f"📝 By: {update.effective_user.full_name}",
        parse_mode="HTML",
        reply_to_message_id=reported_msg.message_id,
        reply_markup=markup
    )
    try:
        await update.message.delete()
    except Exception:
        pass

# ── CALLBACKS: help_admin / help_user / report actions ───────────────

async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    if data == "help_main":
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👮 ᴀᴅᴍɪɴ", callback_data="help_admin"),
                InlineKeyboardButton("👤 ᴜꜱᴇʀ",  callback_data="help_user"),
            ],
            [InlineKeyboardButton("👑 ᴘʀᴇᴍɪᴜᴍ", callback_data="prem_info")],
            [InlineKeyboardButton("✖️ ᴄʟᴏꜱᴇ", callback_data="close")],
        ])
        await query.edit_message_text(
            f"📖 <b>{BOT_NAME} — Help</b>\n\nCategory choose karo:",
            parse_mode="HTML",
            reply_markup=markup
        )

    elif data == "help_admin":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data="help_main")]])
        await query.edit_message_text(HELP_ADMIN, parse_mode="HTML", reply_markup=markup)

    elif data == "help_user":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data="help_main")]])
        await query.edit_message_text(HELP_USER, parse_mode="HTML", reply_markup=markup)

    # ── Report action callbacks ───────────────────────────────────────
    elif data.startswith("rep_"):
        from telegram.constants import ChatMemberStatus
        try:
            m = await context.bot.get_chat_member(chat_id, user_id)
            adm = m.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        except Exception:
            adm = (user_id == ADMIN_ID)
        if not adm:
            return await query.answer("Sirf admins!", show_alert=True)
        parts  = data.split("_")
        action = parts[1]
        uid    = int(parts[2])
        from core.db import add_warn, get_setting, reset_warns, is_premium
        if not is_premium(chat_id):
            return await query.answer("Premium required!", show_alert=True)
        try:
            if action == "warn":
                wl  = get_setting(chat_id, "warn_limit", 3)
                cnt = add_warn(chat_id, uid, "Reported by user", user_id)
                if cnt >= wl:
                    await context.bot.ban_chat_member(chat_id, uid)
                    reset_warns(chat_id, uid)
                    await query.answer("Warned + Auto-banned!")
                else:
                    await query.answer(f"Warned! ({cnt}/{wl})")
            elif action == "mute":
                from telegram import ChatPermissions
                from datetime import timedelta
                await context.bot.restrict_chat_member(
                    chat_id, uid,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=__import__("datetime").datetime.now() + timedelta(hours=1)
                )
                await query.answer("Muted for 1h!")
            elif action == "ban":
                await context.bot.ban_chat_member(chat_id, uid)
                await query.answer("Banned!")
            await query.edit_message_reply_markup(None)
        except Exception as e:
            await query.answer(f"Error: {e}", show_alert=True)
