import os, re, asyncio, random, string
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from core.db import (
    save_user, save_message, is_blocked, get_setting, is_premium,
    save_sticker, get_stickers,
    is_flooding, schedule_delete, save_active_member, inc_message_count,
    push_context, get_gaali_strikes, inc_gaali_strike, reset_gaali_strikes,
    store_file_hash, find_file_by_unique_id, get_note, get_all_notes,
    record_raid_join, detect_raid, add_warn, get_warns, reset_warns,
    get_captcha, del_captcha,
    # NEW additions
    save_movie_request, get_requesters_today,
    save_forward_cache, get_forward_cache,
    has_bio_perm, grant_bio_perm,
    get_captcha_token_doc, del_captcha_token, set_captcha_token,
    get_global_stickers, save_global_stickers,
)
from core.brain import (
    make_girl_reply, make_gaali_reply,
    learn_from_conversation, learn_from_bot_reply,
)
from core.persona import BOT_TRIGGERS, get_sticker, should_send_sticker

ADMIN_ID         = int(os.environ.get("ADMIN_ID", "0"))
FILE_LOG_CHANNEL = os.environ.get("FILE_LOG_CHANNEL", "")
FORWARD_CHANNEL  = os.environ.get("FORWARD_CHANNEL", "")   # separate channel for file cache

# In-memory bio check cache: user_id → (has_links: bool, checked_at: datetime)
_bio_cache: dict = {}
BIO_CACHE_TTL = 3600  # 1 hour

# In-memory dedup: last N bot messages per chat to prevent repetition
_last_bot_msgs: dict = {}  # chat_id → [last 5 replies]

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

async def _check_bio_links(context, user, bot_username: str = "") -> bool:
    """Check if user's bio contains links/usernames. Cached 1hr."""
    now = datetime.now()
    cached = _bio_cache.get(user.id)
    if cached:
        result, checked_at = cached
        if (now - checked_at).total_seconds() < BIO_CACHE_TTL:
            return result
    try:
        user_chat = await context.bot.get_chat(user.id)
        bio = user_chat.bio or ""
        has_link = has_url(bio) or has_username_promo(bio, bot_username)
        _bio_cache[user.id] = (has_link, now)
        return has_link
    except Exception:
        return False

def _is_bot_reply_duplicate(chat_id: int, reply_text: str) -> bool:
    """Check if bot already sent this exact reply recently in this chat."""
    last_msgs = _last_bot_msgs.get(chat_id, [])
    return reply_text in last_msgs

def _record_bot_reply(chat_id: int, reply_text: str):
    """Track last 5 bot replies per chat for dedup."""
    if chat_id not in _last_bot_msgs:
        _last_bot_msgs[chat_id] = []
    _last_bot_msgs[chat_id].append(reply_text)
    _last_bot_msgs[chat_id] = _last_bot_msgs[chat_id][-5:]

# ══════════════════════════════════════════════════════════
# CAPTION BUILDER — SOFT & HARD
# ══════════════════════════════════════════════════════════

# ── HARD mode: Mixed stylish Unicode + look-alike symbols ──
_HARD_TITLE_MAP = {
    'A': ['𝑨', '@', '4'],
    'B': ['𝑩'],
    'C': ['𝑪', '¢'],
    'D': ['𝑫'],
    'E': ['𝑬', '€', '3'],
    'F': ['𝑭'],
    'G': ['𝑮', '9'],
    'H': ['𝑯'],
    'I': ['𝑰', '¡', '!'],
    'J': ['𝑱'],
    'K': ['𝑲'],
    'L': ['𝑳', '|'],
    'M': ['𝑴'],
    'N': ['𝑵'],
    'O': ['O', '0'],
    'P': ['𝑷', '₱'],
    'Q': ['𝑸'],
    'R': ['𝑹', '₹'],
    'S': ['𝑺', '$'],
    'T': ['𝑻', '†'],
    'U': ['𝑼', 'υ'],
    'V': ['𝑽', '√'],
    'W': ['𝑾'],
    'X': ['𝑿', '×'],
    'Y': ['𝒀', '¥'],
    'Z': ['𝒁', '2'],
    '0': ['O', '0'],
    '1': ['1', '|'],
    '2': ['2'],
    '3': ['3'],
    '4': ['4'],
    '5': ['5', '$'],
    '6': ['6'],
    '7': ['7'],
    '8': ['8'],
    '9': ['9'],
}

