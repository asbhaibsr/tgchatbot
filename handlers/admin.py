"""
Admin Commands — Ban/Unban/Mute/Kick/Warn/Pin/Purge/Lock + Premium & Settings
All features from ASGroupBot ported to python-telegram-bot (PTB) framework.
"""
import os
import re
import asyncio
import random
from datetime import datetime, timedelta

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

from core.db import (
    block_user, unblock_user, set_setting, get_setting, toggle_setting,
    get_all_users, get_all_groups, is_premium, set_premium, revoke_premium,
    add_warn, get_warns, get_warn_reasons, reset_warns,
    save_prem_request
)
from core.brain import teach_pattern, forget_pattern, list_patterns

ADMIN_ID      = int(os.environ.get("ADMIN_ID", "0"))
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"
UPI_ID         = "arsadsaifi8272@ibl"
PREMIUM_PRICE  = 200
BOT_NAME       = "ᴀꜱ ɢʀᴏᴜᴘ ʙᴏᴛ"

# ── Premium conversation states (in-memory) ───────────────────────────
_prem_state: dict = {}

# Auto-delete & warn presets
DEL_PRESETS  = [300, 900, 1800, 3600, 7200, 21600, 43200, 86400]
WARN_PRESETS = [2, 3, 4, 5]

# ── Small caps helper ─────────────────────────────────────────────────
_SC = {'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ғ','g':'ɢ','h':'ʜ',
       'i':'ɪ','j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ',
       'q':'ǫ','r':'ʀ','s':'ꜱ','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x',
       'y':'ʏ','z':'ᴢ'}

def sc(text: str) -> str:
    return ''.join(_SC.get(c, c) for c in text.lower())

def fmt_time(seconds: int) -> str:
    if seconds < 60:    return f"{seconds}s"
    if seconds < 3600:  return f"{seconds // 60}m"
    if seconds < 86400: return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"

def parse_time(s: str):
    """'1h'/'30m'/'2d' → timedelta or None"""
    m = re.match(r'^(\d+)([smhd]?)$', (s or '').lower().strip())
    if not m:
        return None
    v, u = int(m.group(1)), m.group(2) or 'm'
    return timedelta(seconds=v * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[u])

# ── Helper: admin check ───────────────────────────────────────────────

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user.id == ADMIN_ID:
        return True
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if context.args:
        username = context.args[0].lstrip("@")
        try:
            chat_member = await context.bot.get_chat_member(
                update.effective_chat.id, username
            )
            return chat_member.user
        except Exception:
            return None
    return None

async def need_premium(update: Update):
    await update.message.reply_text(
        "👑 <b>Premium Feature!</b>\n\n"
        "Ye command premium groups ke liye hai.\n"
        "👉 /premium — ₹200/month mein activate karo!",
        parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════════════
#  🔨 BAN / UNBAN
# ═══════════════════════════════════════════════════════════

async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins kar sakte hain!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse ban karna hai? Reply karo ya @username do 🙄")
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(
            f"🔨 <b>ʙᴀɴ ʜᴀᴍᴍᴇʀ ᴅʀᴏᴘᴘᴇᴅ</b> 🔨\n\n"
            f"┌ 👤 <b>{target.full_name}</b>\n"
            f"├ 🆔 <code>{target.id}</code>\n"
            f"├ 📝 {reason}\n"
            f"└ 🚫 <b>Status: BANNED</b>\n\n"
            f"━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Unban karo", callback_data=f"unban_{target.id}")
            ]])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ban fail: {e}")

async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse unban karna hai? 🙄")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"✅ <b>Unbanned:</b> {target.full_name}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Unban fail: {e}")

# ═══════════════════════════════════════════════════════════
#  🔇 MUTE / UNMUTE
# ═══════════════════════════════════════════════════════════

async def mute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse mute karna hai? 🙄")
    # Optional timed mute
    duration_str = context.args[1] if context.args and len(context.args) > 1 else None
    td = parse_time(duration_str) if duration_str else None
    until = datetime.now() + td if td else None
    dur_text = fmt_time(int(td.total_seconds())) if td else "∞"
    reason = " ".join(context.args[2:]) if context.args and len(context.args) > 2 else "No reason"
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )
        await update.message.reply_text(
            f"🔇 <b>ᴍᴜᴛᴇ ᴀᴘᴘʟɪᴇᴅ</b> 🔇\n\n"
            f"┌ 👤 <b>{target.full_name}</b>\n"
            f"├ 🆔 <code>{target.id}</code>\n"
            f"├ ⏱ <b>Duration:</b> {dur_text}\n"
            f"├ 📝 {reason}\n"
            f"└ 🔕 <b>Status: MUTED</b>\n\n"
            f"━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔊 Unmute karo", callback_data=f"unmute_{target.id}")
            ]])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Mute fail: {e}")

