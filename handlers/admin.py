import os, asyncio, random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes

from core.db import (
    get_setting, set_setting, toggle_setting,
    is_premium, grant_premium, revoke_premium, get_all_premium_groups,
    add_warn, get_warns, get_warn_reasons, reset_warns,
    save_prem_request,
    prem_state_get, prem_state_set, prem_state_del, prem_state_exists,
    block_user, unblock_user, is_blocked,
    save_note, get_note, get_all_notes, delete_note,
    get_group_stats, get_top_users, get_user_msg_count, get_user_info,
    reset_gaali_strikes, get_all_users, get_all_groups,
    add_scheduled, get_scheduled, del_scheduled,
    set_tagall_job, get_tagall_job, pause_tagall, resume_tagall,
    update_tagall_progress, clear_tagall_job, is_tagall_paused,
    save_sticker, get_stickers, clear_stickers,
    remove_sticker,
)

ADMIN_ID       = int(os.environ.get("ADMIN_ID", "0"))
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"
PREMIUM_PRICE  = int(os.environ.get("PREMIUM_PRICE", "99"))
BOT_NAME       = "ᴀꜱ ɢʀᴏᴜᴘ ʙᴏᴛ"

# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _progress_bar(pct: int, length: int = 10) -> str:
    """Fancy block progress bar — e.g. ████▒▒▒▒▒▒ 40%"""
    filled = round(pct / 100 * length)
    empty  = length - filled
    return f"{'█' * filled}{'▒' * empty} {pct}%"

def _warn_bar(n: int, limit: int) -> str:
    """Warn progress bar with colored blocks."""
    pct    = int(n / limit * 100) if limit else 0
    filled = round(n / limit * 10) if limit else 0
    empty  = 10 - filled
    color  = "🟥" if pct >= 80 else ("🟧" if pct >= 50 else "🟨")
    return f"{color * filled}{'⬜' * empty}  {n}/{limit}"

_LOAD_STEPS = [
    ("⋘ 𝑙𝑜𝑎𝑑𝑖𝑛𝑔 𝑑𝑎𝑡𝑎... ⋙",   _progress_bar(10)),
    ("⋘ 𝑃𝑙𝑒𝑎𝑠𝑒 𝑤𝑎𝑖𝑡... ⋙",   _progress_bar(50)),
    ("⋘ 𝑠𝑎𝑣𝑖𝑛𝑔... ⋙",         _progress_bar(80)),
]

def _is_owner(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def _is_user_admin(context, chat_id: int, user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        m = await context.bot.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "creator")
    except Exception:
        return False

async def _get_target(update, context, chat_id: int):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    if context.args:
        try:
            uid = int(context.args[0])
            m   = await context.bot.get_chat_member(chat_id, uid)
            return m.user
        except Exception:
            pass
    return None

# ══════════════════════════════════════════════════════════
# SETTINGS PANEL
# ══════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────
# NEW CATEGORY-BASED SETTINGS PANEL
# Main → Category → Detail + Toggle
# ──────────────────────────────────────────────────────────

# Key defaults — some settings are ON by default
_KEY_DEFAULTS = {
    "welcome_on":   True,
    "goodbye_on":   True,
    "chat_bot_on":  True,
    "movie_on":     True,
}

def _tog_btn(chat_id, label, key, default=False, crown=""):
    val  = get_setting(chat_id, key, _KEY_DEFAULTS.get(key, default))
    icon = "✅" if val else "❌"
    return InlineKeyboardButton(f"{icon} {label}{crown}", callback_data=f"tog_{key}")

def _main_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    prem = is_premium(chat_id)
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Chatbot",        callback_data="scat_chatbot"),
            InlineKeyboardButton("👋 Welcome",         callback_data="scat_welcome"),
        ],
        [
            InlineKeyboardButton("🛡 Anti-Spam",       callback_data="scat_antispam"),
            InlineKeyboardButton("🎬 Movie Sys",       callback_data="scat_movie"),
        ],
        [
            InlineKeyboardButton("⚡ Advanced",        callback_data="scat_advanced"),
            InlineKeyboardButton("❌ Close",            callback_data="close"),
        ],
    ])

def _chatbot_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    solo_pct = get_setting(chat_id, "chat_solo_pct", 80)
    utu_pct  = get_setting(chat_id, "chat_utu_pct",  10)
    def _pct_row(key, cur):
        return [
            InlineKeyboardButton(
                f"{'●' if p == cur else p}%",
                callback_data=f"set_pct_{key}_{p}",
            )
            for p in [0, 10, 20, 30, 50, 80, 100]
        ]
    return InlineKeyboardMarkup([
        [_tog_btn(chat_id, "🤖 Chat Reply", "chat_bot_on", True)],
        [InlineKeyboardButton("── Normal message reply% ──", callback_data="noop")],
        _pct_row("solo", solo_pct),
        [InlineKeyboardButton("── User→User reply% ──", callback_data="noop")],
        _pct_row("utu", utu_pct),
        [InlineKeyboardButton("« Back", callback_data="settings_main")],
    ])

def _welcome_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [_tog_btn(chat_id, "👋 Welcome Message", "welcome_on",  True)],
        [_tog_btn(chat_id, "👋 Goodbye Message", "goodbye_on",  True)],
        [
            InlineKeyboardButton("👁 Welcome dekhein", callback_data="wel_view_welcome"),
            InlineKeyboardButton("🗑 Reset",           callback_data="wel_reset_welcome"),
        ],
        [
            InlineKeyboardButton("👁 Goodbye dekhein", callback_data="wel_view_goodbye"),
            InlineKeyboardButton("🗑 Reset",            callback_data="wel_reset_goodbye"),
        ],
        [InlineKeyboardButton("« Back", callback_data="settings_main")],
    ])

def _antispam_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    prem = is_premium(chat_id)
    rows = [
        [_tog_btn(chat_id, "🚫 Anti-Gaali",          "antigaali_on",    False, " 🆓")],
        [_tog_btn(chat_id, "👤 Anti-Username @promo", "antiusername_on", False, " 🆓")],
    ]
    if prem:
        rows += [
            [_tog_btn(chat_id, "🔗 Anti-Link (URLs)",   "antilink_on",  False, " 👑")],
            [_tog_btn(chat_id, "↩️ Anti-Forward",        "antifwd_on",   False, " 👑")],
            [_tog_btn(chat_id, "⚡ Anti-Raid",            "antiraid_on",  False, " 👑")],
            [_tog_btn(chat_id, "🧬 Bio Link Block",       "antibio_on",   False, " 👑")],
        ]
    else:
        rows.append([InlineKeyboardButton("👑 Premium unlock karo!", callback_data="prem_info")])
    rows.append([InlineKeyboardButton("« Back", callback_data="settings_main")])
    return InlineKeyboardMarkup(rows)

def _movie_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    prem = is_premium(chat_id)
    if not prem:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Premium Feature — Subscribe!", callback_data="prem_info")],
            [InlineKeyboardButton("« Back", callback_data="settings_main")],
        ])
    cap_mode  = get_setting(chat_id, "movie_caption_mode", "hard").upper()
    cap_icons = {"HARD": "🔒 HARD", "SOFT": "✏️ SOFT", "OFF": "🚫 OFF"}
    del_secs  = get_setting(chat_id, "autodel_time", 3600)
    hours     = del_secs // 3600
    mins      = (del_secs % 3600) // 60
    del_str   = f"{hours}h {mins}m" if (hours and mins) else (f"{hours}h" if hours else f"{mins}m")
    return InlineKeyboardMarkup([
        [_tog_btn(chat_id, "🎬 Movie System",       "movie_on",          True,  " 👑")],
        [_tog_btn(chat_id, "🔔 Request Tagging",    "movie_request_on",  True,  " 👑")],
        [InlineKeyboardButton(
            f"🎞 Caption: {cap_icons.get(cap_mode, cap_mode)} — tap to cycle",
            callback_data="cycle_movie_caption",
        )],
        [_tog_btn(chat_id, "⏱ Auto-Delete Files", "autodel_on",         False, " 👑")],
        [InlineKeyboardButton(
            f"🕐 Del Time: {del_str} — /autodel <sec>",
            callback_data="settings_autodel",
        )],
        [InlineKeyboardButton("« Back", callback_data="settings_main")],
    ])

def _advanced_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    prem = is_premium(chat_id)
    rows = []
    if prem:
        rows += [
            [_tog_btn(chat_id, "🌊 Flood Control",  "flood_on",   False, " 👑")],
            [_tog_btn(chat_id, "⏱ Auto-Delete",     "autodel_on", False, " 👑")],
            [_tog_btn(chat_id, "🔒 Captcha Verify", "captcha_on", False, " 👑")],
            [_tog_btn(chat_id, "✏️ Anti-Edit",       "antiedit_on", False, " 👑")],
        ]
    else:
        rows.append([InlineKeyboardButton("👑 Premium unlock karo!", callback_data="prem_info")])
    flood_limit = get_setting(chat_id, "flood_limit", 5)
    warn_limit  = get_setting(chat_id, "warn_limit",  3)
    del_secs    = get_setting(chat_id, "autodel_time", 3600)
    hours = del_secs // 3600; mins = (del_secs % 3600) // 60
    del_str = f"{hours}h {mins}m" if (hours and mins) else (f"{hours}h" if hours else f"{mins}m")
    rows += [
        [InlineKeyboardButton(f"⚡ Flood Limit: {flood_limit} msgs — /floodlimit <n>", callback_data="settings_flood")],
        [InlineKeyboardButton(f"🕐 Del Time: {del_str} — /autodel <sec>",             callback_data="settings_autodel")],
        [InlineKeyboardButton("🔒 Lock Types (sticker/gif/poll)",                     callback_data="settings_locks")],
        [InlineKeyboardButton(f"⚠️ Warn Limit: {warn_limit} warns — /warnlimit <n>",  callback_data="settings_warn")],
        [InlineKeyboardButton("« Back", callback_data="settings_main")],
    ]
    return InlineKeyboardMarkup(rows)

