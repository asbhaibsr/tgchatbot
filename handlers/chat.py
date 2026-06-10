import os, re, asyncio, random
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from core.db import (
    save_user, save_message, is_blocked, get_setting, is_premium,
    is_flooding, schedule_delete, save_active_member, inc_message_count,
    push_context, get_gaali_strikes, inc_gaali_strike, reset_gaali_strikes,
    store_file_hash, find_file_by_unique_id, get_note, get_all_notes,
    record_raid_join, detect_raid, add_warn, get_warns, reset_warns,
    get_captcha, del_captcha,
)
from core.brain import (
    make_girl_reply, make_gaali_reply,
    learn_from_conversation, learn_from_bot_reply,
)
from core.persona import BOT_TRIGGERS, get_sticker, should_send_sticker

ADMIN_ID         = int(os.environ.get("ADMIN_ID", "0"))
FILE_LOG_CHANNEL = os.environ.get("FILE_LOG_CHANNEL", "")

# ══════════════════════════════════════════════════════════
# ANTI-GAALI — 200+ words + leetspeak
# ══════════════════════════════════════════════════════════
GAALI_LIST = {
    "chutiya","chootiya","chutia","chut","chooti","choot",
    "madarchod","madarchot","madarchood","mc","maderchod","maderchoot",
    "bhenchod","bhencho","bhainchod","bhenchoot","bc","bhaichod",
    "bhosdike","bhosdiwale","bhosdiwala","bhosdi","bhosdina",
    "harami","haramzada","haramkhor","haramzadi","haraami","haramkhor",
    "randi","randa","randwa","raand","raundi","randibaaz",
    "gandu","gaandu","gand","gandiya",
    "saala","saali","sala","saale","saalon",
    "kamina","kamini","kamine","kameena","kameeni",
    "kutte","kutta","kutiya","kutti","kuttiya","kuttiya",
    "ullu","ullupan","ulluke","ullukapattha",
    "bakchod","bakchodi","bakchood",
    "lund","lauda","lawda","lawde","lode","lavde","lavda",
    "gaand","gaandu","gandu",
    "hijra","hijda","kinner","chakka","meetha",
    "nikamma","nalayak","bewakoof","bevakoof",
    "chodu","chodna","choda","chod","chodke",
    "suar","suwar","suarke",
    "gadha","gadhe","gadhi","gandhaa",
    "besharam","behaya","beghairat",
    "tatti","tattu","tattibaaz",
    "machod","machuda","machudiya",
    "kanjri","kanjari","kanjjar",
    "dalla","dallal","dallabaaz",
    "chamaar","chamar","bhangi","chura",
    "motherfucker","fucker","fuck","fuckr","fuk",
    "bastard","bitch","bitches","biatch",
    "asshole","assh","ass","arse",
    "dick","cock","pussy","cunt","twat",
    "slut","whore","hoe","skank",
    "shit","shitt","sh1t",
    "bsdk","mf","stfu","gtfo",
    "jhantu","jhantoo","jhant",
    "chutmarke","madarjaat","behenchod",
    "teri maa","teri ma","teri behen","teri behan",
    "maa ki aankh","behen ki","maa ka",
    "teri gaand","teri aankh ki",
    "bhad mein jao","bhadme",
    "chutiyap","chutiyapa",
}

def _normalize(text: str) -> str:
    t = {"@":"a","4":"a","!":"i","1":"i","|":"i","0":"o",
         "3":"e","$":"s","5":"s","7":"t","+":"t","(":"c",
         "*":"",".":"","-":"","_":""}
    return "".join(t.get(c, c) for c in text.lower())

def contains_gaali(text: str) -> tuple:
    if not text:
        return False, ""
    orig = text.lower()
    norm = _normalize(text)
    for word in GAALI_LIST:
        if re.search(r'\b' + re.escape(word) + r'\b', orig):
            return True, word
        if len(word) >= 4 and word in norm:
            return True, word
    return False, ""

