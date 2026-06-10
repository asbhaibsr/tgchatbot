import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.db import get_setting, is_premium
from core.persona import BOT_NAME

OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"
PREMIUM_PRICE  = int(os.environ.get("PREMIUM_PRICE", "99"))

# ════════════════════════════════════════════════════════
# HELP — full interactive menu
# ════════════════════════════════════════════════════════

_HELP_MAIN = """
📖 <b>Help Menu — {bot_name}</b>

Neeche se category choose karo:
""".strip()

_HELP_ADMIN = """
👮 <b>Admin Commands</b>

<b>Moderation:</b>
/ban — User ko ban karo (reply ya ID)
/unban — Unban karo
/mute [time] — Mute (e.g. /mute 1h, /mute 30m)
/unmute — Unmute karo
/kick — Group se kick
/warn [reason] — Warn do
/warns — Warns dekho
/resetwarn — Warns reset karo

<b>Group Management:</b>
/pin — Message pin karo (reply karke)
/unpin — Unpin karo
/del — Message delete (reply karke)
/purge — Multiple messages delete
/promote — Admin banao
/demote — Admin hatao
/tagall [msg] — Sab members ko tag karo
/slowmode [sec] — Slowmode set karo

<b>Locks:</b>
/lock [type] — Lock: stickers/gifs/polls/media/voice
/unlock [type] — Unlock karo
/settings — Full settings panel

<b>Notes:</b>
/save [name] [content] — Note save karo
/get [name] — Note get karo
/notes — Sab notes list
/delnote [name] — Note delete karo
Type <code>#notename</code> anywhere to get a note!

<b>Welcome/Rules:</b>
/setwelcome [msg] — Custom welcome set (variables: {name}, {group})
/setgoodbye [msg] — Custom goodbye
/setrules [text] — Group rules set

<b>Analytics (Premium):</b>
/stats — Group statistics
/topusers — Top chatters
/whois — User info

<b>Premium Only:</b>
/schedule HH:MM [msg] — Daily message schedule
/unschedule — Schedule cancel
/floodlimit [n] — Flood limit set
/autodel [sec] — Auto-delete timer
/warnlimit [n] — Warn limit set
/unlock_raid — Raid ke baad group unlock
""".strip()

_HELP_USER = """
👤 <b>User Commands</b>

/start — Bot start karo
/help — Yeh menu
/rules — Group rules dekho
/id — Apna/kisi ka ID dekho
/whois — User info (reply karke)
/premium — Premium info
/report [reason] — Admin ko alert karo (reply karke)
/font [text] — Text ko fancy font mein convert karo
/adminlist — Admins ki list

<b>Notes:</b>
<code>#notename</code> — Koi bhi note directly type karke pao!
""".strip()

def _main_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👮 Admin",    callback_data="help_admin"),
            InlineKeyboardButton("👤 User",     callback_data="help_user"),
        ],
        [
            InlineKeyboardButton("👑 Premium",  callback_data="prem_info"),
            InlineKeyboardButton("ℹ️ About",    callback_data="about"),
        ],
        [InlineKeyboardButton("📢 Channel", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}")],
    ])

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        _HELP_MAIN.format(bot_name=BOT_NAME),
        parse_mode="HTML",
        reply_markup=_main_markup(),
    )

async def user_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    await query.answer()

    if data == "help_main":
        await query.edit_message_text(
            _HELP_MAIN.format(bot_name=BOT_NAME),
            parse_mode="HTML",
            reply_markup=_main_markup(),
        )
    elif data == "help_admin":
        await query.edit_message_text(
            _HELP_ADMIN,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="help_main")
            ]]),
        )
    elif data == "help_user":
        await query.edit_message_text(
            _HELP_USER,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="help_main")
            ]]),
        )

# ════════════════════════════════════════════════════════
# /RULES
# ════════════════════════════════════════════════════════

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat    = update.effective_chat
    message = update.effective_message
    rules   = get_setting(chat.id, "rules", None)
    if rules:
        await message.reply_text(
            f"📋 <b>{chat.title} Rules:</b>\n\n{rules}",
            parse_mode="HTML"
        )
    else:
        await message.reply_text(
            "📋 Rules abhi set nahi hain!\n"
            "Admin: /setrules <rules text>"
        )

# ════════════════════════════════════════════════════════
# /ID
# ════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════
# /PREMIUM INFO
# ════════════════════════════════════════════════════════

async def premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    me   = await context.bot.get_me()

    prem_active = is_premium(chat.id) if chat.type != "private" else False
    status_line = "✅ <b>Active!</b>" if prem_active else "❌ Not Active"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "💳 Subscribe Now",
            url=f"https://t.me/{me.username}?start=premium"
        )],
        [InlineKeyboardButton("📢 Updates", url=f"https://t.me/{UPDATE_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("👤 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.lstrip('@')}")],
    ])

    await update.message.reply_text(
        f"👑 <b>Premium Subscription</b>\n\n"
        f"Status: {status_line}\n"
        f"💰 Price: <b>₹{PREMIUM_PRICE}/month</b>\n\n"
        f"<b>Free (All Groups):</b>\n"
        f"✅ Anti-Gaali (200+ words + leetspeak)\n"
        f"✅ Notes System (#notename)\n"
        f"✅ Smart AI Chatbot\n"
        f"✅ Warn/Ban/Mute/Kick\n"
        f"✅ Welcome/Goodbye\n"
        f"✅ Pin/Purge/Tag All\n"
        f"✅ /whois User Info\n\n"
        f"<b>👑 Premium Only:</b>\n"
        f"🔗 Anti-Link + Anti-Forward\n"
        f"👤 Anti-Username Promo\n"
        f"🛡 Anti-Raid (auto group lock)\n"
        f"🎬 Movie File Copyright System\n"
        f"🤖 Button Captcha (new members)\n"
        f"📊 Group Analytics + Top Users\n"
        f"⏰ Scheduled Daily Messages\n"
        f"🗑 Auto-Delete Media\n"
        f"⚡ Flood Control\n"
        f"🔒 Media/Sticker/GIF Locks\n\n"
        f"PM {OWNER_USERNAME} to subscribe!",
        parse_mode="HTML",
        reply_markup=markup,
    )

# ════════════════════════════════════════════════════════
# /FONT — Fancy text converter
# ════════════════════════════════════════════════════════

_FONTS = {
    "bold":    str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    ),
    "italic":  str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡"
    ),
    "script":  str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"
    ),
    "bubble":  str.maketrans(
        "abcdefghijklmnopqrstuvwxyz",
        "ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ"
    ),
    "small":   str.maketrans(
        "abcdefghijklmnopqrstuvwxyz",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘQʀꜱᴛᴜᴠᴡxʏᴢ"
    ),
}

async def font_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not context.args:
        await message.reply_text(
            "❌ Use: /font <text>\n\nExample: /font hello world"
        )
        return
    text = " ".join(context.args)
    results = []
    for name, table in _FONTS.items():
        converted = text.translate(table)
        results.append(f"<b>{name.title()}:</b> {converted}")
    await message.reply_text("\n".join(results), parse_mode="HTML")

# ════════════════════════════════════════════════════════
# /ADMINLIST (also in admin.py but accessible to users)
# ════════════════════════════════════════════════════════

