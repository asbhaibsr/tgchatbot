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
)

ADMIN_ID       = int(os.environ.get("ADMIN_ID", "0"))
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"
PREMIUM_PRICE  = int(os.environ.get("PREMIUM_PRICE", "99"))
BOT_NAME       = "ᴀꜱ ɢʀᴏᴜᴘ ʙᴏᴛ"

# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

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

def _settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    def btn(label, key, default=False):
        val  = get_setting(chat_id, key, default)
        icon = "✅" if val else "❌"
        return InlineKeyboardButton(f"{icon} {label}", callback_data=f"tog_{key}")

    cap_mode = get_setting(chat_id, "movie_caption_mode", "hard").upper()
    prem = is_premium(chat_id)

    rows = [
        [btn("Chatbot",       "chat_bot_on",    True),
         btn("Welcome",       "welcome_on",     True)],
        [btn("Goodbye",       "goodbye_on",     True),
         btn("Anti-Gaali 🆓", "antigaali_on",   False)],
        [btn("Anti-Username 🆓","antiusername_on", False),
         btn("Anti-Link 👑",  "antilink_on",    False)],
    ]
    if prem:
        rows += [
            [btn("Anti-Fwd 👑",   "antifwd_on",    False),
             btn("Anti-Raid 👑",  "antiraid_on",   False)],
            [btn("Flood 👑",      "flood_on",      False),
             btn("Auto-Del 👑",   "autodel_on",    False)],
            [btn("Captcha 👑",    "captcha_on",    False),
             btn("Movie Sys 👑",  "movie_on",      True)],
            [InlineKeyboardButton(
                f"🎬 Caption Mode: {cap_mode} 👑",
                callback_data="cycle_movie_caption"
            )],
        ]
    else:
        rows.append([InlineKeyboardButton(
            "👑 Unlock Premium Features", callback_data="prem_info"
        )])
    rows += [
        [InlineKeyboardButton("⚡ Flood Limit",  callback_data="settings_flood"),
         InlineKeyboardButton("⏱ Auto-Del Time", callback_data="settings_autodel")],
        [InlineKeyboardButton("🔒 Lock Types",    callback_data="settings_locks"),
         InlineKeyboardButton("⚠️ Warn Limit",    callback_data="settings_warn")],
        [InlineKeyboardButton("❌ Close",          callback_data="close")],
    ]
    return InlineKeyboardMarkup(rows)

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        await update.message.reply_text("Group mein use karo /settings~ 🌸")
        return
    if not await _is_user_admin(context, chat.id, user.id):
        await update.message.reply_text("❌ Sirf admins!")
        return
    prem = is_premium(chat.id)
    await update.message.reply_text(
        f"⚙️ <b>Settings — {chat.title}</b>\n\n"
        f"{'👑 Premium Group' if prem else '🆓 Free Group'}\n\n"
        "Features toggle karo:",
        parse_mode="HTML",
        reply_markup=_settings_keyboard(chat.id),
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
    if n >= limit:
        await message.reply_text(
            f"⚠️ {target.mention_html()} — <b>Warning {n}/{limit}</b>\n"
            f"📝 {reason}\n\n🔨 <b>Limit reached — Banning!</b>",
            parse_mode="HTML",
        )
        try:
            await context.bot.ban_chat_member(chat.id, target.id)
            reset_warns(chat.id, target.id)
        except Exception:
            pass
    else:
        await message.reply_text(
            f"⚠️ {target.mention_html()} — <b>Warning {n}/{limit}</b>\n"
            f"📝 Reason: <i>{reason}</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Reset", callback_data=f"resetwarn_{target.id}")
            ]]),
        )

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
    await message.reply_text(
        f"⚠️ <b>{target.full_name}</b> — Warns: <b>{n}/{limit}</b>\n\n"
        f"Reasons:\n{r_text}",
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
# BROADCAST
# ══════════════════════════════════════════════════════════

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    message = update.effective_message
    if not _is_owner(user.id):
        return
    args = list(context.args or [])
    mode = "users"
    if args and args[0] in ("-g", "-groups"):
        mode = "groups"; args = args[1:]
    elif args and args[0] in ("-all", "-a"):
        mode = "all"; args = args[1:]
    if not args and not message.reply_to_message:
        await message.reply_text(
            "❌ Use:\n/broadcast <msg> — all users\n"
            "/broadcast -g <msg> — all groups\n"
            "/broadcast -all <msg> — both\n"
            "Ya kisi message ko reply karke /broadcast"
        )
        return
    bcast_msg  = message.reply_to_message
    bcast_text = " ".join(args) if args else None
    sent = failed = 0
    notif = await message.reply_text(f"📢 Broadcasting ({mode})...")

    async def send_one(cid):
        nonlocal sent, failed
        try:
            if bcast_msg:
                await context.bot.forward_message(
                    chat_id=cid, from_chat_id=bcast_msg.chat_id,
                    message_id=bcast_msg.message_id,
                )
            else:
                await context.bot.send_message(
                    chat_id=cid, text=bcast_text, parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    if mode in ("users", "all"):
        for u in get_all_users():
            await send_one(u["user_id"])
    if mode in ("groups", "all"):
        for g in get_all_groups():
            await send_one(g["chat_id"])

    try:
        await notif.edit_text(
            f"📢 <b>Broadcast Done!</b>\n✅ Sent: <b>{sent}</b>\n❌ Failed: <b>{failed}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

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

    # ── Toggle settings ──────────────────────────────────
    elif data.startswith("tog_"):
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        key     = data[4:]
        new_val = toggle_setting(chat.id, key, False)
        icon    = "✅" if new_val else "❌"
        label   = key.replace("_on","").replace("_"," ").strip().title()
        await query.answer(f"{icon} {label} {'ON' if new_val else 'OFF'}")
        try:
            await query.edit_message_reply_markup(
                reply_markup=_settings_keyboard(chat.id)
            )
        except Exception:
            pass

    # ── Cycle movie caption mode ─────────────────────────
    elif data == "cycle_movie_caption":
        if not await _is_user_admin(context, chat.id, user.id):
            await query.answer("❌ Sirf admins!", show_alert=True)
            return
        modes   = ["off", "soft", "hard"]
        current = get_setting(chat.id, "movie_caption_mode", "hard")
        idx     = modes.index(current) if current in modes else 2
        new_mode = modes[(idx + 1) % len(modes)]
        set_setting(chat.id, "movie_caption_mode", new_mode)
        await query.answer(f"🎬 Caption mode: {new_mode.upper()}")
        try:
            await query.edit_message_reply_markup(
                reply_markup=_settings_keyboard(chat.id)
            )
        except Exception:
            pass

    # ── Settings sub-menus ───────────────────────────────
    elif data == "settings_flood":
        await query.message.reply_text(
            "⚡ <b>Flood Limit:</b>\nUse: /floodlimit <number>\nDefault: 5 msgs/10s",
            parse_mode="HTML",
        )
    elif data == "settings_autodel":
        await query.message.reply_text(
            "⏱ <b>Auto-Delete Time:</b>\nUse: /autodel <seconds>\nExample: /autodel 3600",
            parse_mode="HTML",
        )
    elif data == "settings_warn":
        await query.message.reply_text(
            "⚠️ <b>Warn Limit:</b>\nUse: /warnlimit <number>\nDefault: 3 warns → ban",
            parse_mode="HTML",
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

    elif data == "settings_main":
        try:
            await query.edit_message_reply_markup(
                reply_markup=_settings_keyboard(chat.id)
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