# ══════════════════════════════════════════════════════════
# ANTI-LINK — catches ALL URLs
# ══════════════════════════════════════════════════════════
_TLDS = (r"com|net|org|io|in|co|me|app|dev|xyz|info|online|site|store|"
         r"shop|club|tv|ly|ai|tech|cc|gg|vip|pro|top|biz|live|news|"
         r"media|click|link|page|website|support|services|solutions|"
         r"ru|uk|us|ca|au|de|fr|jp|pk|bd|sg|my|id|ph|hk|kr|cn|za|"
         r"ng|ke|ma|tn|dz|pk|pw|tk|ml|ga|cf")

_URL_RE = re.compile(
    r"(?i)(?:"
    r"https?://[^\s<>\"'`]{2,}"
    r"|ftp://[^\s<>\"'`]{2,}"
    r"|www\.[^\s<>\"'`]{2,}"
    r"|t\.me/[^\s]+"
    r"|telegram\.me/[^\s]+"
    r"|telegram\.dog/[^\s]+"
    r"|(?:[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]\.)(?:"
    + _TLDS + r")(?:/[^\s]*)?"
    r")"
)
_USERNAME_RE = re.compile(r"@[a-zA-Z][a-zA-Z0-9_]{3,32}")

def has_url(text: str) -> bool:
    return bool(_URL_RE.search(text or ""))

def has_username_promo(text: str, bot_username: str = "") -> bool:
    for m in _USERNAME_RE.findall(text or ""):
        if m.lstrip("@").lower() != bot_username.lower():
            return True
    return False

# ══════════════════════════════════════════════════════════
# CAPTION OBFUSCATION
# ══════════════════════════════════════════════════════════
_SOFT_MAP = {"a":"а","e":"е","o":"о","p":"р","c":"с","x":"х"}
_HARD_CHAR = {
    "a":["@","4","α","𝗮"],"e":["3","£","ε","𝗲"],"i":["!","1","ι","𝗶"],
    "o":["0","ο","σ","𝗼"],"s":["$","5","ƨ","𝘀"],"t":["7","†","τ","𝘁"],
    "n":["ɴ","η","𝗻"],"r":["ʀ","ɾ","𝗿"],"l":["ʟ","|","𝗹"],
    "m":["ɱ","𝗺"],"b":["ʙ","𝗯"],"d":["ᴅ","𝗱"],"h":["ʜ","𝗵"],
    "k":["ᴋ","𝗸"],"v":["ᴠ","𝘃"],"u":["υ","𝘂"],"g":["ɢ","𝗴"],
}
_QUALITY_HARD = {
    "1080p":"1080ᴾ","720p":"720ᴾ","480p":"480ᴾ","4k":"4ᴷ","2160p":"2160ᴾ",
    "hdr":"ʜᴅʀ","hevc":"ʜᴇᴠᴄ","x265":"𝗫265","x264":"𝗫264",
    "webrip":"ᴡᴇʙʀɪᴘ","web-dl":"ᴡᴇʙᴅʟ","bluray":"ʙʟᴜʀᴀʏ","blu-ray":"ʙʟᴜʀᴀʏ",
    "dvdrip":"ᴅᴠᴅʀɪᴘ","hdrip":"ʜᴅʀɪᴘ","hindi":"ʜɪɴᴅɪ","english":"ᴇɴɢ",
    "dual":"ᴅᴜᴀʟ","multi":"ᴍᴜʟᴛɪ","aac":"ᴀᴀᴄ","ac3":"ᴀᴄ3",
    "esub":"ᴇꜱᴜʙ","msub":"ᴍꜱᴜʙ",
}

def obfuscate_caption_soft(caption: str) -> str:
    if not caption:
        return ""
    result = ""
    for ch in caption:
        if ch in _SOFT_MAP and random.random() < 0.35:
            result += _SOFT_MAP[ch]
        else:
            result += ch
    return result