def _get_cat_text(cat_key: str, chat_id: int) -> str:
    """Dynamic settings text — shows current ON/OFF status."""
    def _s(key, default=False):
        val = get_setting(chat_id, key, _KEY_DEFAULTS.get(key, default))
        return "✅ ON" if val else "❌ OFF"

    if cat_key == "scat_chatbot":
        return (
            "🤖 <b>Chatbot Settings</b>\n"
            "-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
            f"• Chat Reply: <b>{_s('chat_bot_on', True)}</b>\n\n"
            "📊 <b>Reply Rate:</b>\n"
            "▸ Normal messages → <b>80%</b> reply chance\n"
            "▸ User→User tag/reply → <b>10%</b> chance (bot seekhta bhi hai)\n"
            "▸ Bulk messages → sirf <b>1 in 3</b> pe reply\n\n"
            "<i>Bot har conversation se patterns seekhta rehta hai!</i>"
        )
    elif cat_key == "scat_welcome":
        return (
            "👋 <b>Welcome / Goodbye Settings</b>\n"
            "-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
            f"• Welcome Message: <b>{_s('welcome_on', True)}</b>\n"
            f"• Goodbye Message: <b>{_s('goodbye_on', True)}</b>\n\n"
            "✏️ <b>Custom set karo:</b>\n"
            "<code>/setwelcome {name} swagat hai {group} mein!</code>\n"
            "<code>/setgoodbye {name} ne group chhoda!</code>\n\n"
            "<i>👁 View/Reset buttons se current message dekho ya hatao.</i>"
        )
    elif cat_key == "scat_antispam":
        return (
            "🛡 <b>Anti-Spam Settings</b>\n"
            "-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
            f"🆓 Anti-Gaali:          <b>{_s('antigaali_on')}</b>\n"
            f"🆓 Anti-Username @promo: <b>{_s('antiusername_on')}</b>\n"
            f"👑 Anti-Link (URLs):    <b>{_s('antilink_on')}</b>\n"
            f"👑 Anti-Forward:        <b>{_s('antifwd_on')}</b>\n"
            f"👑 Anti-Raid:           <b>{_s('antiraid_on')}</b>\n"
            f"👑 Bio Link Block:      <b>{_s('antibio_on')}</b>\n\n"
            "⚠️ <b>Gaali System:</b>\n"
            "1st → Warning  |  2nd → Mute 1h  |  3rd → Auto Ban"
        )
    elif cat_key == "scat_movie":
        cap_mode = get_setting(chat_id, "movie_caption_mode", "hard").upper()
        del_secs = get_setting(chat_id, "autodel_time", 3600)
        hours = del_secs // 3600; mins = (del_secs % 3600) // 60
        del_str = f"{hours}h {mins}m" if (hours and mins) else (f"{hours}h" if hours else f"{mins}m")
        return (
            "🎬 <b>Movie System Settings</b>\n"
            "-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
            f"• Movie System:     <b>{_s('movie_on', True)}</b>\n"
            f"• Request Tagging:  <b>{_s('movie_request_on', True)}</b>\n"
            f"• Caption Mode:     <b>{cap_mode}</b>\n"
            f"• Auto-Delete:      <b>{_s('autodel_on')}</b>\n"
            f"• Del Time:         <b>{del_str}</b>\n\n"
            "📋 <b>Caption Modes:</b>\n"
            "🔒 HARD = Obfuscated title  |  ✏️ SOFT = Clean  |  🚫 OFF = Original\n\n"
            "🔔 <b>Request Tagging ON:</b>\n"
            "Jab koi movie ka naam likhta hai → file aate hi bot tag karta hai!\n\n"
            "• Files freely FORWARD ho sakti hain ✅\n"
            "<i>Bot ko Delete Messages permission chahiye!</i>"
        )
    elif cat_key == "scat_advanced":
        flood_limit = get_setting(chat_id, "flood_limit", 5)
        warn_limit  = get_setting(chat_id, "warn_limit",  3)
        del_secs    = get_setting(chat_id, "autodel_time", 3600)
        hours = del_secs // 3600; mins = (del_secs % 3600) // 60
        del_str = f"{hours}h {mins}m" if (hours and mins) else (f"{hours}h" if hours else f"{mins}m")
        return (
            "⚡ <b>Advanced Settings</b>\n"
            "-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
            f"👑 Flood Control:    <b>{_s('flood_on')}</b>  (limit: {flood_limit} msgs)\n"
            f"👑 Auto-Delete:      <b>{_s('autodel_on')}</b>  (time: {del_str})\n"
            f"👑 Captcha Verify:   <b>{_s('captcha_on')}</b>\n"
            f"👑 Anti-Edit:        <b>{_s('antiedit_on')}</b>\n"
            f"⚠️ Warn Limit:       <b>{warn_limit} warns → ban</b>\n\n"
            "💡 <i>Niche buttons se values change karo.</i>"
        )
    return "⚙️ Settings"

# Legacy static fallback (for any code still referencing _CAT_TEXT directly)
_CAT_TEXT: dict = {}  # deprecated — use _get_cat_text()

_CAT_KBD = {
    "scat_chatbot":  _chatbot_keyboard,
    "scat_welcome":  _welcome_keyboard,
    "scat_antispam": _antispam_keyboard,
    "scat_movie":    _movie_keyboard,
    "scat_advanced": _advanced_keyboard,
}

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    msg  = update.effective_message
    if chat.type == "private":
        await msg.reply_text("Group mein use karo /settings~ 🌸")
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await msg.reply_text("❌ Sirf admins!")
        return
    prem = is_premium(chat.id)
    await msg.reply_text(
        f"⚙️ <b>Settings — {chat.title}</b>\n"
        f"{'👑 Premium Active' if prem else '🆓 Free Group'}\n\n"
        "📌 Category choose karo:",
        parse_mode="HTML",
        reply_markup=_main_settings_keyboard(chat.id),
    )

# ══════════════════════════════════════════════════════════
# TAGALL — emoji tags + stop/resume
# ══════════════════════════════════════════════════════════

async def tagall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return

    # Check if tagall already running
    existing_job = get_tagall_job(chat.id)
    if existing_job and existing_job.get("status") == "running":
        await message.reply_text(
            "⚠️ Tagall already chal raha hai!\n"
            "/stoptagall se rokh sakte ho.",
        )
        return

    custom_msg = " ".join(context.args) if context.args else "📢 Attention!"

    # Get active users from analytics (top 50)
    top_users = get_top_users(chat.id, limit=50)
    user_ids  = [u["_id"] for u in top_users]

    if not user_ids:
        await message.reply_text(
            "❌ Koi active user nahi mila!\n"
            "Group mein pehle kuch messages hone chahiye."
        )
        return

    # Send control message with Stop button
    stop_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("⏹ Stop Tagall", callback_data=f"tagall_stop_{chat.id}")
    ]])
    control_msg = await message.reply_text(
        f"📣 <b>Tagall shuru...</b>\n"
        f"💬 Message: {custom_msg[:80]}\n"
        f"👥 Users: 0/{len(user_ids)}",
        parse_mode="HTML",
        reply_markup=stop_markup,
    )

    # Store job in DB
    set_tagall_job(chat.id, custom_msg, user_ids, user.id, control_msg.message_id)

    BATCH = 8  # tags per message
    sent_count = 0

    for i in range(0, len(user_ids), BATCH):
        # Check stop flag from DB (set by Stop button in parallel request)
        if is_tagall_paused(chat.id):
            try:
                await context.bot.edit_message_text(
                    f"⏸ <b>Tagall Roka Gaya!</b>\n"
                    f"💬 {custom_msg[:80]}\n"
                    f"👥 Tagged: {sent_count}/{len(user_ids)}\n\n"
                    f"▶️ Resume karne ke liye button dabao:",
                    chat_id=chat.id,
                    message_id=control_msg.message_id,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "▶️ Resume Tagall",
                            callback_data=f"tagall_resume_{chat.id}"
                        )
                    ]]),
                )
            except Exception:
                pass
            return

        batch    = user_ids[i:i + BATCH]
        # Emoji tags — 👤 shown, user gets pinged
        tag_str  = "".join(
            f'<a href="tg://user?id={uid}">👤</a>' for uid in batch
        )

        try:
            await context.bot.send_message(
                chat.id,
                f"{tag_str}\n{custom_msg}",
                parse_mode="HTML",
            )
        except Exception as e:
            print(f"[TAGALL] send error: {e}")

        sent_count += len(batch)
        update_tagall_progress(chat.id, sent_count)

        # Update control message progress
        try:
            await context.bot.edit_message_text(
                f"📣 <b>Tagging...</b>\n"
                f"💬 {custom_msg[:80]}\n"
                f"👥 Progress: {sent_count}/{len(user_ids)}",
                chat_id=chat.id,
                message_id=control_msg.message_id,
                parse_mode="HTML",
                reply_markup=stop_markup,
            )
        except Exception:
            pass

        await asyncio.sleep(0.4)

    # Done
    clear_tagall_job(chat.id)
    try:
        await context.bot.edit_message_text(
            f"✅ <b>Tagall Complete!</b>\n"
            f"💬 {custom_msg[:80]}\n"
            f"👥 {sent_count} users tagged!",
            chat_id=chat.id,
            message_id=control_msg.message_id,
            parse_mode="HTML",
        )
    except Exception:
        pass

async def stoptagall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if not await _is_user_admin(context, chat.id, user.id):
        return
    job = get_tagall_job(chat.id)
    if not job:
        await update.effective_message.reply_text("❌ Koi tagall nahi chal raha!")
        return
    pause_tagall(chat.id)
    await update.effective_message.reply_text(
        "⏸ <b>Tagall rok diya!</b>\n"
        "Control message mein ▶️ Resume button se dubara shuru karo.",
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════════
# BAN / UNBAN
# ══════════════════════════════════════════════════════════

async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if chat.type == "private":
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko ban karna hai? Reply karo ya ID do.")
        return
    if await _is_user_admin(context, chat.id, target.id):
        await message.reply_text("❌ Admin ko ban nahi kar sakte!")
        return
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason"
    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        await message.reply_text(
            f"🔨 <b>{target.full_name}</b> banned!\n"
            f"👮 By: {user.mention_html()}\n"
            f"📝 Reason: <i>{reason}</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔓 Unban", callback_data=f"unban_{target.id}")
            ]]),
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko unban karna hai?")
        return
    try:
        await context.bot.unban_chat_member(chat.id, target.id)
        await message.reply_text(f"✅ <b>{target.full_name}</b> unbanned! 🌸", parse_mode="HTML")
    except Exception as e:
        await message.reply_text(f"❌ {e}")