async def unmute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse unmute karna hai? 🙄")
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True
            )
        )
        await update.message.reply_text(f"🔊 <b>Unmuted:</b> {target.full_name}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Unmute fail: {e}")

# ═══════════════════════════════════════════════════════════
#  👟 KICK
# ═══════════════════════════════════════════════════════════

async def kick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse kick karna hai? 🙄")
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason"
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(
            f"👟 <b>ᴋɪᴄᴋᴇᴅ ᴏᴜᴛ</b> 👟\n\n"
            f"┌ 👤 <b>{target.full_name}</b>\n"
            f"├ 🆔 <code>{target.id}</code>\n"
            f"└ 📝 {reason}\n\n"
            f"💨 Bahar kar diya~\n"
            f"━━━━━━━━━━━━━━━━",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Kick fail: {e}")

# ═══════════════════════════════════════════════════════════
#  ⚠️ WARN
# ═══════════════════════════════════════════════════════════

async def warn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisko warn karna hai? 🙄")
    reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "No reason"
    chat_id = update.effective_chat.id
    warn_limit = get_setting(chat_id, "warn_limit", 3)
    count = add_warn(chat_id, target.id, reason, update.effective_user.id)
    if count >= warn_limit:
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            reset_warns(chat_id, target.id)
            await update.message.reply_text(
                f"💀 <b>ᴀᴜᴛᴏ-ʙᴀɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ</b> 💀\n\n"
                f"┌ 👤 {target.full_name}\n"
                f"├ ⚠️ Warns: {count}/{warn_limit}\n"
                f"└ 🔨 Status: <b>BANNED</b>\n\n"
                f"🚫 Limit cross kar di inhone~\n"
                f"━━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"Warn diya par ban fail: {e}")
    else:
        bars = "█" * count + "░" * (warn_limit - count)
        await update.message.reply_text(
            f"⚠️ <b>ᴡᴀʀɴɪɴɢ ᴅɪꜱᴘᴀᴛᴄʜᴇᴅ</b> ⚠️\n\n"
            f"┌ 👤 <b>User:</b> {target.full_name}\n"
            f"├ 📝 <b>Reason:</b> {reason}\n"
            f"├ ⚡ <b>Warns:</b> [{bars}] {count}/{warn_limit}\n"
            f"└ 💀 <b>Auto-ban:</b> {warn_limit} pe hoga\n\n"
            f"{'🚨 <b>Danger Zone!</b> Ek aur aur ban~' if count >= warn_limit - 1 else '⚠️ Sambhalo apne aap ko~'}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Reset", callback_data=f"resetwarn_{target.id}"),
                    InlineKeyboardButton("🔇 Mute", callback_data=f"rep_mute_{target.id}"),
                    InlineKeyboardButton("🔨 Ban", callback_data=f"rep_ban_{target.id}"),
                ]
            ])
        )

async def warns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kiska warns check karein? Reply karo ya @username do")
    chat_id = update.effective_chat.id
    count = get_warns(chat_id, target.id)
    reasons = get_warn_reasons(chat_id, target.id)
    warn_limit = get_setting(chat_id, "warn_limit", 3)
    text = f"⚠️ <b>{target.full_name} ke Warns: {count}/{warn_limit}</b>\n\n"
    for i, r in enumerate(reasons, 1):
        text += f"{i}. {r}\n"
    await update.message.reply_text(text, parse_mode="HTML")

async def resetwarn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kiska warn reset karein?")
    reset_warns(update.effective_chat.id, target.id)
    await update.message.reply_text(f"🔄 {target.full_name} ke warns reset ho gaye!")

# ═══════════════════════════════════════════════════════════
#  📌 PIN / UNPIN / DEL
# ═══════════════════════════════════════════════════════════

async def pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not update.message.reply_to_message:
        return await update.message.reply_text("Kaunsa message pin karna hai? Reply karo usse~ 🙄")
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 Message pin kar diya!")
    except Exception as e:
        await update.message.reply_text(f"❌ Pin fail: {e}")

async def unpin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    try:
        await context.bot.unpin_chat_message(update.effective_chat.id)
        await update.message.reply_text("📌 Message unpin ho gaya!")
    except Exception as e:
        await update.message.reply_text(f"❌ Unpin fail: {e}")

async def del_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("Kaunsa message delete karein? Reply karo.")
    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Delete fail: {e}")

