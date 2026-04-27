import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from core.db import block_user, unblock_user, set_group_setting, get_all_users, get_all_groups
from core.brain import teach_pattern, forget_pattern, list_patterns

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ── Helper: admin check ───────────────────────────────────────────────

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user   = update.effective_user
    chat   = update.effective_chat
    if user.id == ADMIN_ID:
        return True
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)

async def get_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply se ya @mention se target user ID lo"""
    message = update.effective_message
    if message.reply_to_message:
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

# ── BAN ───────────────────────────────────────────────────────────────

async def ban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse ban karna hai? Reply karo ya @username do 🙄")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(
            f"🚫 {target.full_name} ko ban kar diya gaya!\nBye bye~ 👋",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔓 Unban", callback_data=f"unban_{target.id}")
            ]])
        )
    except Exception as e:
        await update.message.reply_text(f"Ban nahi kar paya 😭 Error: {e}")

# ── UNBAN ─────────────────────────────────────────────────────────────

async def unban_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse unban karna hai? 🙄")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"✅ {target.full_name} unban ho gaya! Welcome back~ 🌸")
    except Exception as e:
        await update.message.reply_text(f"Unban nahi hua 😭 Error: {e}")

# ── MUTE ──────────────────────────────────────────────────────────────

async def mute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse mute karna hai? 🙄")
    try:
        from telegram import ChatPermissions
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await update.message.reply_text(f"🔇 {target.full_name} ko mute kar diya! Chup raho~ 😤")
    except Exception as e:
        await update.message.reply_text(f"Mute nahi hua 😭 Error: {e}")

# ── UNMUTE ────────────────────────────────────────────────────────────

async def unmute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse unmute karna hai? 🙄")
    try:
        from telegram import ChatPermissions
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True
            )
        )
        await update.message.reply_text(f"🔊 {target.full_name} unmute ho gaya! Bol sakte ho ab~ 🌸")
    except Exception as e:
        await update.message.reply_text(f"Unmute nahi hua 😭 Error: {e}")

# ── KICK ──────────────────────────────────────────────────────────────

async def kick_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisse kick karna hai? 🙄")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"👟 {target.full_name} ko kick kar diya! Jao yahan se~ 😂")
    except Exception as e:
        await update.message.reply_text(f"Kick nahi hua 😭 Error: {e}")

# ── WARN ──────────────────────────────────────────────────────────────

_warnings = {}

async def warn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    target = await get_target(update, context)
    if not target:
        return await update.message.reply_text("Kisko warn karna hai? 🙄")
    uid   = target.id
    count = _warnings.get(uid, 0) + 1
    _warnings[uid] = count
    if count >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            await update.message.reply_text(
                f"⚠️ {target.full_name} ko 3 warnings mil gayi!\n🚫 Auto-ban ho gaya! Bye~ 👋"
            )
            _warnings[uid] = 0
        except Exception:
            pass
    else:
        await update.message.reply_text(
            f"⚠️ Warning {count}/3 — {target.full_name}\n"
            f"3 warnings pe auto-ban hoga! Sambhal ke raho~ 😤"
        )

# ── PIN ───────────────────────────────────────────────────────────────

async def pin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    if not update.message.reply_to_message:
        return await update.message.reply_text("Kaunsa message pin karna hai? Reply karo usse~ 🙄")
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 Message pin kar diya! Important hai yeh~ 🌸")
    except Exception as e:
        await update.message.reply_text(f"Pin nahi hua 😭 Error: {e}")

# ── SET WELCOME ───────────────────────────────────────────────────────

async def setwelcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Tumhare paas admin rights nahi hain 😤")
    if not context.args:
        return await update.message.reply_text(
            "Format: /setwelcome Heyy {name} aagaye!\n{name} = user ka naam"
        )
    msg = " ".join(context.args)
    set_group_setting(update.effective_chat.id, "welcome_msg", msg)
    await update.message.reply_text(f"✅ Welcome message set ho gaya!\n\nPreview:\n{msg.replace('{name}', 'TestUser')}")

# ── BLOCK / UNBLOCK (bot level) ───────────────────────────────────────

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

# ── TEACH ─────────────────────────────────────────────────────────────

async def teach_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Sirf admin sikha sakta hai mujhe 😤")
    if not context.args:
        return await update.message.reply_text(
            "Format: /teach trigger | response\n\nExample:\n/teach hello kaise ho | Heyy! Main theek hoon~ 🌸"
        )
    text = " ".join(context.args)
    ok, trigger, response = teach_pattern(text, update.effective_user.id)
    if ok:
        await update.message.reply_text(
            f"✅ Seekh liya maine!\n\n"
            f"Trigger: <code>{trigger}</code>\n"
            f"Response: {response}",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("Format galat hai 😭 Use: /teach trigger | response")

# ── FORGET ───────────────────────────────────────────────────────────

async def forget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("Sirf admin bhula sakta hai 😤")
    if not context.args:
        return await update.message.reply_text("Kaunsa pattern bhooloon? /forget trigger")
    trigger = " ".join(context.args)
    forget_pattern(trigger)
    await update.message.reply_text(f"🗑️ Pattern bhool gaya: <code>{trigger}</code>", parse_mode="HTML")

# ── PATTERNS LIST ────────────────────────────────────────────────────

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

# ── BROADCAST ────────────────────────────────────────────────────────

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