# ══════════════════════════════════════════════════════════
# MUTE / UNMUTE
# ══════════════════════════════════════════════════════════

async def mute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko mute karna hai?")
        return
    if await _is_user_admin(context, chat.id, target.id):
        await message.reply_text("❌ Admin ko mute nahi kar sakte!")
        return
    # Parse duration: /mute 1h or /mute 30m or /mute 2d
    dur_str = context.args[0] if context.args else "0"
    import re as _re
    match = _re.match(r"(\d+)([mhd]?)", dur_str)
    duration_min = 0
    if match:
        n, unit = int(match.group(1)), match.group(2)
        if unit == "h":   duration_min = n * 60
        elif unit == "d": duration_min = n * 1440
        else:             duration_min = n
    until = None
    if duration_min > 0:
        until = datetime.now() + timedelta(minutes=duration_min)
    try:
        await context.bot.restrict_chat_member(
            chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        dur_text = f"{duration_min}m" if duration_min else "forever"
        await message.reply_text(
            f"🔇 <b>{target.full_name}</b> muted!\n"
            f"⏱ Duration: <b>{dur_text}</b>\n"
            f"👮 By: {user.mention_html()}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔊 Unmute", callback_data=f"unmute_{target.id}")
            ]]),
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

async def unmute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko unmute karna hai?")
        return
    try:
        await context.bot.restrict_chat_member(
            chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
            ),
        )
        await message.reply_text(f"🔊 <b>{target.full_name}</b> unmuted! 🌸", parse_mode="HTML")
    except Exception as e:
        await message.reply_text(f"❌ {e}")

# ══════════════════════════════════════════════════════════
# KICK
# ══════════════════════════════════════════════════════════

async def kick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko kick karna hai?")
        return
    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        await asyncio.sleep(0.5)
        await context.bot.unban_chat_member(chat.id, target.id)
        await message.reply_text(
            f"👟 <b>{target.full_name}</b> kicked!\n(Wapas aa sakte hain)",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

# ══════════════════════════════════════════════════════════
# WARN SYSTEM
# ══════════════════════════════════════════════════════════

async def warn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko warn karna hai?")
        return
    if await _is_user_admin(context, chat.id, target.id):
        await message.reply_text("❌ Admin ko warn nahi kar sakte!")
        return
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason"
    limit  = get_setting(chat.id, "warn_limit", 3)
    n      = add_warn(chat.id, target.id, reason, user.id)
    # ── Warn progress bar ─────────────────────────────────
    filled = "🔴" * n + "⚪" * (limit - n)
    bar    = f"{filled}  {n}/{limit}"

    if n >= limit:
        warn_text = (
            f"╔══════════════════╗\n"
            f"  🚨 <b>AUTO BAN</b>\n"
            f"╚══════════════════╝\n\n"
            f"👤 {target.mention_html()}\n"
            f"📝 Reason: <i>{reason}</i>\n"
            f"⚠️ Warns: {bar}\n\n"
            f"🔨 <b>Warn limit paar! Ban ho gaya.</b>"
        )
        await message.reply_text(warn_text, parse_mode="HTML")
        try:
            await context.bot.ban_chat_member(chat.id, target.id)
            reset_warns(chat.id, target.id)
        except Exception:
            pass
    else:
        danger = "\n🔴 <b>AGLA WARN = AUTO BAN!</b>" if n == limit - 1 else ""
        warn_text = (
            f"╔══════════════════╗\n"
            f"  ⚠️ <b>WARNING #{n}</b>\n"
            f"╚══════════════════╝\n\n"
            f"👤 {target.mention_html()}\n"
            f"📝 Reason: <i>{reason}</i>\n"
            f"⚠️ Warns: {bar}{danger}"
        )
        warn_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Dismiss",    callback_data=f"warn_dismiss_{target.id}"),
                InlineKeyboardButton("🔇 Mute 1h",   callback_data=f"warn_mute_{target.id}_3600"),
            ],
            [
                InlineKeyboardButton("⛔ Ban",        callback_data=f"warn_ban_{target.id}"),
                InlineKeyboardButton("🔄 Reset Warns",callback_data=f"resetwarn_{target.id}"),
            ],
        ])
        await message.reply_text(warn_text, parse_mode="HTML", reply_markup=warn_kb)

async def warns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    target  = await _get_target(update, context, chat.id) or update.effective_user
    n       = get_warns(chat.id, target.id)
    limit   = get_setting(chat.id, "warn_limit", 3)
    reasons = get_warn_reasons(chat.id, target.id)
    r_text  = "\n".join(
        f"  {i+1}. {r.get('reason','No reason')}"
        for i, r in enumerate(reasons)
    ) or "  None"
    bar = _warn_bar(n, limit)
    await message.reply_text(
        f"⚠️ <b>Warn Report</b>\n"
        f"-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
        f"👤 {target.mention_html()}\n"
        f"📊 {bar}\n\n"
        f"📝 <b>Reasons:</b>\n{r_text}",
        parse_mode="HTML",
    )

async def resetwarn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kiska warn reset?")
        return
    reset_warns(chat.id, target.id)
    await message.reply_text(f"✅ <b>{target.full_name}</b> ke warns reset! 🌸", parse_mode="HTML")

# ══════════════════════════════════════════════════════════
# PIN / UNPIN / DEL / PURGE
# ══════════════════════════════════════════════════════════

async def pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_user_admin(context, update.effective_chat.id, update.effective_user.id):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("❌ Koi message reply karke /pin karo!")
        return
    try:
        await update.effective_message.reply_to_message.pin()
        await update.effective_message.reply_text("📌 Pinned!")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")

async def unpin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_user_admin(context, update.effective_chat.id, update.effective_user.id):
        return
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.effective_message.reply_text("📌 Unpinned!")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ {e}")

async def del_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_user_admin(context, update.effective_chat.id, update.effective_user.id):
        return
    if update.effective_message.reply_to_message:
        try:
            await update.effective_message.reply_to_message.delete()
            await update.effective_message.delete()
        except Exception:
            pass

async def purge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, update.effective_user.id):
        return
    if not message.reply_to_message:
        await message.reply_text("❌ Pehle message reply karo!")
        return
    from_id = message.reply_to_message.message_id
    to_id   = message.message_id
    deleted = 0
    for mid in range(from_id, to_id + 1):
        try:
            await context.bot.delete_message(chat.id, mid)
            deleted += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass
    n = await context.bot.send_message(
        chat.id, f"🗑 <b>{deleted} messages delete kiye!</b>", parse_mode="HTML"
    )
    await asyncio.sleep(4)
    try:
        await n.delete()
    except Exception:
        pass

# ══════════════════════════════════════════════════════════
# PROMOTE / DEMOTE
# ══════════════════════════════════════════════════════════