def obfuscate_caption_hard(caption: str) -> str:
    if not caption:
        return ""
    result = caption
    for q, qv in _QUALITY_HARD.items():
        result = re.sub(re.escape(q), qv, result, flags=re.IGNORECASE)
    parts, final = result.split(), []
    for p in parts:
        if any(qv in p for qv in _QUALITY_HARD.values()):
            final.append(p)
        else:
            obf = ""
            for ch in p:
                cl = ch.lower()
                if cl in _HARD_CHAR and random.random() < 0.55:
                    obf += random.choice(_HARD_CHAR[cl])
                else:
                    obf += ch
            final.append(obf)
    return " ".join(final)

# ══════════════════════════════════════════════════════════
# ROAST MESSAGES
# ══════════════════════════════════════════════════════════
_ROAST_MSGS = [
    "😂 Arre hero! File share karna seekh liya par save karna bhool gaya?",
    "🤣 Bhai itna acha content daala aur khud ke liye save nahi kiya? 🤦",
    "😏 File note ho gayi! Save kar le jaldi, warna roo mat baad mein! 😂",
    "🤪 Pehle apne Saved Messages mein bhej, phir share kar! 😂",
    "😂 File daali aur delete bhi hogi — yahi zindagi hai bhai! Save kar le!",
    "🙄 Apne Saved Messages mein bhej pehle, phir share kar! 😂",
    "😜 Jaldi save kar — bhai timeout aa raha hai! ⏰",
]

# ══════════════════════════════════════════════════════════
# MOVIE FILE HANDLER (PREMIUM)
# ══════════════════════════════════════════════════════════
async def movie_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message  = update.effective_message
    chat     = update.effective_chat
    user     = update.effective_user

    if not message or not user or chat.type == "private":
        return
    if not (message.document or message.video):
        return

    # ── Check premium and setting ──────────────────────────
    if not is_premium(chat.id):
        return
    if not get_setting(chat.id, "movie_on", True):
        return

    file_obj  = message.document or message.video
    is_doc    = bool(message.document)
    file_id   = file_obj.file_id
    unique_id = file_obj.file_unique_id
    original_caption = message.caption or ""
    caption_mode = get_setting(chat.id, "movie_caption_mode", "hard")

    # ══ FIX 1: DUPLICATE CHECK FIRST ══════════════════════
    # Prevents double-send when Telegram retries webhook
    existing = find_file_by_unique_id(unique_id)
    if existing:
        # Already processed — silently delete the duplicate user message
        try:
            await message.delete()
        except Exception:
            pass
        return  # DO NOT send again

    # ── Store hash IMMEDIATELY (before any network calls) ──
    # This acts as a lock — if webhook is retried, second call
    # finds the hash and returns above without double-sending
    store_file_hash(chat.id, unique_id, file_id, original_caption, user.id)

    # ── Build obfuscated caption ───────────────────────────
    if caption_mode == "off":
        new_caption = original_caption or None
    elif caption_mode == "soft":
        new_caption = obfuscate_caption_soft(original_caption) or None
    else:
        new_caption = obfuscate_caption_hard(original_caption) or None

    # ── STEP 1: Forward ORIGINAL to log channel ───────────
    if FILE_LOG_CHANNEL:
        try:
            await context.bot.forward_message(
                chat_id=int(FILE_LOG_CHANNEL),
                from_chat_id=chat.id,
                message_id=message.message_id,
            )
            await context.bot.send_message(
                int(FILE_LOG_CHANNEL),
                f"📁 <b>File Log</b>\n"
                f"👤 {user.full_name} (<code>{user.id}</code>)\n"
                f"👥 {chat.title} (<code>{chat.id}</code>)\n"
                f"📋 Caption: <code>{(original_caption or 'None')[:200]}</code>\n"
                f"🆔 UniqueID: <code>{unique_id}</code>\n"
                f"🎨 Mode: {caption_mode.upper()}",
                parse_mode="HTML",
            )
        except Exception as e:
            print(f"[LOG] {e}")

    # ── STEP 2: Delete original from group ────────────────
    deleted = False
    try:
        await message.delete()
        deleted = True
    except Exception as del_err:
        print(f"[MOVIE] Delete failed: {del_err}")

    # ══ FIX 2: IF DELETE FAILS → ABORT ══════════════════
    # Bot doesn't have delete permission — sending new file
    # would cause TWO files visible in group
    if not deleted:
        await context.bot.send_message(
            chat.id,
            "⚠️ <b>Bot ko 'Delete Messages' admin permission chahiye!</b>\n\n"
            "Bina delete permission ke file system kaam nahi kar sakta.\n"
            "Bot ko admin banao aur 'Delete Messages' permission do.",
            parse_mode="HTML",
        )
        return

    # ── STEP 3: Send obfuscated version to group ──────────
    try:
        send_kwargs = dict(chat_id=chat.id, protect_content=True)
        if new_caption:
            send_kwargs["caption"] = new_caption

        if is_doc:
            sent = await context.bot.send_document(document=file_id, **send_kwargs)
        else:
            sent = await context.bot.send_video(video=file_id, **send_kwargs)

        # ── STEP 4: Deletion warning + roast ─────────────
        if get_setting(chat.id, "autodel_on", False):
            del_secs  = get_setting(chat.id, "autodel_time", 3600)
            delete_at = datetime.now() + timedelta(seconds=del_secs)
            schedule_delete(chat.id, sent.message_id, delete_at)

            hours = del_secs // 3600
            mins  = (del_secs % 3600) // 60
            if hours and mins:
                readable = f"{hours}h {mins}m"
            elif hours:
                readable = f"{hours} ghante"
            else:
                readable = f"{mins} minute"

            del_time_str = delete_at.strftime("%I:%M %p")
            roast = random.choice(_ROAST_MSGS)

            await context.bot.send_message(
                chat.id,
                f"⚠️ <b>Jaldi Save Karo!</b>\n\n"
                f"🕐 Yeh file <b>{readable}</b> baad delete hogi\n"
                f"⏰ Delete time: <b>{del_time_str}</b>\n\n"
                f"💾 <b>Saved Messages mein save karo abhi!</b>\n\n"
                f"🤣 {roast}",
                parse_mode="HTML",
            )

    except Exception as e:
        print(f"[MOVIE] Send error: {e}")