# ═══════════════════════════════════════════════════════════
#  🗑 PURGE
# ═══════════════════════════════════════════════════════════

async def purge_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    if not update.message.reply_to_message:
        return await update.message.reply_text("Kahan se purge karein? Pehle message reply karo.")
    n = 1
    if context.args:
        try:
            n = min(int(context.args[0]), 100)
        except ValueError:
            pass
    from_id = update.message.reply_to_message.message_id
    to_id   = update.message.message_id
    deleted = 0
    for mid in range(from_id, to_id + 1):
        try:
            await context.bot.delete_message(update.effective_chat.id, mid)
            deleted += 1
        except Exception:
            pass
    notif = await update.message.reply_text(f"🗑 {deleted} messages purge ho gaye!")
    await asyncio.sleep(3)
    try:
        await notif.delete()
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════
#  👮 PROMOTE / DEMOTE
# ═══════════════════════════════════════════════════════════

async def promote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse promote karein?")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_invite_users=True
        )
        await update.message.reply_text(f"👮 {target.full_name} ko admin bana diya!")
    except Exception as e:
        await update.message.reply_text(f"❌ Promote fail: {e}")

async def demote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse demote karein?")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_delete_messages=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_invite_users=False
        )
        await update.message.reply_text(f"👤 {target.full_name} ko demote kar diya!")
    except Exception as e:
        await update.message.reply_text(f"❌ Demote fail: {e}")

# ═══════════════════════════════════════════════════════════
#  🔒 LOCK / UNLOCK
# ═══════════════════════════════════════════════════════════

LOCK_TYPES = ["links", "stickers", "gifs", "media", "polls"]

async def lock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    if not context.args:
        return await update.message.reply_text(
            f"Format: /lock <type>\nTypes: {', '.join(LOCK_TYPES)}"
        )
    lock_type = context.args[0].lower()
    if lock_type not in LOCK_TYPES:
        return await update.message.reply_text(f"❌ Valid types: {', '.join(LOCK_TYPES)}")
    chat_id = update.effective_chat.id
    locked = get_setting(chat_id, "locked_types", []) or []
    if lock_type not in locked:
        locked.append(lock_type)
    set_setting(chat_id, "locked_types", locked)
    await update.message.reply_text(f"🔒 {lock_type.capitalize()} locked!")

async def unlock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    if not context.args:
        return await update.message.reply_text(f"Format: /unlock <type>")
    lock_type = context.args[0].lower()
    chat_id = update.effective_chat.id
    locked = get_setting(chat_id, "locked_types", []) or []
    if lock_type in locked:
        locked.remove(lock_type)
    set_setting(chat_id, "locked_types", locked)
    await update.message.reply_text(f"🔓 {lock_type.capitalize()} unlocked!")

# ═══════════════════════════════════════════════════════════
#  📋 RULES
# ═══════════════════════════════════════════════════════════

async def setrules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not context.args:
        return await update.message.reply_text("Format: /setrules 1. No spam\n2. Be nice")
    rules = " ".join(context.args)
    set_setting(update.effective_chat.id, "rules", rules)
    await update.message.reply_text("✅ Rules set kar diye!")

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("Ye command group mein use karo!")
    rules = get_setting(chat.id, "rules", None)
    if not rules:
        return await update.message.reply_text("❌ Koi rules set nahi hue.\nAdmin: /setrules ...")
    await update.message.reply_text(f"📋 <b>Group Rules:</b>\n\n{rules}", parse_mode="HTML")

# ═══════════════════════════════════════════════════════════
#  📝 SET WELCOME / GOODBYE
# ═══════════════════════════════════════════════════════════

async def setwelcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not context.args:
        return await update.message.reply_text(
            "Format: /setwelcome Heyy {name} aagaye!\n{name} = user ka naam"
        )
    msg = " ".join(context.args)
    set_setting(update.effective_chat.id, "welcome_msg", msg)
    await update.message.reply_text(
        f"✅ Welcome message set!\n\nPreview:\n{msg.replace('{name}', 'TestUser')}",
        parse_mode="HTML"
    )

