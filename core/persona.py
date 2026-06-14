import random

BOT_NAME       = "ᴀꜱ ɢʀᴏᴜᴘ ʙᴏᴛ"
OWNER_USERNAME = "@asbhaibsr"
UPDATE_CHANNEL = "@asbhai_bsr"

# ════════════════════════════════════════════════════════
# BOT TRIGGER KEYWORDS
# ════════════════════════════════════════════════════════

BOT_TRIGGERS = [
    # Bot names
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
    # Common Indian
    "arre", "yaar", "dost",
]

# ════════════════════════════════════════════════════════
# STICKER IDs — replace with real ones from your bot
# ════════════════════════════════════════════════════════

_STICKERS = {
    "happy":   ["CAACAgIAAxkBAAIBB2YAAhappysticker1"],
    "sad":     ["CAACAgIAAxkBAAIBB2YAAasadsticker1"],
    "angry":   ["CAACAgIAAxkBAAIBB2YAAaangrysticker1"],
    "love":    ["CAACAgIAAxkBAAIBB2YAAalovesticker1"],
    "laugh":   ["CAACAgIAAxkBAAIBB2YAAlaughsticker1"],
    "default": ["CAACAgIAAxkBAAIBB2YAAdefaultsticker1"],
}

def get_sticker(mood: str = "default") -> str:
    options = _STICKERS.get(mood, _STICKERS["default"])
    return random.choice(options)

def should_send_sticker() -> bool:
    return random.random() < 0.15


# ════════════════════════════════════════════════════════
# WELCOME MESSAGES — Roast + Funny Indian Style 😂
# ════════════════════════════════════════════════════════

_WELCOME_MSGS = [
    "🎉 Aye {mention}! Aa gaye finally?\nRules padh lena bhai, warna main padhaaunga 😤",
    "🌸 {mention} join ho gaye!\nSwagat hai... agar rules follow karoge toh 😏",
    "😎 {mention} aaya/aayi! Ab group poora hua!\nPehle /rules padh lo, phir mazak karo 😂",
    "✨ Heyy {mention}! Welcome welcome~\nGroup mein settle ho jao, gaali mat dena warna ban 👋😂",
    "🎊 {mention} ka grand swagat!\nID proof mat maango, group hai Aadhaar center nahi 😅",
    "🌺 Areyy {mention} aa gaya/aayi!\nRules follow karo, admin ke baap mat bano 😤",
    "🎀 {mention}! Welcome!\nDekho naya member aaya — ab thodi life aayi group mein! 💘",
    "⭐ {mention} join kiya!\nBhai seedha raho, tab tak sab theek hai 😊",
    "🔥 {mention} enter the group!\nRules todne se pehle socho — ban milta hai maafi nahi 😈",
    "💫 Aye {mention}! Group mein aao, settle ho jao!\nGaali doge toh main hoon na... band kardunga 😂",
]

def get_welcome(mention: str) -> str:
    msg = random.choice(_WELCOME_MSGS)
    return msg.replace("{mention}", mention)

def get_welcome_caption(mention: str) -> str:
    captions = [
        "Naya member! 🌸 {mention} — swagat hai, rules follow karo!",
        "{mention} aa gaye! 🎉 Mazak mast karo, gaali mat dena 😂",
    ]
    return random.choice(captions).replace("{mention}", mention)


# ════════════════════════════════════════════════════════
# GOODBYE MESSAGES — Roast + Funny Indian Style 😂
# ════════════════════════════════════════════════════════

_GOODBYE_MSGS = [
    "😢 {name} chala/chali gaya/gayi...\nShayad rules se dara/dari 😂",
    "👋 Bye {name}! Take care~\nAate rehna... agar himmat ho toh 😏",
    "💔 {name} ne group chhod diya!\nLog aate hain, jaate hain — life goes on 🌸",
    "🚪 {name} ne exit maar liya!\nKoi baat nahi, kuch log paida hi jaane ke liye hote hain 😂",
    "😔 {name} left the chat!\nRona nahi chahiye... waise bhi rules nahi follow karte the 😤",
    "🏃 {name} bhaag gaya/gayi!\nShayad ban se dara/dari thi — smart move 😂",
]

def get_goodbye(name: str) -> str:
    msg = random.choice(_GOODBYE_MSGS)
    return msg.replace("{name}", name)


# ════════════════════════════════════════════════════════
# ABOUT TEXT
# ════════════════════════════════════════════════════════

ABOUT_TEXT = f"""
🤖 <b>{BOT_NAME}</b>

Advanced Telegram Group Manager with Smart AI 🌸
(Jo rules nahi maanta, use main sambhalti hoon 😤)

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
