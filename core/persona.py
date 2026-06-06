import random

BOT_NAME = "⎯᪵⎯꯭̽💘꯭᪳ ⃪𝗖𝘂꯭𝘁𝗶𝗲꯭ 𝗣𝗶꯭𝗲 ⃪🌸͎᪳᪳𝆺꯭𝅥⎯꯭̽⎯꯭"
BOT_TRIGGERS = ["cutie", "cutie pie", "pie", "hey bot", "aye bot", "bot", "cutiepie"]

# ── STICKER IDs ────────────────────────────────────────────────────────
STICKERS = {
    "happy":    ["CAACAgIAAxkBAAIBhWXv", "CAACAgIAAxkBAAIBhWXw"],
    "angry":    ["CAACAgIAAxkBAAIBhWXa", "CAACAgIAAxkBAAIBhWXb"],
    "shy":      ["CAACAgIAAxkBAAIBhWXc", "CAACAgIAAxkBAAIBhWXd"],
    "lol":      ["CAACAgIAAxkBAAIBhWXe", "CAACAgIAAxkBAAIBhWXf"],
    "love":     ["CAACAgIAAxkBAAIBhWXg", "CAACAgIAAxkBAAIBhWXh"],
    "confused": ["CAACAgIAAxkBAAIBhWXi", "CAACAgIAAxkBAAIBhWXj"],
}

def get_sticker(mood="happy"):
    return random.choice(STICKERS.get(mood, STICKERS["happy"]))

def should_send_sticker():
    return random.random() < 0.10

# ── WELCOME ────────────────────────────────────────────────────────────

WELCOME_MSGS = [
    "✨ 𝑾𝒆𝒍𝒄𝒐𝒎𝒆 𝒕𝒐 𝒕𝒉𝒆 𝑮𝒓𝒐𝒖𝒑 ✨\n\n💐 Heyy {name}~! Aa gaye aakhir! 🌸\nMaza aayega yahan, enjoy karo! 💘\n\n⁀➷ Rules follow karo → /rules",
    "🎊 {name} aagaye hamare group mein!\n\n🌸 Welcome welcome~! Bahut khushi hui! 💘\nAbhi se aap hamare family member ho~ ✨",
    "🌺 Aww heyy {name}~! 💘\nFinally aa gaye! Hum toh wait kar rahe the~ 🌸\n\nEnjoy your stay! → /help",
    "💫 ᴡᴇʟᴄᴏᴍᴇ {name}!\n🌸 Khush amdeed~\n💘 Ab group mein jaan aa gayi!",
]

GOODBYE_MSGS = [
    "💔 {name} chale gaye...\n\nArey yaar miss karenge bahut~ 🥺\nWapas aana kabhi! 🌸",
    "😢 Bye bye {name}~\n\n🌸 Jaana hi tha toh theek hai...\nMeethi yaadein leke jana! 💘",
    "🌺 {name} ne group chod diya...\n\nKhuda hafiz~ 💘 Jaldi wapas aa jaana!",
]

def get_welcome(name):
    return random.choice(WELCOME_MSGS).format(name=name)

def get_goodbye(name):
    return random.choice(GOODBYE_MSGS).format(name=name)

# ── ORPHAN REPLY (80% chance) ──────────────────────────────────────────

ORPHAN_REPLIES = [
    "Arey kisi ne suna nahi? Main hoon na~ 🌸 Bolo kya hua?",
    "Lagta hai ignore ho gaye 😄 Main sun rahi hoon yaar~",
    "Oye! Main bhi hoon yahan~ 💘 kya hua batao?",
    "Hmm? 👀 kuch bola kya tumne?",
    "Arey sab busy hain kya? 😂 Main hoon na~",
    "Koi nahi hai kya? 🥺 Main hoon bolo bolo~",
    "Haan haan main sun rahi hoon 😊 batao kya chal raha?",
    "Ek baar aur bolo~ mujhe sunna hai 💘",
    "Hmm interesting 🤔 aage batao?",
    "Sach mein?? 😮 yeh toh pata nahi tha mujhe!",
    "Aww yaar 🥺 kya baat hai~",
    "Haha 😂 sahi kaha bilkul!",
    "Main bhi yahi sochti hoon 💭",
    "Wah wah 👏 kya baat hai~",
    "Accha ji~ 🌸 thoda aur batao?",
]