async def setgoodbye_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not context.args:
        return await update.message.reply_text("Format: /setgoodbye Bye {name}! 👋")
    msg = " ".join(context.args)
    set_setting(update.effective_chat.id, "goodbye_msg", msg)
    await update.message.reply_text(
        f"✅ Goodbye message set!\n\nPreview:\n{msg.replace('{name}', 'TestUser')}",
        parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════════════
#  👥 TAG ALL (premium)
# ═══════════════════════════════════════════════════════════

async def tagall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf admins!")
    if not is_premium(update.effective_chat.id):
        return await need_premium(update)
    from core.db import get_active_members
    members = get_active_members(update.effective_chat.id)
    if not members:
        return await update.message.reply_text("Koi active member nahi mila DB mein.")
    custom_msg = " ".join(context.args) if context.args else "📢 Attention!"
    mentions = ""
    batch = []
    for m in members:
        batch.append(f'<a href="tg://user?id={m["user_id"]}">⁠</a>')
        if len(batch) >= 5:
            await update.message.reply_text(
                custom_msg + "\n" + "".join(batch),
                parse_mode="HTML"
            )
            batch = []
            await asyncio.sleep(0.5)
    if batch:
        await update.message.reply_text(
            custom_msg + "\n" + "".join(batch),
            parse_mode="HTML"
        )

# ═══════════════════════════════════════════════════════════
#  📋 ADMINLIST
# ═══════════════════════════════════════════════════════════

async def adminlist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        text = "👮 <b>Group Admins:</b>\n\n"
        for a in admins:
            name = a.user.full_name
            username = f"@{a.user.username}" if a.user.username else ""
            role = "👑 Creator" if a.status == "creator" else "🔰 Admin"
            text += f"{role} — {name} {username}\n"
        await update.message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ═══════════════════════════════════════════════════════════
#  🚫 BLOCK / UNBLOCK (bot level)
# ═══════════════════════════════════════════════════════════

async def blockuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisko block karna hai?")
    block_user(target.id)
    await update.message.reply_text(f"🚫 {target.full_name} bot pe block ho gaya!")

async def unblockuser_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisko unblock karna hai?")
    unblock_user(target.id)
    await update.message.reply_text(f"✅ {target.full_name} unblock ho gaya!")

# ═══════════════════════════════════════════════════════════
#  🧠 TEACH / FORGET / PATTERNS
# ═══════════════════════════════════════════════════════════

async def teach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Sirf admin sikha sakta hai mujhe 😤")
    if not context.args:
        return await update.message.reply_text(
            "Format: /teach trigger | response\n\nExample:\n/teach hello | Heyy! Kaise ho~ 🌸"
        )
    text = " ".join(context.args)
    ok, trigger, response = teach_pattern(text, update.effective_user.id)
    if ok:
        await update.message.reply_text(
            f"✅ Seekh liya!\n\nTrigger: <code>{trigger}</code>\nResponse: {response}",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("Format galat hai 😭 Use: /teach trigger | response")

async def forget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Sirf admin bhula sakta hai 😤")
    if not context.args:
        return await update.message.reply_text("Kaunsa pattern bhooloon? /forget trigger")
    trigger = " ".join(context.args)
    forget_pattern(trigger)
    await update.message.reply_text(f"🗑️ Pattern bhool gaya: <code>{trigger}</code>", parse_mode="HTML")

async def patterns_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return
    all_p = list_patterns()
    if not all_p:
        return await update.message.reply_text("Koi pattern nahi sikha abhi tak 😅")
    text = "📚 <b>Sikhe hue Patterns:</b>\n\n"
    for p in all_p[:20]:
        count = len(p.get("responses", []))
        text += f"• <code>{p['trigger']}</code> → {count} response(s)\n"
    if len(all_p) > 20:
        text += f"\n...aur {len(all_p)-20} patterns hain"
    await update.message.reply_text(text, parse_mode="HTML")

# ═══════════════════════════════════════════════════════════
#  📢 BROADCAST
# ═══════════════════════════════════════════════════════════

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("Sirf main hi broadcast kar sakta hoon 😤")
    if not context.args:
        return await update.message.reply_text("Kya broadcast karna hai? /broadcast message")
    text   = " ".join(context.args)
    users  = get_all_users()
    groups = get_all_groups()
    sent = failed = 0
    for u in users:
        try:
            await context.bot.send_message(u["user_id"], text)
            sent += 1
        except Exception:
            failed += 1
    for g in groups:
        try:
            await context.bot.send_message(g["chat_id"], text)
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"📢 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}"
    )

# ═══════════════════════════════════════════════════════════
#  👑 PREMIUM SYSTEM (full multi-step flow)
# ═══════════════════════════════════════════════════════════

PREM_TEXT = (
    f"👑 <b>Premium Plan — ₹{PREMIUM_PRICE}/month</b>\n\n"
    f"🏦 UPI ID: <code>{UPI_ID}</code>\n\n"
    "✨ <b>Premium Features:</b>\n"
    "• Ban, Mute, Kick users\n"
    "• Warn system with auto-ban\n"
    "• Anti-link, Anti-spam, Flood control\n"
    "• Auto-delete files from group\n"
    "• Custom welcome/goodbye templates\n"
    "• Promote / Demote admins\n"
    "• Tag all active members\n"
    "• Lock message types\n\n"
    "📋 <b>Subscribe Process:</b>\n"
    f"1. ₹{PREMIUM_PRICE} UPI pe bhejo: <code>{UPI_ID}</code>\n"
    "2. Neeche Subscribe button dabao\n"
    "3. Group ID bhejo\n"
    "4. UTR / Transaction ID bhejo\n"
    "5. Screenshot bhejo\n"
    "6. Owner verify karega\n\n"
    "⚡ Ek group ke liye valid."
)

async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    text = PREM_TEXT
    if chat.type != "private":
        text += f"\n\n📌 <b>Aapke Group ki ID:</b> <code>{chat.id}</code>"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Subscribe", callback_data="prem_start")],
        [InlineKeyboardButton(f"📢 Updates", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}")],
    ])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)