async def promote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko promote?")
        return
    try:
        await context.bot.promote_chat_member(
            chat.id, target.id,
            can_delete_messages=True, can_restrict_members=True,
            can_pin_messages=True, can_manage_chat=True,
        )
        await message.reply_text(
            f"⭐ <b>{target.full_name}</b> promoted! 🎉", parse_mode="HTML"
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

async def demote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    target = await _get_target(update, context, chat.id)
    if not target:
        await message.reply_text("❌ Kisko demote?")
        return
    try:
        await context.bot.promote_chat_member(
            chat.id, target.id,
            can_delete_messages=False, can_restrict_members=False,
            can_pin_messages=False, can_manage_chat=False,
        )
        await message.reply_text(
            f"📉 <b>{target.full_name}</b> demoted!", parse_mode="HTML"
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

# ══════════════════════════════════════════════════════════
# LOCK / UNLOCK
# ══════════════════════════════════════════════════════════

_LOCK_TYPES = ["stickers", "gifs", "polls", "media", "voice"]

async def lock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not context.args:
        await message.reply_text(
            f"🔒 Lock types: <code>{' | '.join(_LOCK_TYPES)}</code>\n"
            f"Example: /lock stickers",
            parse_mode="HTML",
        )
        return
    lt = context.args[0].lower()
    if lt not in _LOCK_TYPES:
        await message.reply_text(f"❌ Valid: {', '.join(_LOCK_TYPES)}")
        return
    locked = get_setting(chat.id, "locked_types", []) or []
    if lt not in locked:
        locked.append(lt)
        set_setting(chat.id, "locked_types", locked)
    await message.reply_text(f"🔒 <b>{lt}</b> locked! 🌸", parse_mode="HTML")

async def unlock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not context.args:
        await message.reply_text("❌ Example: /unlock stickers")
        return
    lt = context.args[0].lower()
    locked = get_setting(chat.id, "locked_types", []) or []
    if lt in locked:
        locked.remove(lt)
        set_setting(chat.id, "locked_types", locked)
    await message.reply_text(f"🔓 <b>{lt}</b> unlocked! 🌸", parse_mode="HTML")

# ══════════════════════════════════════════════════════════
# WELCOME / GOODBYE / RULES
# ══════════════════════════════════════════════════════════

async def setwelcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not context.args and not (message.reply_to_message
                                  and message.reply_to_message.text):
        await message.reply_text(
            "❌ Use: /setwelcome <msg>\nVariables: {name}, {group}"
        )
        return
    text = (" ".join(context.args) if context.args
            else message.reply_to_message.text)
    set_setting(chat.id, "welcome_msg", text)
    preview = text.replace("{name}", update.effective_user.first_name).replace(
        "{group}", chat.title or "")
    await message.reply_text(
        f"✅ Welcome set!\n\nPreview:\n{preview}", parse_mode="HTML"
    )

async def setgoodbye_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not context.args:
        await message.reply_text("❌ Use: /setgoodbye <msg>  Variable: {name}")
        return
    set_setting(chat.id, "goodbye_msg", " ".join(context.args))
    await message.reply_text("✅ Goodbye set! 🌸")

async def setrules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not context.args:
        await message.reply_text("❌ Use: /setrules <text>")
        return
    set_setting(chat.id, "rules", " ".join(context.args))
    await message.reply_text("✅ Rules set! 🌸")

# ══════════════════════════════════════════════════════════
# NOTES SYSTEM
# ══════════════════════════════════════════════════════════

async def save_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if chat.type == "private":
        await message.reply_text("❌ Group mein use karo!")
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins notes save kar sakte hain!")
        return
    if not context.args:
        await message.reply_text("❌ Use: /save <name> <content>\nYa: reply karke /save <name>")
        return
    name = context.args[0].lower()
    if message.reply_to_message and message.reply_to_message.text:
        content = message.reply_to_message.text
    elif len(context.args) > 1:
        content = " ".join(context.args[1:])
    else:
        await message.reply_text("❌ Content do ya reply karo!")
        return
    save_note(chat.id, name, content, user.id)
    await message.reply_text(
        f"✅ Note <code>#{name}</code> saved!\nGet: /get {name} ya <code>#{name}</code>",
        parse_mode="HTML",
    )

async def get_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    if not context.args:
        await message.reply_text("❌ Use: /get <notename>")
        return
    note = get_note(chat.id, context.args[0].lower())
    if not note:
        await message.reply_text(
            f"❌ Note <code>#{context.args[0]}</code> nahi mila!", parse_mode="HTML"
        )
        return
    await message.reply_text(note["content"], parse_mode="HTML")

async def notes_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    notes   = get_all_notes(chat.id)
    if not notes:
        await message.reply_text("📝 Koi note nahi! /save se banao.")
        return
    lines = [f"<code>#{n['name']}</code>" for n in notes]
    await message.reply_text(
        f"📝 <b>{chat.title} Notes ({len(notes)}):</b>\n\n"
        + "\n".join(lines) +
        "\n\n<i>Koi bhi note get karne ke liye #notename type karo</i>",
        parse_mode="HTML",
    )

async def delnote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return
    if not context.args:
        await message.reply_text("❌ Use: /delnote <name>")
        return
    delete_note(chat.id, context.args[0].lower())
    await message.reply_text(
        f"🗑 Note <code>#{context.args[0]}</code> deleted! 🌸", parse_mode="HTML"
    )

# ══════════════════════════════════════════════════════════
# /WHOIS
# ══════════════════════════════════════════════════════════

async def whois_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    target  = await _get_target(update, context, chat.id) or update.effective_user
    status_map = {"creator": "👑 Owner", "administrator": "⭐ Admin",
                  "member": "👤 Member", "restricted": "🔇 Restricted",
                  "left": "🚪 Left", "kicked": "🔨 Banned"}
    try:
        mem    = await context.bot.get_chat_member(chat.id, target.id)
        status = status_map.get(mem.status, "👤 Member")
    except Exception:
        status = "❓ Unknown"
    warns     = get_warns(chat.id, target.id)
    msg_count = get_user_msg_count(chat.id, target.id)
    user_info = get_user_info(target.id)
    last_seen = user_info.get("last_seen", "Unknown") if user_info else "Unknown"
    if isinstance(last_seen, datetime):
        last_seen = last_seen.strftime("%d %b %Y %H:%M")
    await message.reply_text(
        f"👤 <b>User Info</b>\n\n"
        f"🏷 <b>Name:</b> {target.full_name}\n"
        f"🆔 <b>ID:</b> <code>{target.id}</code>\n"
        f"📛 <b>Username:</b> {'@'+target.username if target.username else 'None'}\n"
        f"🏅 <b>Status:</b> {status}\n"
        f"⚠️ <b>Warns:</b> {warns}\n"
        f"💬 <b>Messages:</b> {msg_count}\n"
        f"🕐 <b>Last Seen:</b> {last_seen}",
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════════
# /STATS / /TOPUSERS (PREMIUM)
# ══════════════════════════════════════════════════════════

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    if chat.type == "private":
        return
    if not is_premium(chat.id):
        await message.reply_text("👑 Premium feature! /premium dekho.")
        return
    stats       = get_group_stats(chat.id)
    notes_count = len(get_all_notes(chat.id))
    await message.reply_text(
        f"📊 <b>Stats — {chat.title}</b>\n\n"
        f"💬 Total Messages: <b>{stats.get('total_messages', 0):,}</b>\n"
        f"👥 Active Users: <b>{stats.get('active_users', 0)}</b>\n"
        f"📝 Notes: <b>{notes_count}</b>\n"
        f"👑 Premium: ✅\n\n"
        f"<i>Top chatters: /topusers</i>",
        parse_mode="HTML",
    )

async def topusers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    if not is_premium(chat.id):
        await message.reply_text("👑 Premium feature!")
        return
    top    = get_top_users(chat.id, limit=10)
    if not top:
        await message.reply_text("📊 Koi data nahi!")
        return
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines  = []
    for i, t in enumerate(top):
        try:
            m    = await context.bot.get_chat_member(chat.id, t["_id"])
            name = m.user.full_name
        except Exception:
            name = f"User {t['_id']}"
        lines.append(f"{medals[i]} <b>{name}</b> — {t['total']:,} msgs")
    await message.reply_text(
        f"🏆 <b>Top Chatters — {chat.title}</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════════
# /PREMIUMSTATS (Owner only)
# ══════════════════════════════════════════════════════════

async def premiumstats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        await message.reply_text("❌ Sirf bot owner!")
        return
    prem_groups  = get_all_premium_groups()
    all_groups   = get_all_groups()
    all_users    = get_all_users()
    lines = []
    for g in prem_groups:
        exp = g.get("premium_expires")
        exp_str = exp.strftime("%d %b %Y") if exp else "N/A"
        lines.append(
            f"• <b>{g.get('title', 'Unknown')}</b> "
            f"(<code>{g['chat_id']}</code>) — expires {exp_str}"
        )
    await message.reply_text(
        f"👑 <b>Premium Stats</b>\n\n"
        f"🌟 Premium Groups: <b>{len(prem_groups)}</b>\n"
        f"👥 Total Groups: <b>{len(all_groups)}</b>\n"
        f"👤 Total Users: <b>{len(all_users)}</b>\n\n"
        + ("<b>Active Premium Groups:</b>\n" + "\n".join(lines) if lines
           else "No premium groups active."),
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════════
# TEACH / FORGET / PATTERNS
# ══════════════════════════════════════════════════════════

async def teach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        await message.reply_text("❌ Sirf bot owner!")
        return
    if not context.args:
        await message.reply_text("❌ Use: /teach trigger | response")
        return
    from core.brain import teach_pattern
    ok, trigger, response = teach_pattern(" ".join(context.args), user.id)
    if ok:
        await message.reply_text(
            f"✅ <b>Seekh liya!</b>\n"
            f"📥 Trigger: <code>{trigger}</code>\n"
            f"📤 Response: {response}",
            parse_mode="HTML",
        )
    else:
        await message.reply_text("❌ Format: /teach trigger | response")

async def forget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    if not context.args:
        await message.reply_text("❌ Use: /forget <trigger>")
        return
    from core.brain import forget_pattern
    forget_pattern(" ".join(context.args))
    await message.reply_text(
        f"✅ Bhool gaya: <code>{' '.join(context.args)}</code> 🌸",
        parse_mode="HTML",
    )

async def patterns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    from core.brain import list_patterns
    patterns = list_patterns()
    if not patterns:
        await message.reply_text("📚 Koi pattern nahi!")
        return
    lines = [f"• <code>{p['trigger'][:40]}</code>" for p in patterns[:30]]
    await message.reply_text(
        f"📚 <b>Patterns ({len(patterns)}):</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════════
# BLOCK / UNBLOCK
# ══════════════════════════════════════════════════════════

async def blockuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    target = await _get_target(update, context, update.effective_chat.id)
    if not target:
        await message.reply_text("❌ Kisko block?")
        return
    block_user(target.id)
    await message.reply_text(
        f"🚫 <b>{target.full_name}</b> bot se block!", parse_mode="HTML"
    )

async def unblockuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    if not context.args:
        await message.reply_text("❌ Use: /unblockuser <id>")
        return
    try:
        uid = int(context.args[0])
        unblock_user(uid)
        await message.reply_text(
            f"✅ User <code>{uid}</code> unblocked! 🌸", parse_mode="HTML"
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

# ══════════════════════════════════════════════════════════
# SLOWMODE / FLOODLIMIT / AUTODEL / WARNLIMIT
# ══════════════════════════════════════════════════════════

async def slowmode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    secs = 0
    if context.args:
        try:
            secs = int(context.args[0])
        except ValueError:
            pass
    try:
        await context.bot.set_chat_slow_mode_delay(chat.id, secs)
        msg = "🟢 Slowmode off!" if secs == 0 else f"🐢 Slowmode: <b>{secs}s</b>"
        await message.reply_text(msg + " 🌸", parse_mode="HTML")
    except Exception as e:
        await message.reply_text(f"❌ {e}")

async def floodlimit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    try:
        limit = int(context.args[0])
        assert 2 <= limit <= 50
        set_setting(chat.id, "flood_limit", limit)
        await message.reply_text(
            f"⚡ Flood limit: <b>{limit} msgs/10s</b> 🌸", parse_mode="HTML"
        )
    except Exception:
        await message.reply_text("❌ Use: /floodlimit <2-50>")

async def autodel_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    try:
        secs = int(context.args[0])
        set_setting(chat.id, "autodel_time", secs)
        td = timedelta(seconds=secs)
        await message.reply_text(
            f"⏱ Auto-delete: <b>{secs}s ({str(td)})</b> 🌸", parse_mode="HTML"
        )
    except Exception:
        await message.reply_text("❌ Use: /autodel <seconds>  e.g. /autodel 3600")

async def warnlimit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    try:
        limit = int(context.args[0])
        set_setting(chat.id, "warn_limit", limit)
        await message.reply_text(
            f"⚠️ Warn limit: <b>{limit}</b> 🌸", parse_mode="HTML"
        )
    except Exception:
        await message.reply_text("❌ Use: /warnlimit <number>")

# ══════════════════════════════════════════════════════════
# SCHEDULED MESSAGES (PREMIUM)
# ══════════════════════════════════════════════════════════

async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not is_premium(chat.id):
        await message.reply_text("👑 Premium feature!")
        return
    if not context.args or len(context.args) < 2:
        await message.reply_text("❌ Use: /schedule HH:MM <message>\nExample: /schedule 09:00 Good morning!")
        return
    try:
        hour, minute = map(int, context.args[0].split(":"))
        assert 0 <= hour <= 23 and 0 <= minute <= 59
    except Exception:
        await message.reply_text("❌ Valid time: HH:MM (e.g. 09:30)")
        return
    text     = " ".join(context.args[1:])
    sched_id = add_scheduled(chat.id, text, hour, minute, user.id)
    await message.reply_text(
        f"⏰ <b>Scheduled!</b>\n"
        f"🕐 Every day at <b>{hour:02d}:{minute:02d}</b>\n"
        f"💬 {text[:100]}\n"
        f"🔑 ID: <code>{sched_id}</code>\n\n"
        f"Cancel: /unschedule {sched_id}",
        parse_mode="HTML",
    )

async def unschedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not await _is_user_admin(context, chat.id, user.id):
        return
    if not context.args:
        scheduled = get_scheduled(chat.id)
        if not scheduled:
            await message.reply_text("📅 Koi scheduled message nahi!")
            return
        lines = [
            f"• {s['hour']:02d}:{s['minute']:02d} — {s['text'][:40]} "
            f"(<code>{s['_id']}</code>)"
            for s in scheduled
        ]
        await message.reply_text(
            "📅 <b>Scheduled Messages:</b>\n\n" + "\n".join(lines) +
            "\n\nCancel: /unschedule <id>",
            parse_mode="HTML",
        )
        return
    ok = del_scheduled(context.args[0])
    await message.reply_text("✅ Cancel ho gaya!" if ok else "❌ ID nahi mili!")

# ══════════════════════════════════════════════════════════
# ADMINLIST / REPORT / ID
# ══════════════════════════════════════════════════════════

async def adminlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    if chat.type == "private":
        return
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        lines  = []
        for a in admins:
            if a.user.is_bot:
                continue
            icon = "👑" if a.status == "creator" else "⭐"
            lines.append(
                f'{icon} <a href="tg://user?id={a.user.id}">{a.user.full_name}</a>'
            )
        await message.reply_text(
            f"👮 <b>Admins — {chat.title}:</b>\n\n" + "\n".join(lines),
            parse_mode="HTML",
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if not message.reply_to_message:
        await message.reply_text("❌ Kisi message ko reply karke /report karo!")
        return
    reported = message.reply_to_message.from_user
    reason   = " ".join(context.args) if context.args else "No reason"
    markup   = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚠️ Warn",  callback_data=f"rep_warn_{reported.id}"),
        InlineKeyboardButton("🔇 Mute",  callback_data=f"rep_mute_{reported.id}"),
        InlineKeyboardButton("🔨 Ban",   callback_data=f"rep_ban_{reported.id}"),
    ]])
    try:
        admins = await context.bot.get_chat_administrators(chat.id)
        pings  = "".join(
            f'<a href="tg://user?id={a.user.id}">‌</a>'
            for a in admins if not a.user.is_bot
        )
    except Exception:
        pings = ""
    await message.reply_text(
        f"🚨 <b>User Reported!</b> {pings}\n\n"
        f"Reporter: {user.mention_html()}\n"
        f"Reported: {reported.mention_html()}\n"
        f"Reason: <i>{reason}</i>",
        parse_mode="HTML",
        reply_markup=markup,
    )

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message
    if message.reply_to_message:
        t = message.reply_to_message.from_user
        await message.reply_text(
            f"👤 <b>{t.full_name}</b>\n"
            f"🆔 User ID: <code>{t.id}</code>\n"
            f"👥 Chat ID: <code>{chat.id}</code>",
            parse_mode="HTML",
        )
    else:
        await message.reply_text(
            f"👤 <b>{user.full_name}</b>\n"
            f"🆔 Your ID: <code>{user.id}</code>\n"
            f"👥 Chat ID: <code>{chat.id}</code>",
            parse_mode="HTML",
        )

# ══════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════
# BROADCAST  (with dedup + progress + stop support)
# ══════════════════════════════════════════════════════════

# Module-level flag — works within one broadcast session
_BC: dict = {"running": False, "sent": 0, "failed": 0, "total": 0}

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _BC
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return

    # ── Already running? ──────────────────────────────────
    if _BC["running"]:
        await message.reply_text(
            f"⚠️ Broadcast already chal raha hai!\n"
            f"✅ {_BC['sent']} | ❌ {_BC['failed']} | Total: {_BC['total']}\n\n"
            f"/stopbroadcast se rok sakte ho.",
        )
        return

    args = list(context.args or [])
    mode = "users"
    if args and args[0] in ("-g", "-groups"):
        mode = "groups"; args = args[1:]
    elif args and args[0] in ("-all", "-a"):
        mode = "all"; args = args[1:]

    if not args and not message.reply_to_message:
        await message.reply_text(
            "❌ <b>Usage:</b>\n"
            "/broadcast msg — all users\n"
            "/broadcast -g msg — all groups\n"
            "/broadcast -all msg — users + groups\n"
            "Ya reply karke: /broadcast",
            parse_mode="HTML",
        )
        return

    bcast_msg  = message.reply_to_message
    bcast_text = " ".join(args) if args else None

    # ── Build UNIQUE target list ──────────────────────────
    targets: list[int] = []
    seen: set[int]     = set()

    if mode in ("users", "all"):
        for u in get_all_users():
            uid = u.get("user_id")
            if uid and uid not in seen:
                seen.add(uid); targets.append(uid)

    if mode in ("groups", "all"):
        for g in get_all_groups():
            gid = g.get("chat_id")
            if gid and gid not in seen:
                seen.add(gid); targets.append(gid)

    total = len(targets)
    if total == 0:
        await message.reply_text("📭 Koi target nahi mila!")
        return

    # ── Init state ────────────────────────────────────────
    _BC.update({"running": True, "sent": 0, "failed": 0, "total": total})

    notif = await message.reply_text(
        f"📢 <b>Broadcast Start!</b>\n"
        f"👥 Targets: <b>{total}</b> | Mode: <b>{mode}</b>\n\n"
        f"▱▱▱▱▱▱▱▱▱▱  0%\n"
        f"/stopbroadcast se rok sakte ho",
        parse_mode="HTML",
    )

    # ── Send loop ─────────────────────────────────────────
    async def send_one(cid: int):
        try:
            if bcast_msg:
                await context.bot.copy_message(          # copy instead of forward (no "forwarded" tag)
                    chat_id=cid,
                    from_chat_id=bcast_msg.chat_id,
                    message_id=bcast_msg.message_id,
                )
            else:
                await context.bot.send_message(
                    chat_id=cid, text=bcast_text,
                    parse_mode="HTML", disable_web_page_preview=True,
                )
            _BC["sent"] += 1
        except Exception:
            _BC["failed"] += 1
        await asyncio.sleep(0.08)   # ~12 msgs/sec — safe rate

    UPDATE_EVERY = 20   # update progress bar every N sends

    for i, cid in enumerate(targets):
        if not _BC["running"]:
            break
        await send_one(cid)

        if (i + 1) % UPDATE_EVERY == 0 or (i + 1) == total:
            pct   = int((i + 1) / total * 100)
            done  = pct // 10
            bar   = "▰" * done + "▱" * (10 - done)
            try:
                await notif.edit_text(
                    f"📢 <b>Broadcasting...</b>\n"
                    f"👥 {i+1}/{total}\n\n"
                    f"{bar}  {pct}%\n"
                    f"✅ {_BC['sent']} | ❌ {_BC['failed']}\n\n"
                    f"/stopbroadcast",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    stopped = not _BC["running"]
    _BC["running"] = False

    # ── Final report ──────────────────────────────────────
    status = "⛔ Stopped!" if stopped else "✅ Done!"
    try:
        await notif.edit_text(
            f"📢 <b>Broadcast {status}</b>\n\n"
            f"▰▰▰▰▰▰▰▰▰▰  100%\n\n"
            f"✅ Sent:   <b>{_BC['sent']}</b>\n"
            f"❌ Failed: <b>{_BC['failed']}</b>\n"
            f"👥 Total:  <b>{_BC['total']}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass


async def stopbroadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stopbroadcast — Stop ongoing broadcast."""
    global _BC
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    if not _BC["running"]:
        await message.reply_text("ℹ️ Koi broadcast chal nahi raha.")
        return
    _BC["running"] = False
    await message.reply_text(
        f"⛔ <b>Broadcast Stopped!</b>\n\n"
        f"✅ Sent:   <b>{_BC['sent']}</b>\n"
        f"❌ Failed: <b>{_BC['failed']}</b>\n"
        f"👥 Total:  <b>{_BC['total']}</b>",
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════════
# PREMIUM MANAGEMENT
# ══════════════════════════════════════════════════════════

async def addprem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    if not context.args:
        await message.reply_text("❌ Use: /addprem <group_id> [days=30]")
        return
    try:
        gid  = int(context.args[0])
        days = int(context.args[1]) if len(context.args) > 1 else 30
        grant_premium(gid, days)
        await message.reply_text(
            f"✅ Group <code>{gid}</code> — <b>{days} days Premium!</b> 👑",
            parse_mode="HTML",
        )
        try:
            await context.bot.send_message(
                gid,
                f"🎉 <b>Premium Activated!</b> 👑\n"
                f"Duration: <b>{days} days</b>\n\n"
                f"Sare premium features unlock!\n/settings se configure karo~ 🌸",
                parse_mode="HTML",
            )
        except Exception:
            pass
    except Exception as e:
        await message.reply_text(f"❌ {e}")

async def remprem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    if not context.args:
        await message.reply_text("❌ Use: /remprem <group_id>")
        return
    try:
        gid = int(context.args[0])
        revoke_premium(gid)
        await message.reply_text(
            f"✅ Premium revoked from <code>{gid}</code>!", parse_mode="HTML"
        )
    except Exception as e:
        await message.reply_text(f"❌ {e}")

# ══════════════════════════════════════════════════════════
# PREMIUM SUBSCRIPTION FLOW (PM)
# ══════════════════════════════════════════════════════════

async def prem_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if prem_state_exists(user.id):
        await message.reply_text("⏳ Request already chal rahi hai! /cancel se cancel karo.")
        return
    prem_state_set(user.id, "group_id", {})
    await message.reply_text(
        f"💳 <b>Premium — Step 1/3</b>\n\n"
        f"Kaun se group ke liye premium chahiye?\n"
        f"Us group ka <b>ID</b> bhejo.\n\n"
        f"Group ID kaise pata kare:\n"
        f"➡️ Bot ko group mein add karo → /id chalao\n\n"
        f"Format: <code>-1001234567890</code>\n\n"
        f"<i>/cancel — cancel karo</i>",
        parse_mode="HTML",
    )

async def pm_premium_conversation(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id    = update.effective_user.id
    state      = prem_state_get(user_id)
    if state is None:
        return False
    message    = update.effective_message
    step       = state["step"]
    state_data = state["data"]

    if step == "group_id":
        text = (message.text or "").strip()
        if not (text.startswith("-100") and text[4:].isdigit()):
            await message.reply_text(
                "❌ Valid group ID chahiye!\nExample: <code>-1009876543210</code>\n\n"
                "<i>/cancel — cancel karo</i>",
                parse_mode="HTML",
            )
            return True
        state_data["group_id"] = int(text)
        prem_state_set(user_id, "utr", state_data)
        await message.reply_text(
            f"✅ Group noted!\n\n💳 <b>Step 2/3 — Payment</b>\n\n"
            f"₹{PREMIUM_PRICE} send karo UPI pe:\n<code>asbhai@paytm</code>\n\n"
            f"Payment ke baad <b>UTR/Transaction ID</b> bhejo.\n"
            f"Example: <code>T2024123456789</code>\n\n<i>/cancel — cancel karo</i>",
            parse_mode="HTML",
        )
        return True

    elif step == "utr":
        utr = (message.text or "").strip()
        if len(utr) < 4:
            await message.reply_text("❌ Valid UTR bhejo!")
            return True
        state_data["utr"] = utr
        prem_state_set(user_id, "screenshot", state_data)
        await message.reply_text(
            "✅ UTR noted!\n\n📸 <b>Step 3/3 — Screenshot</b>\n\n"
            "Payment ka <b>screenshot</b> bhejo — directly photo ke roop mein 📷\n\n"
            "<i>/cancel — cancel karo</i>",
            parse_mode="HTML",
        )
        return True

    elif step == "screenshot":
        if not message.photo and not message.document:
            await message.reply_text(
                "❌ Screenshot chahiye!\nDirect <b>photo</b> bhejo gallery se 📸\n\n"
                "<i>/cancel — cancel karo</i>",
                parse_mode="HTML",
            )
            return True
        data       = state_data
        screenshot = (message.photo[-1].file_id if message.photo
                      else message.document.file_id)
        data["screenshot"] = screenshot
        save_prem_request(user_id, data["group_id"], data["utr"], screenshot)
        markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve",
                callback_data=f"prem_a_{user_id}_{data['group_id']}"),
            InlineKeyboardButton("❌ Reject",
                callback_data=f"prem_r_{user_id}"),
        ]])
        try:
            await context.bot.send_photo(
                ADMIN_ID, photo=screenshot,
                caption=(
                    f"💳 <b>New Premium Request</b>\n\n"
                    f"👤 {update.effective_user.full_name}\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"👥 Group: <code>{data['group_id']}</code>\n"
                    f"💰 UTR: <code>{data['utr']}</code>\n"
                    f"💵 Amount: ₹{PREMIUM_PRICE}"
                ),
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception as e:
            prem_state_del(user_id)
            await message.reply_text(
                f"❌ Owner tak nahi pauhncha: {e}\n"
                f"Directly contact: {OWNER_USERNAME}"
            )
            return True
        prem_state_del(user_id)
        await message.reply_text(
            "✅ <b>Request Submit Ho Gayi!</b>\n\n"
            "Owner jaldi verify karega.\n"
            f"Direct baat: {OWNER_USERNAME}\n\n"
            "Verification ke baad group mein message aayega! 🎉",
            parse_mode="HTML",
        )
        return True
    return False

async def cancel_premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if prem_state_exists(uid):
        prem_state_del(uid)
        await update.message.reply_text("❌ Cancel ho gaya! /premium se dubara shuru karo.")
    else:
        await update.message.reply_text("Koi active process nahi. 🌸")

# ══════════════════════════════════════════════════════════
# MASTER CALLBACK HANDLER
# ══════════════════════════════════════════════════════════

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    data    = query.data
    user    = query.from_user
    chat    = query.message.chat

    await query.answer()

    # ── Tagall Stop ──────────────────────────────────────
    if data.startswith("tagall_stop_"):
        cid = int(data.split("_")[2])
        if not await _is_user_admin(context, cid, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        pause_tagall(cid)
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "▶️ Resume Tagall",
                        callback_data=f"tagall_resume_{cid}"
                    )
                ]])
            )
        except Exception:
            pass
        return

    # ── Tagall Resume ────────────────────────────────────
    if data.startswith("tagall_resume_"):
        cid = int(data.split("_")[2])
        if not await _is_user_admin(context, cid, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        job = get_tagall_job(cid)
        if not job:
            await query.answer("Koi tagall job nahi mili!", show_alert=True)
            return
        resume_tagall(cid)
        # Continue from where we stopped
        all_uids   = job["user_ids"]
        start_idx  = job.get("current_index", 0)
        custom_msg = job.get("message_text", "📢 Attention!")
        stop_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏹ Stop Tagall", callback_data=f"tagall_stop_{cid}")
        ]])
        try:
            await query.edit_message_text(
                f"📣 <b>Resuming tagall...</b>\n"
                f"💬 {custom_msg[:80]}\n"
                f"👥 {start_idx}/{len(all_uids)} done",
                parse_mode="HTML",
                reply_markup=stop_markup,
            )
        except Exception:
            pass
        BATCH = 8
        sent_count = start_idx
        for i in range(start_idx, len(all_uids), BATCH):
            if is_tagall_paused(cid):
                try:
                    await context.bot.edit_message_reply_markup(
                        chat_id=cid,
                        message_id=query.message.message_id,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "▶️ Resume Tagall",
                                callback_data=f"tagall_resume_{cid}"
                            )
                        ]]),
                    )
                except Exception:
                    pass
                return
            batch   = all_uids[i:i + BATCH]
            tag_str = "".join(
                f'<a href="tg://user?id={uid}">👤</a>' for uid in batch
            )
            try:
                await context.bot.send_message(
                    cid, f"{tag_str}\n{custom_msg}", parse_mode="HTML"
                )
            except Exception:
                pass
            sent_count += len(batch)
            update_tagall_progress(cid, sent_count)
            await asyncio.sleep(0.4)
        clear_tagall_job(cid)
        try:
            await context.bot.edit_message_text(
                f"✅ <b>Tagall Complete!</b>\n👥 {sent_count} users tagged!",
                chat_id=cid,
                message_id=query.message.message_id,
                parse_mode="HTML",
            )
        except Exception:
            pass
        return

    # ── Unban ────────────────────────────────────────────
    if data.startswith("unban_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        uid = int(data.split("_")[1])
        try:
            await context.bot.unban_chat_member(chat.id, uid)
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(
                f"✅ User <code>{uid}</code> unbanned! 🌸", parse_mode="HTML"
            )
        except Exception as e:
            await query.answer(str(e), show_alert=True)

    # ── Unmute ───────────────────────────────────────────
    elif data.startswith("unmute_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        uid = int(data.split("_")[1])
        try:
            await context.bot.restrict_chat_member(
                chat.id, uid,
                permissions=ChatPermissions(
                    can_send_messages=True, can_send_media_messages=True,
                    can_send_other_messages=True, can_add_web_page_previews=True,
                ),
            )
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception as e:
            await query.answer(str(e), show_alert=True)

    # ── Reset warn ───────────────────────────────────────
    elif data.startswith("resetwarn_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        uid = int(data.split("_")[1])
        reset_warns(chat.id, uid)
        await query.answer("✅ Warns reset!")
        await query.edit_message_reply_markup(reply_markup=None)

    # ── Warn action: Dismiss ──────────────────────────────
    elif data.startswith("warn_dismiss_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        await query.answer("✅ Warning dismissed!")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

    # ── Warn action: Mute ────────────────────────────────
    elif data.startswith("warn_mute_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        parts    = data.split("_")
        target_id = int(parts[2])
        dur_secs  = int(parts[3]) if len(parts) > 3 else 3600
        try:
            from datetime import timedelta
            until = datetime.now() + timedelta(seconds=dur_secs)
            await context.bot.restrict_chat_member(
                chat.id, target_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            hrs = dur_secs // 3600
            await query.answer(f"🔇 Muted for {hrs}h!")
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Unmute", callback_data=f"unmute_{target_id}"),
            ]]))
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)

    # ── Warn action: Ban ─────────────────────────────────
    elif data.startswith("warn_ban_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        target_id = int(data.split("_")[2])
        try:
            await context.bot.ban_chat_member(chat.id, target_id)
            await query.answer("⛔ Banned!")
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔓 Unban", callback_data=f"unban_{target_id}"),
            ]]))
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)

    # ── Premium Approve ──────────────────────────────────
    elif data.startswith("prem_a_"):
        if user.id != ADMIN_ID:
            await query.answer("❌ Sirf bot owner!", show_alert=True)
            return
        parts  = data.split("_")
        req_uid, grp_id = int(parts[2]), int(parts[3])
        grant_premium(grp_id, 30)
        try:
            await query.edit_message_caption(
                caption=(query.message.caption or "") + "\n\n✅ <b>APPROVED</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        try:
            await context.bot.send_message(
                req_uid,
                f"🎉 <b>Premium Approved!</b> 👑\n"
                f"Group <code>{grp_id}</code> — 30 days premium!\n"
                f"/settings se configure karo~ 🌸",
                parse_mode="HTML",
            )
            await context.bot.send_message(
                grp_id,
                "🎉 <b>Premium Activated!</b> 👑\n"
                "Sare premium features unlock!\n/settings se configure karo~ 🌸",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # ── Premium Reject ───────────────────────────────────
    elif data.startswith("prem_r_"):
        if user.id != ADMIN_ID:
            await query.answer("❌ Sirf bot owner!", show_alert=True)
            return
        req_uid = int(data.split("_")[2])
        try:
            await query.edit_message_caption(
                caption=(query.message.caption or "") + "\n\n❌ <b>REJECTED</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        try:
            await context.bot.send_message(
                req_uid,
                f"❌ <b>Premium Rejected!</b>\n\n"
                f"Payment verify nahi ho saki.\n"
                f"Help: {OWNER_USERNAME}",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # ── Category Settings sub-panels ─────────────────────
    if data in _CAT_KBD:
        kbd_fn = _CAT_KBD[data]
        cat_text = _get_cat_text(data, chat.id)
        try:
            await query.edit_message_text(
                cat_text, parse_mode="HTML",
                reply_markup=kbd_fn(chat.id),
            )
        except Exception:
            await query.message.reply_text(
                cat_text, parse_mode="HTML",
                reply_markup=kbd_fn(chat.id),
            )
        return

    # ── Toggle settings (with fancy loading animation) ──────
    if data.startswith("tog_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        key   = data[4:]
        label = key.replace("_on","").replace("_"," ").strip().title()

        await query.answer()
        # Step 1 — loading start
        try:
            await query.edit_message_text(
                f"⚙️ <b>Updating: {label}</b>\n\n"
                f"⋘ 𝑙𝑜𝑎𝑑𝑖𝑛𝑔 𝑑𝑎𝑡𝑎... ⋙\n{_progress_bar(10)}",
                parse_mode="HTML",
            )
        except Exception:
            pass

        import asyncio as _aio
        await _aio.sleep(0.25)

        # Step 2 — applying
        try:
            await query.edit_message_text(
                f"⚙️ <b>Updating: {label}</b>\n\n"
                f"⋘ 𝑠𝑎𝑣𝑖𝑛𝑔... ⋙\n{_progress_bar(80)}",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await _aio.sleep(0.2)

        # Step 3 — Do the actual toggle
        default = _KEY_DEFAULTS.get(key, False)
        new_val = toggle_setting(chat.id, key, default)
        icon    = "✅" if new_val else "❌"

        # Step 4 — Done confirmation
        try:
            await query.edit_message_text(
                f"✅ <b>Setting Updated!</b>\n"
                f"-ˋˏ✄┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
                f"{icon} <b>{label}</b> — {'ON ✅' if new_val else 'OFF ❌'}\n\n"
                f"{_progress_bar(100)}\n\n"
                f"<i>✔ Setting save ho gayi!</i>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await _aio.sleep(0.6)

        # Step 5 — Restore category panel
        cat = "scat_chatbot"
        if "welcome" in key or "goodbye" in key:       cat = "scat_welcome"
        elif "anti" in key or "bio" in key:             cat = "scat_antispam"
        elif "movie" in key or "caption" in key or "request" in key: cat = "scat_movie"
        elif any(k in key for k in ["flood","autodel","captcha","edit","lock","warn"]): cat = "scat_advanced"
        try:
            await query.edit_message_text(
                _get_cat_text(cat, chat.id),
                parse_mode="HTML",
                reply_markup=_CAT_KBD[cat](chat.id),
            )
        except Exception:
            pass
        return

    # ── Cycle movie caption mode ─────────────────────────
    elif data == "cycle_movie_caption":
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        modes    = ["off", "soft", "hard"]
        current  = get_setting(chat.id, "movie_caption_mode", "hard")
        idx      = modes.index(current) if current in modes else 2
        new_mode = modes[(idx + 1) % len(modes)]
        set_setting(chat.id, "movie_caption_mode", new_mode)
        await query.answer(f"🎬 Caption mode: {new_mode.upper()} ✅")
        try:
            await query.edit_message_text(
                _get_cat_text("scat_movie", chat.id),
                parse_mode="HTML",
                reply_markup=_movie_keyboard(chat.id),
            )
        except Exception:
            pass

    # ── Welcome / Goodbye — View & Reset ─────────────────
    elif data in ("wel_view_welcome", "wel_view_goodbye"):
        which   = "welcome" if "welcome" in data else "goodbye"
        key_msg = f"{which}_msg"
        default = (
            "👋 {name} ne group join kiya! 🎉\n<b>{group}</b> mein swagat hai!"
            if which == "welcome" else
            "👋 {name} ne group chhoda. Alvida! 👋"
        )
        msg = get_setting(chat.id, key_msg, default) or default
        await query.answer()
        try:
            await query.message.reply_text(
                f"📄 <b>Current {which.title()} Message:</b>\n\n{msg}\n\n"
                f"<i>Change karne ke liye: /{which.replace('goodbye','setgoodbye').replace('welcome','setwelcome')} &lt;text&gt;</i>",
                parse_mode="HTML",
            )
        except Exception:
            pass

    elif data in ("wel_reset_welcome", "wel_reset_goodbye"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        which = "welcome" if "welcome" in data else "goodbye"
        set_setting(chat.id, f"{which}_msg", None)
        await query.answer(f"✅ {which.title()} message reset — default chal raha hai!")
        try:
            await query.edit_message_text(
                _get_cat_text("scat_welcome", chat.id),
                parse_mode="HTML",
                reply_markup=_welcome_keyboard(chat.id),
            )
        except Exception:
            pass

    # ── Settings sub-menus (inline popup) ───────────────────
    elif data == "settings_flood":
        fl = get_setting(chat.id, "flood_limit", 5)
        await query.answer(
            f"⚡ Flood Limit: {fl} msgs/10s\nChange: /floodlimit <number>",
            show_alert=True,
        )
    elif data == "settings_autodel":
        ds = get_setting(chat.id, "autodel_time", 3600)
        h  = ds // 3600; m = (ds % 3600) // 60
        ts = f"{h}h {m}m" if (h and m) else (f"{h}h" if h else f"{m}m")
        await query.answer(
            f"⏱ Auto-Delete Time: {ts}\nChange: /autodel <seconds>\nExample: /autodel 3600",
            show_alert=True,
        )
    elif data == "settings_warn":
        wl = get_setting(chat.id, "warn_limit", 3)
        await query.answer(
            f"⚠️ Warn Limit: {wl} warns → ban\nChange: /warnlimit <number>",
            show_alert=True,
        )
    elif data == "settings_locks":
        locked = get_setting(chat.id, "locked_types", []) or []
        lock_rows = [
            ["stickers", "gifs"],
            ["polls", "media"],
            ["voice"],
        ]
        kbd_rows = [
            [InlineKeyboardButton(
                f"{'🔒' if t in locked else '🔓'} {t.title()}",
                callback_data=f"locktype_{t}"
            ) for t in row]
            for row in lock_rows
        ] + [[InlineKeyboardButton("« Back", callback_data="settings_main")]]
        try:
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(kbd_rows)
            )
        except Exception:
            pass

    elif data.startswith("locktype_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        lt     = data[9:]
        locked = get_setting(chat.id, "locked_types", []) or []
        if lt in locked:
            locked.remove(lt)
            await query.answer(f"🔓 {lt} unlocked!")
        else:
            locked.append(lt)
            await query.answer(f"🔒 {lt} locked!")
        set_setting(chat.id, "locked_types", locked)

    # ── noop — label buttons do nothing ─────────────────────
    elif data == "noop":
        await query.answer()

    # ── set_pct_KEY_VALUE — chatbot reply % ─────────────────
    elif data.startswith("set_pct_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        parts = data.split("_")   # set pct KEY VAL
        pct_key = parts[2]; pct_val = int(parts[3])
        setting_key = "chat_solo_pct" if pct_key == "solo" else "chat_utu_pct"
        label       = "Normal msg" if pct_key == "solo" else "User→User msg"
        set_setting(chat.id, setting_key, pct_val)
        await query.answer(f"✅ {label}: {pct_val}%")
        try:
            await query.edit_message_text(
                _get_cat_text("scat_chatbot", chat.id),
                parse_mode="HTML",
                reply_markup=_chatbot_keyboard(chat.id),
            )
        except Exception:
            pass

    elif data == "settings_main":
        prem = is_premium(chat.id)
        status = "👑 Premium Active" if prem else "🆓 Free — /premium se upgrade karo"
        try:
            await query.edit_message_text(
                f"⚙️ <b>Settings — {chat.title}</b>\n"
                f"<i>{status}</i>\n\n"
                "📌 Category choose karo:",
                parse_mode="HTML",
                reply_markup=_main_settings_keyboard(chat.id),
            )
        except Exception:
            pass

    # ── Automod Dismiss (any admin can dismiss warning msgs) ────
    elif data == "automod_dismiss":
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins dismiss kar sakte hain!", show_alert=True)
            return
        await query.answer("✅ Dismissed!")
        try:
            await query.message.delete()
        except Exception:
            pass

    # ── Bio Free prompt from warning message ──────────────
    elif data.startswith("biofree_prompt_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        target_uid = int(data.split("_")[2])
        from core.db import grant_bio_perm
        grant_bio_perm(chat.id, target_uid)
        await query.answer(f"✅ Bio permission dedi!")
        try:
            await query.edit_message_text(
                f"✅ User <code>{target_uid}</code> ko bio permission mil gayi!\n"
                f"Ab wo group mein freely message kar sakta/sakti hai. 🌸",
                parse_mode="HTML",
            )
        except Exception:
            pass

    # ── Close ────────────────────────────────────────────
    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            pass

    # ── Report actions ───────────────────────────────────
    elif data.startswith("rep_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        parts  = data.split("_")
        action = parts[1]
        uid    = int(parts[2])
        if action == "warn":
            add_warn(chat.id, uid, "Reported", user.id)
            await query.answer("⚠️ Warned!")
        elif action == "mute":
            try:
                await context.bot.restrict_chat_member(
                    chat.id, uid,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(hours=1),
                )
                await query.answer("🔇 Muted 1hr!")
            except Exception as e:
                await query.answer(str(e), show_alert=True)
        elif action == "ban":
            try:
                await context.bot.ban_chat_member(chat.id, uid)
                await query.answer("🔨 Banned!")
            except Exception as e:
                await query.answer(str(e), show_alert=True)

    # ── Premium info ─────────────────────────────────────
    elif data in ("prem_info", "prem_start"):
        me = await context.bot.get_me()
        await query.message.reply_text(
            f"👑 <b>Premium Features</b>\n\n"
            f"💰 Price: ₹{PREMIUM_PRICE}/month\n\n"
            f"🔗 Anti-Link (ALL URLs)\n"
            f"↪️ Anti-Forward\n"
            f"👤 Anti-Username Promo\n"
            f"🛡 Anti-Raid (auto lock)\n"
            f"🎬 Movie File System (soft/hard caption)\n"
            f"🤖 Button Captcha\n"
            f"📊 Group Analytics\n"
            f"⏰ Scheduled Messages\n"
            f"🗑 Auto-Delete + Roast Warning\n"
            f"⚡ Flood Control\n\n"
            f"Free features:\n"
            f"🤬 Anti-Gaali (200+ words)\n"
            f"👤 Anti-Username (@) promo\n"
            f"📝 Notes System\n"
            f"🤖 Smart AI Chatbot\n\n"
            f"PM {OWNER_USERNAME} to subscribe!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💳 Subscribe",
                    url=f"https://t.me/{me.username}?start=premium"
                )],
                [InlineKeyboardButton(
                    "📢 Updates",
                    url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}"
                )],
            ]),
        )


# ════════════════════════════════════════════════════════════
# /string — Check userbot string session status
# ════════════════════════════════════════════════════════════

async def string_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/string — Show if Pyrogram string session is active."""
    user    = update.effective_user
    message = update.effective_message

    # Owner-only
    if user.id != ADMIN_ID:
        await message.reply_text("❌ Sirf bot owner ke liye!")
        return

    wait_msg = await message.reply_text("🔍 Session check kar raha hoon...")

    from core.userbot import check_session
    info = await check_session()

    if info.get("active"):
        text = (
            f"✅ <b>String Session ACTIVE!</b>\n\n"
            f"👤 Account: <b>{info['name']}</b>\n"
            f"📱 Phone: <code>{info['phone']}</code>\n"
            f"👥 Groups: <b>{info['groups']}</b> groups mein joined\n\n"
            f"<i>Bot is in groups se conversations search karke reply dega!</i>"
        )
    else:
        reason = info.get("reason", "Unknown error")
        text = (
            f"❌ <b>String Session INACTIVE</b>\n\n"
            f"❗ Reason: <code>{reason}</code>\n\n"
            f"<b>Setup karne ke liye:</b>\n"
            f"1. my.telegram.org → API_ID aur API_HASH lo\n"
            f"2. Pyrogram string session generate karo\n"
            f"3. Vercel mein env set karo:\n"
            f"   • <code>API_ID</code>\n"
            f"   • <code>API_HASH</code>\n"
            f"   • <code>USERBOT_SESSION</code>"
        )

    await wait_msg.edit_text(text, parse_mode="HTML")


# ════════════════════════════════════════════════════════════
# /sticker — Save stickers for bot to use in replies
# ════════════════════════════════════════════════════════════

async def sticker_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sticker — Enter sticker-save mode."""
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        await message.reply_text("Group mein use karo!")
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return

    # Set pending flag in DB
    set_setting(chat.id, "sticker_pending", True)

    stickers = get_stickers(chat.id)
    saved    = len(stickers)

    await message.reply_text(
        f"🎭 <b>Sticker Save Mode ON!</b>\n\n"
        f"Ab koi bhi sticker bhejo → bot save kar lega.\n"
        f"Bot replies mein 20% chance se yahi sticker aayega!\n\n"
        f"📦 Already saved: <b>{saved}</b> stickers\n\n"
        f"<i>✅ Sticker bhejo | /stickerdone — finish</i>",
        parse_mode="HTML",
    )


async def sticker_done_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stickerdone — Exit sticker-save mode."""
    chat    = update.effective_chat
    message = update.effective_message

    if chat.type == "private":
        return
    set_setting(chat.id, "sticker_pending", False)
    stickers = get_stickers(chat.id)
    await message.reply_text(
        f"✅ Sticker mode OFF!\n"
        f"📦 Total saved: <b>{len(stickers)}</b> stickers",
        parse_mode="HTML",
    )


async def sticker_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stickers — Show sticker count."""
    chat    = update.effective_chat
    message = update.effective_message

    if chat.type == "private":
        return
    stickers = get_stickers(chat.id)
    if not stickers:
        await message.reply_text(
            "📭 Koi sticker save nahi!\n/sticker se save karo."
        )
        return
    await message.reply_text(
        f"🎭 <b>Saved Stickers: {len(stickers)}</b>\n\n"
        f"Bot replies mein randomly inhe use karta hai.\n"
        f"/stickerclear — sab delete karo",
        parse_mode="HTML",
    )


async def sticker_clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stickerclear — Delete all saved stickers."""
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return

    clear_stickers(chat.id)
    await message.reply_text("✅ Sab stickers delete kar diye! 🗑")

# ══════════════════════════════════════════════════════════
# /SETCOMMANDS — Set bot commands list via API
# ══════════════════════════════════════════════════════════

async def setcommands_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        await message.reply_text("❌ Sirf bot owner!")
        return

    from telegram import BotCommand, BotCommandScopeAllChatAdministrators, BotCommandScopeDefault

    user_cmds = [
        BotCommand("start",    "Bot start karo 🚀"),
        BotCommand("help",     "Commands list 📖"),
        BotCommand("rules",    "Group rules 📋"),
        BotCommand("premium",  "Premium info 👑"),
        BotCommand("id",       "User/Chat ID 🆔"),
        BotCommand("whois",    "User info 👤"),
        BotCommand("get",      "Note get karo 📝"),
        BotCommand("notes",    "Notes list 📝"),
        BotCommand("report",   "User report karo 🚨"),
    ]
    admin_cmds = user_cmds + [
        BotCommand("settings",    "Group settings ⚙️"),
        BotCommand("ban",         "User ban 🔨"),
        BotCommand("unban",       "User unban 🔓"),
        BotCommand("mute",        "User mute 🔇"),
        BotCommand("unmute",      "User unmute 🔊"),
        BotCommand("kick",        "User kick 👟"),
        BotCommand("warn",        "User warn ⚠️"),
        BotCommand("warns",       "Warns dekhna 📊"),
        BotCommand("resetwarn",   "Warns reset ♻️"),
        BotCommand("pin",         "Message pin 📌"),
        BotCommand("del",         "Message delete 🗑"),
        BotCommand("purge",       "Bulk delete 🗑"),
        BotCommand("promote",     "Admin banao ⭐"),
        BotCommand("demote",      "Admin hatao 📉"),
        BotCommand("tagall",      "Sab tag karo 📢"),
        BotCommand("lock",        "Content lock 🔒"),
        BotCommand("unlock",      "Content unlock 🔓"),
        BotCommand("filter",      "Filter add karo 🔍"),
        BotCommand("filters",     "Filters list 🔍"),
        BotCommand("save",        "Note save karo 💾"),
        BotCommand("delnote",     "Note delete 🗑"),
        BotCommand("setwelcome",  "Welcome set 👋"),
        BotCommand("setgoodbye",  "Goodbye set 👋"),
        BotCommand("setrules",    "Rules set 📋"),
        BotCommand("schedule",    "Message schedule ⏰"),
        BotCommand("slowmode",    "Slowmode set 🐢"),
        BotCommand("floodlimit",  "Flood limit set ⚡"),
        BotCommand("autodel",     "Auto-del time ⏱"),
        BotCommand("warnlimit",   "Warn limit set ⚠️"),
        BotCommand("biofree",     "Bio permission do 🧬"),
        BotCommand("stats",       "Group stats 📊"),
        BotCommand("topusers",    "Top users 🏆"),
        BotCommand("adminlist",   "Admins list 👮"),
        BotCommand("sticker",     "Sticker mode 🎭"),
        BotCommand("stickerdone", "Sticker mode off ✅"),
        BotCommand("stickerclear","Stickers clear 🗑"),
        BotCommand("setcommands", "Commands set karo ⚙️"),
    ]

    wait = await message.reply_text("⚙️ <b>Setting commands...</b>", parse_mode="HTML")
    try:
        await context.bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())
        await context.bot.set_my_commands(admin_cmds, scope=BotCommandScopeAllChatAdministrators())
        await wait.edit_text(
            f"✅ <b>Commands Set!</b>\n\n"
            f"👤 Regular users: {len(user_cmds)} commands\n"
            f"👮 Group admins: {len(admin_cmds)} commands\n\n"
            f"<i>Refresh Telegram to see updated commands!</i>",
            parse_mode="HTML",
        )
    except Exception as e:
        await wait.edit_text(f"❌ Error: {e}")


# ══════════════════════════════════════════════════════════
# /BIOFREE — Give user bio link permission
# ══════════════════════════════════════════════════════════

async def biofree_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    user    = update.effective_user
    message = update.effective_message

    if chat.type == "private":
        await message.reply_text("❌ Group mein use karo!")
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await message.reply_text("❌ Sirf admins!")
        return
    if not context.args:
        await message.reply_text(
            "❌ Use: /biofree <user_id>\n"
            "Example: /biofree 123456789\n"
            "Ya kisi message ko reply karke /biofree karo"
        )
        return

    target = await _get_target(update, context, chat.id)
    if not target:
        try:
            uid = int(context.args[0])
            target_obj = type("U", (), {"id": uid, "full_name": str(uid), "mention_html": lambda: f"<code>{uid}</code>"})()
        except Exception:
            await message.reply_text("