# ══════════════════════════════════════════════════════════
# AUTO-MOD HELPERS
# ══════════════════════════════════════════════════════════
async def _del_notify(context, chat_id, msg, text, delay=6):
    try:
        await msg.delete()
    except Exception:
        pass
    try:
        n = await context.bot.send_message(chat_id, text, parse_mode="HTML")
        await asyncio.sleep(delay)
        await n.delete()
    except Exception:
        pass

async def _apply_gaali_punishment(context, chat_id, user, strikes, message):
    try:
        await message.delete()
    except Exception:
        pass
    if strikes == 1:
        reply = make_gaali_reply(chat_id)
        n = await context.bot.send_message(
            chat_id,
            f"⚠️ {user.mention_html()} — <b>Pehli warning!</b>\n\n"
            f"{reply}\n\n<i>Dobara mat karna, muting hogi!</i>",
            parse_mode="HTML",
        )
        await asyncio.sleep(10)
        try:
            await n.delete()
        except Exception:
            pass
    elif strikes == 2:
        until = datetime.now() + timedelta(hours=1)
        try:
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
        except Exception:
            pass
        n = await context.bot.send_message(
            chat_id,
            f"🔇 {user.mention_html()} — <b>2nd gaali! 1 ghante muted!</b>\n"
            f"<i>Teesri baar permanent ban!</i>",
            parse_mode="HTML",
        )
        await asyncio.sleep(10)
        try:
            await n.delete()
        except Exception:
            pass
    else:
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            reset_gaali_strikes(chat_id, user.id)
        except Exception:
            pass
        n = await context.bot.send_message(
            chat_id,
            f"🔨 {user.mention_html()} — <b>Permanently banned!</b>\n"
            f"<i>Baar baar gaali allowed nahi!</i>",
            parse_mode="HTML",
        )
        await asyncio.sleep(8)
        try:
            await n.delete()
        except Exception:
            pass

