import random

BOT_NAME       = "ᴀꜱ ɢʀᴏᴜᴘ ʙᴏᴛ"
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"

# ════════════════════════════════════════════════════════
# BOT TRIGGER KEYWORDS
# When any of these appear in a message, bot will reply
# ════════════════════════════════════════════════════════

BOT_TRIGGERS = [
    # Bot names / nicknames
    "cutie", "cutie pie", "cutiepie",
    "bot", "robot", "robo",
    "as bot", "as group bot",

    # Direct address (Hinglish)
    "hey bot", "hi bot", "hello bot",
    "oye bot", "aye bot", "sun bot",
    "bhai bot", "yaar bot",

    # Attention words
    "suno", "sun", "batao", "bolo",
    "bol", "kya lagta", "kya sochti",
    "kya hai", "help me", "help karo",

    # Common Indian attention words
    "arre", "yaar", "dost",
]

# ════════════════════════════════════════════════════════
# STICKER IDs
# Replace these with actual sticker file_ids from your bot
# ════════════════════════════════════════════════════════

_STICKERS = {
    "happy": [
        "CAACAgIAAxkBAAIBB2YAAhappysticker1",   # replace with real IDs
        "CAACAgIAAxkBAAIBB2YAAhappysticker2",
    ],
    "sad": [
        "CAACAgIAAxkBAAIBB2YAAasadsticker1",
        "CAACAgIAAxkBAAIBB2YAAasadsticker2",
    ],
    "angry": [
        "CAACAgIAAxkBAAIBB2YAAaangrysticker1",
    ],
    "love": [
        "CAACAgIAAxkBAAIBB2YAAalovesticker1",
        "CAACAgIAAxkBAAIBB2YAAalovesticker2",
    ],
    "laugh": [
        "CAACAgIAAxkBAAIBB2YAAlaughsticker1",
    ],
    "default": [
        "CAACAgIAAxkBAAIBB2YAAdefaultsticker1",
        "CAACAgIAAxkBAAIBB2YAAdefaultsticker2",
    ],
}

def get_sticker(mood: str = "default") -> str:
    """Return a random sticker file_id for given mood"""
    options = _STICKERS.get(mood, _STICKERS["default"])
    return random.choice(options)

def should_send_sticker() -> bool:
    """15% chance bot sends a sticker after replying"""
    return random.random() < 0.15

# ════════════════════════════════════════════════════════
# WELCOME MESSAGES
# ════════════════════════════════════════════════════════

_WELCOME_MSGS = [
    "🌸 {mention} aa gaya/gayi! Welcome to the family~ 💘\nRules follow karo aur maza karo! 🎉",
    "✨ Heyy {mention}! Welcome welcome~ 🌸\nAb group aur bhi acha lag raha hai! 💘",
    "🎉 {mention} ka swagat hai! 🌸\nSaath mein bahut maza aayega~ 💘",
    "💫 {mention} join kar liya! Yayy~ 🎊\nGroup rules zaroor padho! 🌸",
    "🌺 Areyy {mention} aa gaya/gayi! 😄💘\nWelcome to our lovely group~ 🌸",
    "🎀 {mention} welcome!! 🌸\nAb poori team complete ho gayi~ 💘",
    "⭐ {mention} join ho gaye! 🎉\nRules follow karna mat bhulna~ 🌸",
]

_WELCOME_MEDIA_CAPTIONS = [
    "Naya member! 🌸 {mention} — welcome ho~ 💘",
    "{mention} aa gaye! 🎉 Group mein swagat hai~ 🌸",
]

def get_welcome(mention: str) -> str:
    """Return a random welcome message with mention"""
    msg = random.choice(_WELCOME_MSGS)
    return msg.replace("{mention}", mention)

def get_welcome_caption(mention: str) -> str:
    msg = random.choice(_WELCOME_MEDIA_CAPTIONS)
    return msg.replace("{mention}", mention)

# ════════════════════════════════════════════════════════
# GOODBYE MESSAGES
# ════════════════════════════════════════════════════════

_GOODBYE_MSGS = [
    "😢 {name} chala/chali gaya/gayi! Miss karenge~ 🌸",
    "👋 Bye bye {name}! Take care~ 💘",
    "💔 {name} ne group chod diya... sad~ 🌸",
    "🚪 {name} left the chat. Aate rehna! 🌸",
    "😔 {name} ab nahi rahega/rahegi... byeee 💘",
]

def get_goodbye(name: str) -> str:
    """Return a random goodbye message"""
    msg = random.choice(_GOODBYE_MSGS)
    return msg.replace("{name}", name)

# ════════════════════════════════════════════════════════
# ABOUT TEXT
# ════════════════════════════════════════════════════════

ABOUT_TEXT = f"""
🤖 <b>{BOT_NAME}</b>

Advanced Telegram Group Manager with Smart AI 🌸

👨‍💻 Developer: {OWNER_USERNAME}
📢 Updates: {UPDATE_CHANNEL}

Features:
• Anti-Gaali (200+ words + leetspeak)
• Anti-Raid Protection
• Movie Copyright System
• Smart Human-like AI
• Notes System
• Premium Subscription
""".strip()
