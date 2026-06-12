import os
import asyncio
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes

from core.db import (
    save_user, save_group, remove_group,
    get_setting, is_premium,
    set_captcha, get_captcha, del_captcha,
    record_raid_join, detect_raid,
    set_captcha_token,
)
from core.persona import BOT_NAME, get_welcome, get_goodbye

ADMIN_ID       = int(os.environ.get("ADMIN_ID", "0"))
LOG_CHANNEL    = os.environ.get("LOG_CHANNEL_ID", "")
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"


# ══════════════════════════════════════════════════════════
# LOG HELPER
# ══════════════════════════════════════════════════════════

async def send_log(context, text: str):
    if LOG_CHANNEL:
        try:
            await context.bot.send_message(
                chat_id=int(LOG_CHANNEL), text=text,
                parse_mode="HTML", disable_web_page_preview=True,
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
# /start  (handles /start premium parameter too)
# ══════════════════════════════════════════════════════════

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    # ── /start premium → begin subscription flow ──────────
    if context.args and context.args[0].lower() in ("premium", "subscribe"):
        from handlers.admin import prem_start_handler
        return await prem_start_handler(update, context)

    # ── /start cap_CHATID_USERID → captcha verification ───
    if context.args and context.args[0].startswith("cap_"):
        parts = context.args[0].split("_")
        if len(parts) == 3:
            try:
                cap_chat_id = int(parts[1])
                cap_user_id = int(parts[2])
            except ValueError:
                cap_chat_id = cap_user_id = 0

            if cap_user_id == user.id and cap_chat_id:
                captcha_doc = get_captcha(cap_chat_id, cap_user_id)
                if captcha_doc:
                    # Generate 6-char token
                    import string as _str
                    token = "".join(random.choices(_str.ascii_uppercase + _str.digits, k=6))
                    msg_id = captcha_doc.get("message_id", 0)
                    set_captcha_token(cap_chat_id, cap_user_id, token, msg_id)
                    try:
                        group_name = (await context.bot.get_chat(cap_chat_id)).title
                    except Exception:
                        group_name = "Group"
                    await update.message.reply_text(
                        f"🔐 <b>Verification Code</b>\n\n"
                        f"📍 Group: <b>{group_name}</b>\n\n"
                        f"Tera code:\n<code>{token}</code>\n\n"
                        f"Wapas group mein jao aur sirf ye code type karo.\n"
                        f"⏳ 5 minute mein expire hoga!",
                        parse_mode="HTML",
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ Captcha expired ya already verified hai!\n"
                        "Group mein wapas jao.",
                    )
                return

    username_link = (
        f"@{user.username}" if user.username
        else f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    )
    await send_log(
        context,
        f"👤 <b>New User</b>\n"
        f"┌ {user.full_name}\n"
        f"├ <code>{user.id}</code>\n"
        f"└ {username_link}",
    )

    me = await context.bot.get_me()
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Help",  callback_data="help_main"),
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
        ],
        [InlineKeyboardButton("👑 Get Premium",      callback_data="prem_info")],
        [InlineKeyboardButton("📢 Updates Channel",  url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("➕ Add to Group",
                              url=f"https://t.me/{me.username}?startgroup=start")],
    ])

    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"<b>Heyy {user.first_name}! 🌸</b>\n\n"
            f"Main hoon <b>{BOT_NAME}</b>~\n"
            "Tera powerful Telegram group manager!\n\n"
            "🆓 <b>Free:</b> Anti-Gaali • Notes • AI Chatbot • Warn/Ban/Mute\n"
            "👑 <b>Premium:</b> Anti-Link • Anti-Raid • Movie System • Captcha • Analytics\n\n"
            "👇 Group mein add karo aur /settings se configure karo!",
            parse_mode="HTML",
            reply_markup=markup,
        )
    else:
        await update.message.reply_text(
            f"<b>Heyy! Main hoon {BOT_NAME} 🌸</b>\n"
            "Admin commands ke liye /help karo!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "💬 PM for help",
                    url=f"https://t.me/{me.username}?start=help",
                )
            ]]),
        )


# ══════════════════════════════════════════════════════════
# BOT ADD / REMOVE (called by ChatMemberHandler)
# ══════════════════════════════════════════════════════════