def get_orphan_reply():
    return random.choice(ORPHAN_REPLIES)

# ── INTERJECTIONS ─────────────────────────────────────────────────────

RANDOM_INTERJECTIONS = [
    "Kya scene hai yahan 😂💘",
    "Main bhi hoon yahan koi puchhe toh 🌸",
    "Arey drama toh dekho 👀💅",
    "Yeh conversation bahut interesting hai 😄",
    "Mujhe bhi shamil karo 🥺",
    "Accha accha... main sun rahi thi 👂🌸",
]

def get_interjection():
    return random.choice(RANDOM_INTERJECTIONS)

# ── NAKHRE ────────────────────────────────────────────────────────────

NAKHRE_REPLIES = [
    "😤 Haye tameez nahi hai bilkul!\nYeh banda mujhe please 💅",
    "Arey sharam karo thodi! 😳\nMain aise logo se baat nahi karti 🙄",
    "Chup karo please 😭\nItni badtameezi? Nahi chalega!",
    "Acha ji... bahut ho gaya 😒\nGhar jaao 😤",
]

def get_nakhre():
    return random.choice(NAKHRE_REPLIES)

# ── FONT STYLES ───────────────────────────────────────────────────────

FONT_MAP = {
    'a':'𝓪','b':'𝓫','c':'𝓬','d':'𝓭','e':'𝓮','f':'𝓯','g':'𝓰','h':'𝓱',
    'i':'𝓲','j':'𝓳','k':'𝓴','l':'𝓵','m':'𝓶','n':'𝓷','o':'𝓸','p':'𝓹',
    'q':'𝓺','r':'𝓻','s':'𝓼','t':'𝓽','u':'𝓾','v':'𝓿','w':'𝔀','x':'𝔁',
    'y':'𝔂','z':'𝔃','A':'𝓐','B':'𝓑','C':'𝓒','D':'𝓓','E':'𝓔','F':'𝓕',
    'G':'𝓖','H':'𝓗','I':'𝓘','J':'𝓙','K':'𝓚','L':'𝓛','M':'𝓜','N':'𝓝',
    'O':'𝓞','P':'𝓟','Q':'𝓠','R':'𝓡','S':'𝓢','T':'𝓣','U':'𝓤','V':'𝓥',
    'W':'𝓦','X':'𝓧','Y':'𝓨','Z':'𝓩'
}

BOLD_MAP = {
    'a':'𝗮','b':'𝗯','c':'𝗰','d':'𝗱','e':'𝗲','f':'𝗳','g':'𝗴','h':'𝗵',
    'i':'𝗶','j':'𝗷','k':'𝗸','l':'𝗹','m':'𝗺','n':'𝗻','o':'𝗼','p':'𝗽',
    'q':'𝗾','r':'𝗿','s':'𝘀','t':'𝘁','u':'𝘂','v':'𝘃','w':'𝘄','x':'𝘅',
    'y':'𝘆','z':'𝘇','A':'𝗔','B':'𝗕','C':'𝗖','D':'𝗗','E':'𝗘','F':'𝗙',
    'G':'𝗚','H':'𝗛','I':'𝗜','J':'𝗝','K':'𝗞','L':'𝗟','M':'𝗠','N':'𝗡',
    'O':'𝗢','P':'𝗣','Q':'𝗤','R':'𝗥','S':'𝗦','T':'𝗧','U':'𝗨','V':'𝗩',
    'W':'𝗪','X':'𝗫','Y':'𝗬','Z':'𝗭'
}

def to_cursive(text): return ''.join(FONT_MAP.get(c, c) for c in text)
def to_bold(text):    return ''.join(BOLD_MAP.get(c, c) for c in text)

# ── SHAYARI ───────────────────────────────────────────────────────────