# For quality labels: replace vowels + common letters with symbols
_QUAL_CHAR_MAP = {
    'a': "'", 'e': '€', 'i': "'", 'o': 'O', 'u': 'υ',
    'A': '@', 'E': '€', 'I': '¡', 'O': 'O', 'U': 'υ',
    'l': '|', 'L': '|', 'r': '₹', 'R': '₹',
    '0': 'O',
}

def _obf_title(text: str) -> str:
    """Obfuscate movie title: mix italic bold + look-alike symbols."""
    result = ""
    for ch in text.upper():
        opts = _HARD_TITLE_MAP.get(ch, [ch])
        result += random.choice(opts)
    return result

def _obf_year(year: str) -> str:
    """Obfuscate year: 0→O."""
    return year.replace('0', 'O')

def _obf_quality_label(text: str) -> str:
    """Partially obfuscate quality labels."""
    result = ""
    for ch in text:
        result += _QUAL_CHAR_MAP.get(ch, ch)
    return result

_QUALITY_LABELS = [
    ("4K",     r"\b(4[Kk]|2160[Pp])\b"),
    ("1080P",  r"\b1080[Pp]\b"),
    ("720P",   r"\b720[Pp]\b"),
    ("480P",   r"\b480[Pp]\b"),
    ("BluRay", r"\b(blu.?ray|bluray)\b"),
    ("WEBRip", r"\b(web.?rip|webrip)\b"),
    ("WEB-DL", r"\b(web.?dl|webdl)\b"),
    ("HEVC",   r"\b(hevc|x265|h\.?265)\b"),
    ("x264",   r"\b(x264|h\.?264)\b"),
    ("HDR",    r"\bhdr\b"),
    ("Hindi",  r"\bhindi\b"),
    ("Dual",   r"\bdual\b"),
    ("Multi",  r"\bmulti\b"),
    ("ESub",   r"\besub\b"),
]

def _extract_info(raw: str):
    """Return (movie_name, year, [qualities]) from raw caption."""
    # Strip URLs first
    clean = _URL_RE.sub("", raw or "").strip()
    # Replace dots/underscores with space
    clean = re.sub(r"[._]", " ", clean)
    # Extract year
    year_m = re.search(r"\b(19|20)\d{2}\b", clean)
    year   = year_m.group() if year_m else ""
    # Extract qualities
    quals = [label for label, pat in _QUALITY_LABELS if re.search(pat, clean, re.I)]
    # Extract name: everything before year or first quality word
    name = clean
    if year:
        name = clean[:year_m.start()].strip()
    else:
        for _, pat in _QUALITY_LABELS:
            m2 = re.search(pat, name, re.I)
            if m2:
                name = name[:m2.start()].strip()
                break
    name = re.sub(r"\s+", " ", name).strip() or clean[:30]
    return name, year, quals

def obfuscate_caption_soft(raw: str, del_info: str = "") -> str:
    """SOFT: Clean readable caption with light formatting."""
    name, year, quals = _extract_info(raw)
    yr_str = f" ({year})" if year else ""
    q_str  = " • ".join(quals[:3]) if quals else ""
    lines  = [f"🎬 {name}{yr_str}"]
    if q_str:
        lines.append(f"📊 {q_str}")
    lines.append("━━━━━━━━━━━━━━━━━━━")
    lines.append("⛔ Forward Prohibited")
    if del_info:
        lines.append(f"⏰ {del_info}")
    return "\n".join(lines)