async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if not result:
        return
    chat = result.chat
    new  = result.new_chat_member

    if new.status in ("member", "administrator"):
        save_group(chat)
        try:
            link = await context.bot.export_chat_invite_link(chat.id)
        except Exception:
            link = "N/A"
        await send_log(
            context,
            f"🟢 <b>Bot Added</b>\n┌ {chat.title}\n├ <code>{chat.id}</code>\n└ {link}",
        )
        me = await context.bot.get_me()
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text=(
                    f"<b>Heyy sab! Main hoon {BOT_NAME} 🌸</b>\n\n"
                    "Ab is group ka protection mere haath mein hai!\n\n"
                    "🔧 Setup:\n"
                    "• /settings → sab features toggle karo\n"
                    "• /setwelcome → custom welcome\n"
                    "• /setrules → group rules\n"
                    "• /help → poori commands list\n"
                    "• /premium → premium features\n\n"
                    "<i>Note: Bot ko admin banao taaki sab features kaam karein!</i>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings_open"),
                    InlineKeyboardButton("📖 Help",     callback_data="help_main"),
                ]]),
            )
        except Exception:
            pass

    elif new.status in ("left", "kicked", "banned"):
        remove_group(chat.id)
        await send_log(
            context,
            f"🔴 <b>Bot Removed</b>\n┌ {chat.title}\n└ <code>{chat.id}</code>",
        )


# ══════════════════════════════════════════════════════════
# NEW MEMBER (welcome + captcha + anti-raid)
# ══════════════════════════════════════════════════════════

async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message

    for member in message.new_chat_members:
        if member.is_bot:
            continue
        save_user(member)

        # Anti-Raid (PREMIUM)
        if is_premium(chat.id) and get_setting(chat.id, "antiraid_on", False):
            record_raid_join(chat.id, member.id)
            if detect_raid(chat.id, window_sec=30, threshold=5):
                try:
                    await context.bot.set_chat_permissions(
                        chat.id, permissions=ChatPermissions(can_send_messages=False),
                    )
                except Exception:
                    pass
                await message.reply_text(
                    "🚨 <b>RAID DETECTED!</b>\n\n"
                    "5+ users joined in 30 seconds!\n"
                    "Group temporarily <b>LOCKED</b> 🔒\n\n"
                    "Admins — /unlock_raid type karo jab safe ho!",
                    parse_mode="HTML",
                )
                await send_log(
                    context,
                    f"🚨 <b>RAID ALERT</b>\n"
                    f"Group: {chat.title} (<code>{chat.id}</code>)",
                )
                return

        # Captcha (PREMIUM) — NEW: PM-based number verification
        if is_premium(chat.id) and get_setting(chat.id, "captcha_on", False):
            try:
                await context.bot.restrict_chat_member(
                    chat.id, member.id,
                    permissions=ChatPermissions(can_send_messages=False),
                )
            except Exception:
                pass

            me = await context.bot.get_me()
            start_param = f"cap_{chat.id}_{member.id}"

            sent = await message.reply_text(
                f"👋 {member.mention_html()} — Welcome!\n\n"
                f"🔐 <b>Verify karo to chat karo!</b>\n\n"
                f"Step 1️⃣  → Niche 'Verify Now' button dabao\n"
                f"Step 2️⃣  → Bot se code lo (PM mein)\n"
                f"Step 3️⃣  → Wapas aao aur code type karo\n\n"
                f"⏳ <b>5 min</b> mein verify nahi hua → <b>Kick!</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "✅ Verify Now",
                        url=f"https://t.me/{me.username}?start={start_param}",
                    )
                ]]),
            )
            set_captcha(chat.id, member.id, "pending", sent.message_id)

            async def _auto_kick_new(cid, uid, mid):
                await asyncio.sleep(300)   # 5 min
                if get_captcha(cid, uid):
                    del_captcha(cid, uid)
                    try:
                        await context.bot.ban_chat_member(cid, uid)
                        await asyncio.sleep(1)
                        await context.bot.unban_chat_member(cid, uid)
                    except Exception:
                        pass
                    try:
                        await context.bot.delete_message(cid, mid)
                    except Exception:
                        pass

            asyncio.create_task(_auto_kick_new(chat.id, member.id, sent.message_id))
            continue

        # Welcome
        if not get_setting(chat.id, "welcome_on", True):
            continue
        custom = get_setting(chat.id, "welcome_msg", None)
        text   = (
            custom
            .replace("{name}", member.mention_html())
            .replace("{group}", chat.title or "")
            if custom else get_welcome(member.mention_html())
        )
        rules  = get_setting(chat.id, "rules", None)
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 Group Rules", callback_data="show_rules")
        ]]) if rules else None
        await message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# ══════════════════════════════════════════════════════════