# ══════════════════════════════════════════════════════════
# CAPTCHA CALLBACK
# ══════════════════════════════════════════════════════════
async def captcha_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    data    = query.data
    chat    = query.message.chat
    clicker = query.from_user

    parts = data.split("_")
    if len(parts) < 3:
        return
    target_uid = int(parts[1])
    chosen_ans = parts[2]

    if clicker.id != target_uid:
        await query.answer("Yeh tumhara captcha nahi! 😤", show_alert=True)
        return

    captcha = get_captcha(chat.id, target_uid)
    if not captcha:
        await query.answer("Captcha expire ho gaya!", show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if chosen_ans == captcha["answer"]:
        try:
            await context.bot.restrict_chat_member(
                chat.id, target_uid,
                permissions=ChatPermissions(
                    can_send_messages=True, can_send_media_messages=True,
                    can_send_other_messages=True, can_add_web_page_previews=True,
                ),
            )
        except Exception:
            pass
        del_captcha(chat.id, target_uid)
        await query.answer("✅ Sahi jawab! Welcome!")
        try:
            await query.edit_message_text(
                f"✅ {clicker.mention_html()} ne captcha pass kar liya! Welcome~ 🌸",
                parse_mode="HTML",
            )
        except Exception:
            pass
    else:
        await query.answer("❌ Galat jawab! Bye!", show_alert=True)
        del_captcha(chat.id, target_uid)
        try:
            await context.bot.ban_chat_member(chat.id, target_uid)
            await asyncio.sleep(1)
            await context.bot.unban_chat_member(chat.id, target_uid)
            await query.edit_message_text(
                f"❌ {clicker.full_name} captcha fail — <b>Kicked!</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass

# ══════════════════════════════════════════════════════════
# MAIN MESSAGE HANDLER
# ══════════════════════════════════════════════════════════
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat

    if not message or not user or user.is_bot:
        return
    if is_blocked(user.id):
        return

    # ══ FIX 3: Skip document/video/audio in GROUPS ════════
    # movie_file_handler already handles those
    # Without this, chatbot replies to file captions in groups
    if chat.type != "private":
        if (message.document or message.video or
                message.audio or message.voice or
                message.animation or message.sticker):
            return  # Not for this handler

    text = message.text or message.caption or ""

    # Save user + analytics
    save_user(user)
    if chat.type != "private":
        save_active_member(chat.id, user.id)
        inc_message_count(chat.id, user.id)
        if text:
            save_message(chat.id, user.id, text)
            push_context(chat.id, user.first_name, text)

    # Admin self-reply learning
    if (user.id == ADMIN_ID and message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == ADMIN_ID and text):
        rt = message.reply_to_message.text or message.reply_to_message.caption or ""
        if rt:
            from core.brain import learn_from_reply
            if learn_from_reply(rt, text, ADMIN_ID):
                await message.reply_text("✅ Seekh liya~ 🧠💘")
                return

    # ── PM handling ────────────────────────────────────────
    if chat.type == "private":
        from handlers.admin import pm_premium_conversation
        handled = await pm_premium_conversation(update, context)
        if handled:
            return
        if text:
            reply = make_girl_reply(text, chat_id=chat.id, user_name=user.first_name)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
            await asyncio.sleep(random.uniform(0.8, 2.0))
            await message.reply_text(reply)
        return

    # ── Notes auto-reply (#notename) ───────────────────────
    if text and text.startswith("#"):
        note_name = text[1:].strip().lower().split()[0]
        if note_name:
            note = get_note(chat.id, note_name)
            if note:
                await message.reply_text(note["content"], parse_mode="HTML")
                return

    # ── Conversation learning ──────────────────────────────
    if text and message.reply_to_message and message.reply_to_message.from_user:
        ru = message.reply_to_message.from_user
        rt = message.reply_to_message.text or message.reply_to_message.caption or ""
        if rt:
            if ru.id == context.bot.id:
                learn_from_bot_reply(rt, text)
            elif ru.id != user.id:
                learn_from_conversation(rt, text, ru.id, user.id)

    # ── Admin status check ─────────────────────────────────
    user_is_admin = (user.id == ADMIN_ID)
    if not user_is_admin:
        try:
            m = await context.bot.get_chat_member(chat.id, user.id)
            user_is_admin = m.status in ("administrator", "creator")
        except Exception:
            pass

    # ══ FREE FEATURES ══════════════════════════════════════

    # Anti-Gaali (FREE)
    if get_setting(chat.id, "antigaali_on", False) and not user_is_admin:
        found, _ = contains_gaali(text)
        if found:
            strikes = inc_gaali_strike(chat.id, user.id)
            await _apply_gaali_punishment(context, chat.id, user, strikes, message)
            return

    # Anti-Username @ promo (FREE)
    if get_setting(chat.id, "antiusername_on", False) and not user_is_admin:
        bot_me = await context.bot.get_me()
        if has_username_promo(text, bot_me.username):
            await _del_notify(
                context, chat.id, message,
                f"📢 {user.mention_html()} — <b>@Username promotion nahi!</b> 🚫",
            )
            return

    # ══ PREMIUM FEATURES ═══════════════════════════════════

    if is_premium(chat.id) and not user_is_admin:

        # Anti-Link (ALL URLs)
        if get_setting(chat.id, "antilink_on", False):
            if has_url(text):
                await _del_notify(
                    context, chat.id, message,
                    f"🔗 {user.mention_html()} — <b>Links allowed nahi!</b> 🚫",
                )
                return

        # Anti-Forward
        if get_setting(chat.id, "antifwd_on", False):
            if message.forward_from or message.forward_from_chat:
                await _del_notify(
                    context, chat.id, message,
                    f"↪️ {user.mention_html()} — <b>Forwarded messages nahi!</b> 🚫",
                )
                return

        # Lock types
        locked = get_setting(chat.id, "locked_types", []) or []
        if locked:
            msg_type = None
            if message.poll:   msg_type = "polls"
            if msg_type and msg_type in locked:
                try:
                    await message.delete()
                except Exception:
                    pass
                return

        # Flood control
        if get_setting(chat.id, "flood_on", False):
            flood_limit = get_setting(chat.id, "flood_limit", 5)
            if is_flooding(chat.id, user.id, limit=flood_limit, window=10):
                try:
                    until = datetime.now() + timedelta(minutes=5)
                    await context.bot.restrict_chat_member(
                        chat.id, user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until,
                    )
                    n = await context.bot.send_message(
                        chat.id,
                        f"⚡ {user.mention_html()} — <b>Flood! 5 min muted</b> 🔇",
                        parse_mode="HTML",
                    )
                    await asyncio.sleep(8)
                    try:
                        await n.delete()
                    except Exception:
                        pass
                except Exception:
                    pass
                return

    # ══ CHATBOT ════════════════════════════════════════════

    if not get_setting(chat.id, "chat_bot_on", True):
        return

    # ══ FIX 4: Only reply to TEXT messages in groups ═══════
    # Don't reply to photo captions etc unless directly mentioned
    is_text_msg = bool(message.text)
    text_lower  = text.lower() if text else ""
    mentioned   = any(t in text_lower for t in BOT_TRIGGERS)
    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == context.bot.id
    )
    should_reply = mentioned or replied_to_bot

    # Random chatbot trigger — ONLY for pure text messages
    if not should_reply and is_text_msg and len(text) > 3:
        should_reply = random.random() < 0.10

    if not should_reply:
        return

    gaali_found, _ = contains_gaali(text)
    if gaali_found:
        reply = make_gaali_reply(chat.id)
    else:
        reply = make_girl_reply(text, chat_id=chat.id, user_name=user.first_name)
        if not reply:
            reply = make_girl_reply(chat_id=chat.id)

    delay = min(0.8 + len(text) * 0.03, 3.0)
    await asyncio.sleep(random.uniform(delay * 0.6, delay))
    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    try:
        await message.reply_text(reply)
        if should_send_sticker():
            sticker_id = get_sticker("happy")
            try:
                await asyncio.sleep(0.5)
                await message.reply_sticker(sticker_id)
            except Exception:
                pass
    except Exception as e:
        print(f"[CHAT] {e}")