def obfuscate_caption_hard(raw: str, bot_uname: str = "", del_info: str = "") -> str:
    """HARD: Ultra obfuscated title (mixed unicode+symbols) + no copyright line."""
    name, year, quals = _extract_info(raw)

    # Obfuscate title and year
    obf_title = _obf_title(name)
    obf_year  = f" ({_obf_year(year)})" if year else ""

    # Obfuscate each quality label
    obf_quals = " • ".join(_obf_quality_label(q) for q in quals[:4]) if quals else ""

    lines = [
        f"꧁✨ {obf_title}{obf_year} ✨꧂",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    if obf_quals:
        lines.append(f"📊 {obf_quals}")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("⛔ Forward/Share Prohibited")
    if del_info:
        lines.append(f"⏰ {del_info}")
    if bot_uname:
        lines.append(f"🤖 {bot_uname}")
    return "\n".join(lines)

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

    # ══ DUPLICATE CHECK ══════════════════════════════════
    existing = find_file_by_unique_id(unique_id)
    if existing:
        try:
            await message.delete()
        except Exception:
            pass
        return

    store_file_hash(chat.id, unique_id, file_id, original_caption, user.id)

    # ── Get bot info ──────────────────────────────────────
    bot_me    = await context.bot.get_me()
    bot_uname = f"@{bot_me.username}" if bot_me.username else ""

    # ── Extract movie name for cache key ──────────────────
    movie_name, _, _ = _extract_info(original_caption)
    caption_key = movie_name.lower().strip()[:50] if movie_name else unique_id

    # ── Check FORWARD_CHANNEL cache (use cached file if available) ─
    cached = get_forward_cache(caption_key) if caption_key else None
    if cached and cached.get("file_id"):
        use_file_id = cached["file_id"]
        use_is_doc  = cached.get("is_doc", is_doc)
        print(f"[MOVIE] Using cached file for '{caption_key}'")
    else:
        use_file_id = file_id
        use_is_doc  = is_doc

    # ── Get today's requesters for tagging ────────────────
    requesters = get_requesters_today(chat.id, caption_key) if caption_key else []
    # Filter out the uploader
    requesters = [r for r in requesters if r["user_id"] != user.id]

    # ── Build del_info ────────────────────────────────────
    del_info = ""
    del_secs = 0
    delete_time_str = ""
    if get_setting(chat.id, "autodel_on", False):
        del_secs  = get_setting(chat.id, "autodel_time", 3600)
        hours     = del_secs // 3600
        mins      = (del_secs % 3600) // 60
        readable  = f"{hours}h {mins}m" if (hours and mins) else (f"{hours}h" if hours else f"{mins}m")
        delete_at = datetime.now() + timedelta(seconds=del_secs)
        delete_time_str = delete_at.strftime("%H:%M")
        del_info  = f"⏰ {delete_time_str} pe delete hogi — abhi Save karo!"

    # ── Build caption with tags ───────────────────────────
    if caption_mode == "off":
        base_caption = _URL_RE.sub("", original_caption).strip() or ""
    elif caption_mode == "soft":
        base_caption = obfuscate_caption_soft(original_caption, del_info)
    else:
        base_caption = obfuscate_caption_hard(original_caption, bot_uname, del_info)

    # Add requester tags
    tag_line = ""
    if requesters:
        tags = "".join(
            f'<a href="tg://user?id={r["user_id"]}">{r["user_name"]}</a> '
            for r in requesters[:6]
        )
        tag_line = f"\n\n🔔 {tags}"

    if del_info and caption_mode != "off" and delete_time_str:
        save_reminder = f"\n\n⚠️ Ye file {delete_time_str} tak group mein rahegi!\nApne Saved Messages mein save karo!"
    else:
        save_reminder = ""

    new_caption = (base_caption + tag_line + save_reminder).strip()[:1024] or None

    # ── STEP 1: Forward to FILE_LOG_CHANNEL ───────────────
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
                f"🔑 Key: <code>{caption_key}</code>\n"
                f"🎨 Mode: {caption_mode.upper()}",
                parse_mode="HTML",
            )
        except Exception as e:
            print(f"[LOG] {e}")

    # ── STEP 2: Forward to FORWARD_CHANNEL (cache) ────────
    if FORWARD_CHANNEL and not cached:
        try:
            await context.bot.copy_message(
                chat_id=int(FORWARD_CHANNEL),
                from_chat_id=chat.id,
                message_id=message.message_id,
            )
            # Cache this file
            save_forward_cache(caption_key, unique_id, file_id, is_doc)
            print(f"[MOVIE] Cached file to FORWARD_CHANNEL: '{caption_key}'")
        except Exception as e:
            print(f"[FWD_CHANNEL] {e}")

    # ── STEP 3: Delete original from group ────────────────
    deleted = False
    try:
        await message.delete()
        deleted = True
    except Exception as del_err:
        print(f"[MOVIE] Delete failed: {del_err}")

    if not deleted:
        await context.bot.send_message(
            chat.id,
            "⚠️ <b>Bot ko 'Delete Messages' admin permission chahiye!</b>\n\n"
            "Bina delete permission ke Movie System kaam nahi kar sakta.\n"
            "Bot ko admin banao → Delete Messages permission do.",
            parse_mode="HTML",
        )
        return

    # ── STEP 4: Send clean version to group ──────────────
    # protect_content=False — users can forward freely ✅
    try:
        send_kwargs = dict(chat_id=chat.id, parse_mode="HTML")
        if new_caption:
            send_kwargs["caption"] = new_caption

        if use_is_doc:
            sent = await context.bot.send_document(document=use_file_id, **send_kwargs)
        else:
            sent = await context.bot.send_video(video=use_file_id, **send_kwargs)

        # ── STEP 5: Schedule deletion ─────────────────────
        if del_secs > 0:
            delete_at = datetime.now() + timedelta(seconds=del_secs)
            schedule_delete(chat.id, sent.message_id, delete_at)

    except Exception as e:
        print(f"[MOVIE] Send error: {e}")