# LEFT MEMBER
# ══════════════════════════════════════════════════════════

async def left_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    member  = message.left_chat_member
    if not member or member.is_bot:
        return
    if not get_setting(update.effective_chat.id, "goodbye_on", True):
        return
    custom = get_setting(update.effective_chat.id, "goodbye_msg", None)
    text   = (
        custom.replace("{name}", member.full_name)
        if custom else get_goodbye(member.full_name)
    )
    await message.reply_text(text, parse_mode="HTML")


# ══════════════════════════════════════════════════════════
# UNLOCK RAID
# ══════════════════════════════════════════════════════════

async def unlock_raid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    from handlers.admin import _is_user_admin
    if not await _is_user_admin(context, chat.id, user.id):
        await update.effective_message.reply_text("❌ Sirf admins!")
        return
    try:
        await context.bot.set_chat_permissions(
            chat.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
            ),
        )
        from core.db import clear_raid_log
        clear_raid_log(chat.id)
        await update.effective_message.reply_text("✅ Group unlock! Raid log clear. 🌸")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")


# ══════════════════════════════════════════════════════════
# MASTER CALLBACK ROUTER
# ALL button callbacks route here first
# ══════════════════════════════════════════════════════════

# Prefixes that go to admin_callback_handler
_ADMIN_PREFIXES = (
    "unban_", "unmute_", "resetwarn_",
    "prem_a_", "prem_r_",
    "tog_", "cycle_",
    "settings_", "scat_",           # ← scat_ = settings category
    "rep_", "locktype_",
    "tagall_stop_",
    "tagall_resume_",
)

_ADMIN_EXACT = {
    "prem_locked", "prem_info", "prem_start",
    "close", "settings_main",
    "settings_flood", "settings_autodel",
    "settings_warn", "settings_locks",
    "automod_dismiss",   # NEW: dismiss warning messages
}

_ADMIN_PREFIX_EXTRA = ("biofree_prompt_",)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    # Captcha buttons
    if data.startswith("captcha_"):
        from handlers.chat import captcha_callback_handler
        return await captcha_callback_handler(update, context)

    # Admin callbacks
    if data in _ADMIN_EXACT or any(data.startswith(p) for p in _ADMIN_PREFIXES) or any(data.startswith(p) for p in _ADMIN_PREFIX_EXTRA):
        from handlers.admin import admin_callback_handler
        return await admin_callback_handler(update, context)

    # Help / user callbacks
    if data in ("help_main", "help_admin", "help_user"):
        from handlers.user import user_callback_handler
        return await user_callback_handler(update, context)

    # About
    if data == "about":
        await query.answer()
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Channel", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}"),
                InlineKeyboardButton("👤 Owner",   url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}"),
            ],
            [InlineKeyboardButton("« Back", callback_data="help_main")],
        ])
        try:
            await query.edit_message_text(
                f"🤖 <b>{BOT_NAME}</b>\n\n"
                "Advanced Telegram Group Manager 🌸\n\n"
                f"👨‍💻 Owner: {OWNER_USERNAME}\n"
                f"📢 Channel: {UPDATE_CHANNEL}\n\n"
                "Anti-Gaali • Anti-Raid • Movie System\n"
                "Notes • Analytics • Captcha • Smart AI 💘",
                parse_mode="HTML", reply_markup=markup,
            )
        except Exception:
            pass
        return

    # Show rules
    if data == "show_rules":
        await query.answer()
        rules = get_setting(query.message.chat.id, "rules", None)
        if rules:
            await query.message.reply_text(
                f"📋 <b>Group Rules:</b>\n\n{rules}", parse_mode="HTML"
            )
        else:
            await query.answer("Rules abhi set nahi hain!", show_alert=True)
        return

    # Settings open (from bot-added message)
    if data == "settings_open":
        from handlers.admin import settings_handler
        return await settings_handler(update, context)

    await query.answer()