async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command: /approve group_id"""
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("Sirf Owner ye kar sakta hai!")
    if not context.args:
        return await update.message.reply_text("Format: /approve group_id")
    try:
        group_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❌ Valid group ID do!")
    set_premium(group_id, months=1)
    await update.message.reply_text(f"✅ Group <code>{group_id}</code> ab Premium hai! (1 month)", parse_mode="HTML")
    try:
        await context.bot.send_message(
            group_id,
            f"🎉 <b>{BOT_NAME} Premium Activated!</b>\n\n"
            "👑 Is group mein ab premium features available hain!\n"
            "Admin /settings karo sab enable karne ke liye.",
            parse_mode="HTML"
        )
    except Exception:
        pass

async def revoke_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return await update.message.reply_text("Format: /revoke group_id")
    try:
        gid = int(context.args[0])
        revoke_premium(gid)
        await update.message.reply_text(f"✅ Premium revoked for <code>{gid}</code>", parse_mode="HTML")
        try:
            await context.bot.send_message(gid, "⚠️ Premium expired / revoked. /premium se renew karo.")
        except Exception:
            pass
    except ValueError:
        await update.message.reply_text("❌ Valid group ID do!")

async def checkprem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        return await update.message.reply_text("Format: /checkprem group_id")
    try:
        gid = int(context.args[0])
        from core.db import get_group
        g = get_group(gid)
        status = is_premium(gid)
        exp = g.get("premium_expires") if g else None
        await update.message.reply_text(
            f"Group: <code>{gid}</code>\n"
            f"Premium: {'✅ Active' if status else '❌ Inactive'}\n"
            f"Expires: {exp.strftime('%d %b %Y') if exp else 'N/A'}",
            parse_mode="HTML"
        )
    except ValueError:
        await update.message.reply_text("❌ Valid group ID do!")

# ═══════════════════════════════════════════════════════════
#  ⚙️ SETTINGS PANEL
# ═══════════════════════════════════════════════════════════

def _icon(val: bool) -> str:
    return "✅" if val else "❌"

async def _build_settings_panel(chat_id: int, chat_title: str, prem: bool):
    welcome  = get_setting(chat_id, "welcome_on",  True)
    goodbye  = get_setting(chat_id, "goodbye_on",  True)
    chatbot  = get_setting(chat_id, "chat_bot_on", True)
    antilink = get_setting(chat_id, "antilink_on", False)
    antifwd  = get_setting(chat_id, "antifwd_on",  False)
    antispam = get_setting(chat_id, "antispam_on", False)
    flood    = get_setting(chat_id, "flood_on",    False)
    autodel  = get_setting(chat_id, "autodel_on",  False)
    del_time = get_setting(chat_id, "autodel_time", 3600)
    warn_lim = get_setting(chat_id, "warn_limit",   3)

    def prow(label, cb, state):
        if not prem:
            return InlineKeyboardButton(f"🔒 {sc(label)}", callback_data="prem_locked")
        icon = _icon(state) + " "
        return InlineKeyboardButton(f"{icon}{sc(label)}", callback_data=cb)

    keyboard = [
        # Row 1: Welcome | Goodbye
        [
            InlineKeyboardButton(f"{_icon(welcome)} ᴡᴇʟᴄᴏᴍᴇ", callback_data="tog_welcome"),
            InlineKeyboardButton(f"{_icon(goodbye)} ɢᴏᴏᴅʙʏᴇ", callback_data="tog_goodbye"),
        ],
        # Row 2: Chatbot (free)
        [
            InlineKeyboardButton(f"{_icon(chatbot)} ᴄʜᴀᴛ ʙᴏᴛ", callback_data="tog_chatbot"),
        ],
        # Row 3: Anti-link | Anti-fwd (premium)
        [
            prow("anti-link", "tog_antilink", antilink),
            prow("anti-fwd",  "tog_antifwd",  antifwd),
        ],
        # Row 4: Anti-spam | Flood (premium)
        [
            prow("anti-spam", "tog_antispam", antispam),
            prow("flood",     "tog_flood",    flood),
        ],
        # Row 5: Auto-del | Warn limit (premium)
        [
            prow("auto-del", "tog_autodel", autodel),
            InlineKeyboardButton(
                ("🔒 ᴡᴀʀɴ" if not prem else f"⚠️ ᴡᴀʀɴ: {warn_lim}"),
                callback_data="cycle_warnlim" if prem else "prem_locked"
            ),
        ],
        # Row 6: Del timer (premium)
        [
            InlineKeyboardButton(
                ("🔒 ᴀᴜᴛᴏ ᴅᴇʟ ᴛɪᴍᴇ" if not prem else f"⏱ ᴅᴇʟ ᴛɪᴍᴇ: {fmt_time(del_time)}"),
                callback_data="cycle_deltime" if prem else "prem_locked"
            ),
        ],
        # Row 7: Refresh | Close
        [
            InlineKeyboardButton(f"🔄 ʀᴇꜰʀᴇꜱʜ", callback_data="settings_refresh"),
            InlineKeyboardButton(f"✖️ ᴄʟᴏꜱᴇ",   callback_data="close"),
        ],
    ]
    if not prem:
        keyboard.append([
            InlineKeyboardButton("👑 ɢᴇᴛ ᴘʀᴇᴍɪᴜᴍ", callback_data="prem_info")
        ])

    prem_badge = "👑 Premium" if prem else "🆓 Free"
    text = (
        f"⚙️ <b>{sc('settings')}</b> — {chat_title}\n"
        f"Plan: {prem_badge}\n\n"
        "✅ = on  |  ❌ = off  |  🔒 = premium only"
    )
    return text, InlineKeyboardMarkup(keyboard)

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 Sirf group admins /settings use kar sakte hain!")
    chat = update.effective_chat
    prem = is_premium(chat.id)
    text, markup = await _build_settings_panel(chat.id, chat.title, prem)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)

# ═══════════════════════════════════════════════════════════
#  🔘 ALL CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data    = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # ── Admin check helper (inline) ───────────────────────
    async def _is_adm():
        if user_id == ADMIN_ID:
            return True
        try:
            m = await context.bot.get_chat_member(chat_id, user_id)
            return m.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
        except Exception:
            return False

    # ── Unban ────────────────────────────────────────────
    if data.startswith("unban_"):
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        uid = int(data.split("_")[1])
        try:
            await context.bot.unban_chat_member(chat_id, uid)
            await query.answer("✅ Unban ho gaya!")
            await query.edit_message_reply_markup(None)
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)

    # ── Unmute ───────────────────────────────────────────
    elif data.startswith("unmute_"):
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        uid = int(data.split("_")[1])
        try:
            await context.bot.restrict_chat_member(
                chat_id, uid,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True
                )
            )
            await query.answer("🔊 Unmute ho gaya!")
            await query.edit_message_reply_markup(None)
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)

    # ── Reset Warn ───────────────────────────────────────
    elif data.startswith("resetwarn_"):
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        uid = int(data.split("_")[1])
        reset_warns(chat_id, uid)
        await query.answer("🔄 Warns reset!")
        await query.edit_message_reply_markup(None)

    # ── Premium: info ─────────────────────────────────────
    elif data == "prem_info":
        prem = is_premium(chat_id)
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Subscribe", callback_data="prem_start")],
            [InlineKeyboardButton("✖️ Close", callback_data="close")],
        ])
        await query.edit_message_text(PREM_TEXT, parse_mode="HTML", reply_markup=markup)

    # ── Premium: start subscribe ──────────────────────────
    elif data == "prem_start":
        if query.message.chat.type != "private":
            return await query.answer("💬 Pehle bot ko PM mein open karo!", show_alert=True)
        _prem_state[user_id] = {"step": "group_id", "data": {}}
        await query.edit_message_text(
            "📱 <b>Step 1 / 3 — Group ID</b>\n\n"
            "Apne group ka ID bhejo.\n\n"
            "Group ID kaise milega?\n"
            "• Group mein /id command karo\n"
            "• ID <code>-100</code> se shuru hoti hai\n\n"
            "Example: <code>-1009876543210</code>\n\n"
            "<i>/cancel — cancel karne ke liye</i>",
            parse_mode="HTML"
        )

    # ── Settings: free toggles ────────────────────────────
    elif data in ("tog_welcome", "tog_goodbye", "tog_chatbot"):
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        key_map = {"tog_welcome": "welcome_on", "tog_goodbye": "goodbye_on", "tog_chatbot": "chat_bot_on"}
        new_val = toggle_setting(chat_id, key_map[data], True)
        prem = is_premium(chat_id)
        text, markup = await _build_settings_panel(chat_id, query.message.chat.title, prem)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        await query.answer(f"{'✅ On' if new_val else '❌ Off'}")

    # ── Settings: premium toggles ─────────────────────────
    elif data in ("tog_antilink", "tog_antifwd", "tog_antispam", "tog_flood", "tog_autodel"):
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        if not is_premium(chat_id):
            return await query.answer("👑 Premium required!", show_alert=True)
        key_map = {
            "tog_antilink": "antilink_on",
            "tog_antifwd":  "antifwd_on",
            "tog_antispam": "antispam_on",
            "tog_flood":    "flood_on",
            "tog_autodel":  "autodel_on",
        }
        new_val = toggle_setting(chat_id, key_map[data], False)
        text, markup = await _build_settings_panel(chat_id, query.message.chat.title, True)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        await query.answer(f"{'✅ On' if new_val else '❌ Off'}")

    # ── Cycle del time ────────────────────────────────────
    elif data == "cycle_deltime":
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        if not is_premium(chat_id):
            return await query.answer("👑 Premium required!", show_alert=True)
        cur = get_setting(chat_id, "autodel_time", 3600)
        try:
            idx = DEL_PRESETS.index(cur)
            nxt = DEL_PRESETS[(idx + 1) % len(DEL_PRESETS)]
        except ValueError:
            nxt = DEL_PRESETS[0]
        set_setting(chat_id, "autodel_time", nxt)
        text, markup = await _build_settings_panel(chat_id, query.message.chat.title, True)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        await query.answer(f"⏱ Auto-delete: {fmt_time(nxt)}")

    # ── Cycle warn limit ──────────────────────────────────
    elif data == "cycle_warnlim":
        if not await _is_adm():
            return await query.answer("Sirf admins!", show_alert=True)
        if not is_premium(chat_id):
            return await query.answer("👑 Premium required!", show_alert=True)
        cur = get_setting(chat_id, "warn_limit", 3)
        try:
            idx = WARN_PRESETS.index(cur)
            nxt = WARN_PRESETS[(idx + 1) % len(WARN_PRESETS)]
        except ValueError:
            nxt = 3
        set_setting(chat_id, "warn_limit", nxt)
        text, markup = await _build_settings_panel(chat_id, query.message.chat.title, True)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        await query.answer(f"⚠️ Warn limit: {nxt}")

    # ── Settings refresh ──────────────────────────────────
    elif data == "settings_refresh":
        prem = is_premium(chat_id)
        text, markup = await _build_settings_panel(chat_id, query.message.chat.title, prem)
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)
        await query.answer("🔄 Refreshed!")

    # ── Premium locked notice ─────────────────────────────
    elif data == "prem_locked":
        await query.answer("👑 Ye Premium feature hai! /premium se activate karo.", show_alert=True)

    # ── Close ─────────────────────────────────────────────
    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            await query.answer("Close nahi hua 😅")

    # ── Owner: approve premium ────────────────────────────
    elif data.startswith("prem_a_"):
        if user_id != ADMIN_ID:
            return await query.answer("Sirf Owner!", show_alert=True)
        parts = data.split("_")
        req_user_id = int(parts[2])
        req_group_id = int(parts[3])
        set_premium(req_group_id, months=1)
        try:
            await context.bot.send_message(
                req_user_id,
                f"🎉 <b>Premium Approved!</b>\n\n"
                f"Group <code>{req_group_id}</code> pe premium activate ho gaya!\n"
                f"Duration: 1 month\n\n"
                f"Ab group mein /settings karo!\n"
                f"Support: {OWNER_USERNAME}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        try:
            await context.bot.send_message(
                req_group_id,
                f"🎉 <b>{BOT_NAME} Premium Activated!</b>\n\n"
                "👑 Is group mein ab premium features available hain!\n"
                "Admin /settings karo sab enable karne ke liye.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await query.edit_message_caption(
            (query.message.caption or "") + "\n\n✅ APPROVED by owner",
            reply_markup=None
        )
        await query.answer("✅ Approved!")

    # ── Owner: reject premium ─────────────────────────────
    elif data.startswith("prem_r_"):
        if user_id != ADMIN_ID:
            return await query.answer("Sirf Owner!", show_alert=True)
        req_user_id = int(data.split("_")[2])
        try:
            await context.bot.send_message(
                req_user_id,
                f"❌ <b>Premium Request Rejected</b>\n\n"
                "Aapki request is baar approve nahi hui.\n"
                f"Agar galti se hua hai toh directly contact karo:\n{OWNER_USERNAME}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await query.edit_message_caption(
            (query.message.caption or "") + "\n\n❌ REJECTED by owner",
            reply_markup=None
        )
        await query.answer("❌ Rejected!")

# ── Premium PM conversation handler (Step-by-step) ────────────────────

async def pm_premium_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle premium subscription steps in PM"""
    user_id = update.effective_user.id
    if user_id not in _prem_state:
        return False  # not in conversation
    message = update.effective_message
    step = _prem_state[user_id]["step"]

    # Step 1: Group ID
    if step == "group_id":
        text = (message.text or "").strip()
        if not (text.startswith("-100") and text[4:].isdigit()):
            await message.reply_text(
                "❌ Valid group ID chahiye!\n"
                "Example: <code>-1009876543210</code>\n\n"
                "<i>/cancel — cancel karo</i>",
                parse_mode="HTML"
            )
            return True
        _prem_state[user_id]["data"]["group_id"] = int(text)
        _prem_state[user_id]["step"] = "utr"
        await message.reply_text(
            f"💳 <b>Step 2 / 3 — UTR / Transaction ID</b>\n\n"
            f"₹{PREMIUM_PRICE} UPI transfer ke baad jo <b>Transaction ID / UTR</b> mila, wo bhejo.\n\n"
            "Example: <code>T2024123456789</code>\n\n"
            "<i>/cancel — cancel karo</i>",
            parse_mode="HTML"
        )
        return True

    # Step 2: UTR
    elif step == "utr":
        utr = (message.text or "").strip()
        if len(utr) < 4:
            await message.reply_text("❌ Valid UTR/Transaction ID bhejo!")
            return True
        _prem_state[user_id]["data"]["utr"] = utr
        _prem_state[user_id]["step"] = "screenshot"
        await message.reply_text(
            "📸 <b>Step 3 / 3 — Screenshot</b>\n\n"
            "Payment ka <b>screenshot</b> bhejo (photo ke roop mein).\n\n"
            "<i>/cancel — cancel karo</i>",
            parse_mode="HTML"
        )
        return True

    # Step 3: Screenshot
    elif step == "screenshot":
        if not message.photo and not message.document:
            await message.reply_text(
                "❌ Screenshot chahiye!\n\n"
                "Gallery se screenshot photo ke roop mein bhejo 📸\n"
                "File ya text nahi — direct photo bhejo.\n\n"
                "<i>/cancel — cancel karo</i>",
                parse_mode="HTML"
            )
            return True
        data = _prem_state[user_id]["data"]
        if message.photo:
            data["screenshot"] = message.photo[-1].file_id
        else:
            data["screenshot"] = message.document.file_id
        req_doc = save_prem_request(user_id, data["group_id"], data["utr"], data["screenshot"])
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"prem_a_{user_id}_{data['group_id']}"),
                InlineKeyboardButton("❌ Reject",  callback_data=f"prem_r_{user_id}"),
            ]
        ])
        try:
            await context.bot.send_photo(
                ADMIN_ID,
                photo=data["screenshot"],
                caption=(
                    f"💳 <b>New Premium Request</b>\n\n"
                    f"👤 User: {update.effective_user.full_name}\n"
                    f"🆔 User ID: <code>{user_id}</code>\n"
                    f"👥 Group ID: <code>{data['group_id']}</code>\n"
                    f"💰 UTR: <code>{data['utr']}</code>\n"
                    f"💵 Amount: ₹{PREMIUM_PRICE}/month"
                ),
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            await message.reply_text(
                f"❌ Owner tak request nahi pauhnchi: {e}\n"
                f"Please owner se directly contact karo: {OWNER_USERNAME}"
            )
            del _prem_state[user_id]
            return True

        del _prem_state[user_id]
        await message.reply_text(
            "✅ <b>Request Submit Ho Gayi!</b>\n\n"
            "Owner jaldi verify karega.\n"
            f"Direct baat karo: {OWNER_USERNAME}\n\n"
            "Verification ke baad aapke group mein bot message bhejega! 🎉",
            parse_mode="HTML"
        )
        return True

    return False

async def cancel_premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in _prem_state:
        del _prem_state[uid]
        await update.message.reply_text("❌ Premium subscription cancel kar diya.")
    else:
        await update.message.reply_text("Koi active process nahi hai.")