# ══════════════════════════════════════════════════════════
# AUTO-MOD HELPERS
# ══════════════════════════════════════════════════════════
async def _del_notify(context, chat_id, msg, text, target_uid=None, delay=6):
    """Delete offending msg + send warning with Dismiss/action buttons."""
    try:
        await msg.delete()
    except Exception:
        pass
    # Build buttons
    btns = []
    if target_uid:
        btns.append([
            InlineKeyboardButton("🔇 Mute", callback_data=f"warn_mute_{target_uid}_3600"),
            InlineKeyboardButton("⛔ Ban",   callback_data=f"warn_ban_{target_uid}"),
        ])
    btns.append([InlineKeyboardButton("✅ Dismiss", callback_data="automod_dismiss")])
    markup = InlineKeyboardMarkup(btns)
    try:
        await context.bot.send_message(
            chat_id, text, parse_mode="HTML", reply_markup=markup
        )
    except Exception:
        pass

async def _apply_gaali_punishment(context, chat_id, user, strikes, message):
    try:
        await message.delete()
    except Exception:
        pass
    btns_dismiss = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔇 Mute 1h", callback_data=f"warn_mute_{user.id}_3600"),
        InlineKeyboardButton("⛔ Ban",     callback_data=f"warn_ban_{user.id}"),
        InlineKeyboardButton("✅ Dismiss", callback_data="automod_dismiss"),
    ]])
    if strikes == 1:
        reply = make_gaali_reply(chat_id)
        await context.bot.send_message(
            chat_id,
            f"⚠️ {user.mention_html()} — <b>Pehli gaali warning!</b>\n\n"
            f"{reply}\n\n<i>Dobara mat karna, muting hogi! (1/3)</i>",
            parse_mode="HTML",
            reply_markup=btns_dismiss,
        )
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
        await context.bot.send_message(
            chat_id,
            f"🔇 {user.mention_html()} — <b>2nd gaali! 1 ghante muted!</b>\n"
            f"<i>Teesri baar permanent ban! (2/3)</i>",
            parse_mode="HTML",
            reply_markup=btns_dismiss,
        )
    else:
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            reset_gaali_strikes(chat_id, user.id)
        except Exception:
            pass
        await context.bot.send_message(
            chat_id,
            f"🔨 {user.mention_html()} — <b>Permanently banned!</b>\n"
            f"<i>Baar baar gaali — ban liya! (3/3)</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔓 Unban",  callback_data=f"unban_{user.id}"),
                InlineKeyboardButton("✅ Dismiss", callback_data="automod_dismiss"),
            ]]),
        )

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
            # Track as potential movie request (used to tag users when file arrives)
            if len(text) >= 2 and not text.startswith("/"):
                save_movie_request(chat.id, user.id, user.first_name, text)

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
        # Owner sends sticker in PM → save entire sticker pack globally
        if user.id == ADMIN_ID and message.sticker:
            sticker = message.sticker
            if sticker.set_name:
                await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
                sticker_set = await context.bot.get_sticker_set(sticker.set_name)
                file_ids = [s.file_id for s in sticker_set.stickers]
                save_global_stickers(file_ids)
                await message.reply_text(
                    f"✅ <b>Sticker Pack Saved!</b>\n\n"
                    f"📦 Pack: {sticker_set.title}\n"
                    f"🎭 Total stickers: {len(file_ids)}\n\n"
                    f"Bot group replies mein yahi stickers use karega! 🌸",
                    parse_mode="HTML",
                )
            else:
                save_global_stickers([sticker.file_id])
                await message.reply_text("✅ Single sticker saved globally! 🎭")
            return
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

    # ── Captcha token verification ──────────────────────────
    # New PM-based captcha: user sends 6-char code in group
    if text and re.match(r'^[A-Z0-9]{6}$', text.strip().upper()):
        token = text.strip().upper()
        token_doc = get_captcha_token_doc(chat.id, user.id)
        if token_doc and token_doc.get("token") == token:
            expires = token_doc.get("expires_at")
            if expires and expires > datetime.now():
                cap_msg_id = token_doc.get("msg_id")
                del_captcha_token(chat.id, user.id)
                del_captcha(chat.id, user.id)
                # Unrestrict user
                try:
                    await context.bot.restrict_chat_member(
                        chat.id, user.id,
                        permissions=ChatPermissions(
                            can_send_messages=True, can_send_media_messages=True,
                            can_send_other_messages=True, can_add_web_page_previews=True,
                        ),
                    )
                except Exception:
                    pass
                # Delete their code message + captcha message
                try: await message.delete()
                except Exception: pass
                if cap_msg_id:
                    try: await context.bot.delete_message(chat.id, cap_msg_id)
                    except Exception: pass
                # Show welcome message
                if get_setting(chat.id, "welcome_on", True):
                    from core.persona import get_welcome
                    custom = get_setting(chat.id, "welcome_msg", None)
                    wtext = (
                        custom.replace("{name}", user.mention_html()).replace("{group}", chat.title or "")
                        if custom else get_welcome(user.mention_html())
                    )
                    await context.bot.send_message(chat.id, wtext, parse_mode="HTML")
                return

    # ── Notes auto-reply (#notename) ───────────────────────
    if text and text.startswith("#"):
        note_name = text[1:].strip().lower().split()[0]
        if note_name:
            note = get_note(chat.id, note_name)
            if note:
                await message.reply_text(note["content"], parse_mode="HTML")
                return

    # ── Sticker save mode ──────────────────────────────────
    if chat.type != "private" and message.sticker:
        if get_setting(chat.id, "sticker_pending", False):
            if await _is_user_admin(context, chat.id, user.id):
                save_sticker(chat.id, message.sticker.file_id)
                await message.reply_text("✅ Sticker saved! Aur bhejo ya /stickerdone karo.")
                return

    # ── Filter auto-reply ───────────────────────────────────
    if chat.type != "private" and text:
        from handlers.filters import check_and_reply_filter
        filter_hit = await check_and_reply_filter(update, context)
        if filter_hit:
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

        # Bio Link Check (PREMIUM) — antibio_on setting
        if get_setting(chat.id, "antibio_on", False):
            if not has_bio_perm(chat.id, user.id):
                _bot_me = await context.bot.get_me()
                bio_has_link = await _check_bio_links(context, user, _bot_me.username or "")
                if bio_has_link:
                    try: await message.delete()
                    except Exception: pass
                    await context.bot.send_message(
                        chat.id,
                        f"⚠️ {user.mention_html()} — <b>Bio mein link/username hai!</b>\n\n"
                        f"Message karne ke 2 raaste:\n"
                        f"1️⃣ Apni bio se link/username hatao\n"
                        f"2️⃣ Admin se /biofree permission lo\n\n"
                        f"<i>Abhi messaging band hai.</i>",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔓 /biofree dena hai?", callback_data=f"biofree_prompt_{user.id}"),
                            InlineKeyboardButton("✅ Dismiss", callback_data="automod_dismiss"),
                        ]]),
                    )
                    return

        # Anti-Link (ALL URLs)
        if get_setting(chat.id, "antilink_on", False):
            if has_url(text):
                await _del_notify(
                    context, chat.id, message,
                    f"🔗 {user.mention_html()} — <b>Links allowed nahi!</b> 🚫",
                    target_uid=user.id,
                )
                return

        # Anti-Forward
        if get_setting(chat.id, "antifwd_on", False):
            if message.forward_from or message.forward_from_chat:
                await _del_notify(
                    context, chat.id, message,
                    f"↪️ {user.mention_html()} — <b>Forwarded messages nahi!</b> 🚫",
                    target_uid=user.id,
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
                    await context.bot.send_message(
                        chat.id,
                        f"⚡ {user.mention_html()} — <b>Flood! 5 min muted</b> 🔇",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔊 Unmute",  callback_data=f"unmute_{user.id}"),
                            InlineKeyboardButton("✅ Dismiss", callback_data="automod_dismiss"),
                        ]]),
                    )
                except Exception:
                    pass
                return

    # ══ CHATBOT ════════════════════════════════════════════

    if not get_setting(chat.id, "chat_bot_on", True):
        return

    # ══ FIXED REPLY LOGIC ════════════════════════════════
    # 1. User replying to ANOTHER user → NEVER interrupt their convo
    # 2. User replying to BOT           → 30% chance respond
    # 3. Standalone message (no reply)  → 10% chance respond
    is_text_msg = bool(message.text)
    text_lower  = text.lower() if text else ""

    if not is_text_msg or len(text) < 2:
        return

    mentioned  = any(t in text_lower for t in BOT_TRIGGERS)
    reply_to   = message.reply_to_message
    reply_user = reply_to.from_user if reply_to else None

    if reply_user:
        if reply_user.id == context.bot.id:
            # User replied to bot directly
            should_reply = random.random() < 0.30
        else:
            # User replying to another user — bot stays out
            should_reply = False
    elif mentioned:
        # Someone tagged/mentioned bot triggers
        should_reply = random.random() < 0.30
    else:
        # Pure standalone message — 10% chance
        should_reply = random.random() < 0.10

    if not should_reply:
        return

    # ── Dedup: don't repeat same reply twice in a row ──────
    gaali_found, _ = contains_gaali(text)
    if gaali_found:
        reply = make_gaali_reply(chat.id)
    else:
        reply = make_girl_reply(text, chat_id=chat.id, user_name=user.first_name)
        if not reply:
            reply = make_girl_reply(chat_id=chat.id)

        if not reply:
            try:
                import os as _os
                if _os.environ.get("USERBOT_SESSION"):
                    from core.userbot import search_group_reply
                    reply = await search_group_reply(text)
            except Exception as _ube:
                print(f"[USERBOT FALLBACK] {_ube}")

    if not reply:
        return

    # Skip if same as recent bot message (anti-spam)
    if _is_bot_reply_duplicate(chat.id, reply):
        return
    _record_bot_reply(chat.id, reply)

    # ── Typing delay (feels natural) ──────────────────────
    delay = min(0.8 + len(text) * 0.03, 3.0)
    await asyncio.sleep(random.uniform(delay * 0.6, delay))
    await context.bot.send_chat_action(chat.id, ChatAction.TYPING)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    try:
        await message.reply_text(reply)

        # ── Sticker after reply — try global pack first, then per-chat ──
        global_stickers = get_global_stickers()
        saved_stickers  = get_stickers(chat.id)
        all_stickers    = global_stickers + saved_stickers
        if all_stickers and random.random() < 0.20:
            try:
                await asyncio.sleep(0.4)
                await message.reply_sticker(random.choice(all_stickers))
            except Exception:
                pass
        elif should_send_sticker():
            sticker_id = get_sticker("happy")
            try:
                await asyncio.sleep(0.5)
                await message.reply_sticker(sticker_id)
            except Exception:
                pass
    except Exception as e:
        print(f"[CHAT] {e}")

# ══════════════════════════════════════════════════════════
# EDITED MESSAGE HANDLER (PREMIUM)
# Delete any message a user edits — prevents bypass
# ══════════════════════════════════════════════════════════
async def edited_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.edited_message
    if not message:
        return
    chat = message.chat
    user = message.from_user
    if not user or user.is_bot:
        return
    if chat.type == "private":
        return
    if not is_premium(chat.id):
        return
    if not get_setting(chat.id, "antiedit_on", False):
        return

    # Skip admins
    try:
        m = await context.bot.get_chat_member(chat.id, user.id)
        if m.status in ("administrator", "creator"):
            return
    except Exception:
        pass

    try:
        await message.delete()
    except Exception:
        return

    await context.bot.send_message(
        chat.id,
        f"✏️ {user.mention_html()} — <b>Edited message delete ho gaya!</b>\n"
        f"<i>Group mein messages edit karna allowed nahi.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Dismiss", callback_data="automod_dismiss"),
        ]]),
    )