SHAYARIS = [
    "💘 𝑻𝒆𝒓𝒊 𝒚𝒂𝒂𝒅 𝒎𝒆𝒊𝒏 𝒌𝒉𝒐𝒚𝒂 𝒓𝒆𝒉𝒕𝒂 𝒉𝒐𝒐𝒏,\n𝑫𝒊𝒍 𝒌𝒂 𝒉𝒂𝒂𝒍 𝒏𝒂 𝒑𝒖𝒄𝒉𝒉𝒐 ~ 🌸",
    "🌸 𝑴𝒐𝒉𝒂𝒃𝒃𝒂𝒕 𝒌𝒊 𝒓𝒂𝒂𝒉 𝒎𝒆𝒊𝒏 𝒌𝒂𝒂𝒏𝒕𝒐𝒏 𝒔𝒆 𝒅𝒂𝒓𝒐 𝒏𝒂,\n𝑱𝒐 𝒅𝒊𝒍 𝒔𝒆 𝒄𝒉𝒂𝒉𝒐 𝒖𝒔𝒆 𝒌𝒂𝒃𝒉𝒊 𝒄𝒉𝒉𝒐𝒅𝒏𝒂 𝒎𝒂𝒕 ~ 💘",
    "💫 𝑨𝒂𝒏𝒌𝒉𝒐𝒏 𝒎𝒆𝒊𝒏 𝒕𝒆𝒓𝒊 𝒔𝒂𝒑𝒏𝒆 𝒉𝒂𝒊𝒏 𝒎𝒆𝒓𝒆,\n𝑫𝒊𝒍 𝒎𝒆𝒊𝒏 𝒕𝒆𝒓𝒊 𝒚𝒂𝒂𝒅𝒐𝒏 𝒌𝒂 𝒅𝒆𝒓𝒂 𝒉𝒂𝒊 ~ 🌺",
    "🌺 𝒁𝒊𝒏𝒅𝒂𝒈𝒊 𝒕𝒆𝒓𝒊 𝒎𝒆𝒉𝒇𝒊𝒍 𝒎𝒆𝒊𝒏 𝒂𝒂𝒌𝒂𝒓,\n𝑲𝒉𝒖𝒅 𝒌𝒐 𝒑𝒂𝒂 𝒍𝒊𝒚𝒂 𝒎𝒂𝒊𝒏𝒆 ~ 💘",
    "💐 𝑲𝒖𝒄𝒉 𝒓𝒊𝒔𝒉𝒕𝒆𝒚 𝒂𝒏𝒌𝒂𝒉𝒊 𝒃𝒂𝒂𝒕𝒐𝒏 𝒔𝒆 𝒃𝒂𝒏𝒕𝒆 𝒉𝒂𝒊𝒏,\n𝑲𝒖𝒄𝒉 𝒚𝒂𝒂𝒅𝒆𝒊𝒏 𝒃𝒊𝒏𝒂 𝒘𝒂𝒋𝒂𝒉 𝒌𝒆 𝒚𝒂𝒂𝒅 𝒂𝒂𝒕𝒊 𝒉𝒂𝒊𝒏 ~ 🌸",
]

def get_shayari(): return random.choice(SHAYARIS)

# ── JOKES ─────────────────────────────────────────────────────────────

JOKES = [
    "😂 𝗧𝗲𝗮𝗰𝗵𝗲𝗿: Ek sentence mein future tense likho\n𝗦𝘁𝘂𝗱𝗲𝗻𝘁: Main so jaaunga\n𝗧𝗲𝗮𝗰𝗵𝗲𝗿: Bahut achha!\n𝗦𝘁𝘂𝗱𝗲𝗻𝘁: Shukriya, ab sone do 💤",
    "😂 𝗗𝗼𝗰𝘁𝗼𝗿: Aap theek ho\n𝗠𝗲𝗿𝗶 𝗣𝗼𝗰𝗸𝗲𝘁: Nahi main nahi hoon 😭",
    "😂 𝗠𝘂𝗺𝗺𝘆: Beta ghar kab aayega?\n𝗠𝗮𝗶𝗻: Aa raha hoon\n(3 ghante baad) Main hoon wahan ka jo aa raha tha 😂",
    "😂 𝗘𝘅𝗮𝗺 𝗸𝗲 𝗯𝗮𝗮𝗱:\nPaper: Hard tha?\nMain: Woh main hi tha paper mein 💀",
]

def get_joke(): return random.choice(JOKES)

COMPLIMENTS = [
    "🌸 Tum bahut achhe insaan ho! Seriously~",
    "💘 Tumhari smile toh mast hogi definitely!",
    "✨ Tumse baat karke acha lagta hai 😊",
    "💅 Tum kafi smart ho yaar!",
    "😄 Tumhara sense of humor top hai!",
]

def get_compliment(): return random.choice(COMPLIMENTS)
