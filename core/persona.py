import random

BOT_NAME = "⎯᪵⎯꯭̽💘꯭᪳ ⃪𝗖𝘂꯭𝘁𝗶𝗲꯭ 𝗣𝗶꯭𝗲 ⃪🌸͎᪳᪳𝆺꯭𝅥⎯꯭̽⎯꯭"
BOT_TRIGGERS = ["cutie", "cutie pie", "laila", "hey bot", "aye bot", "bot"]

# ── STICKER IDs ────────────────────────────────────────────────────────
# In real use, replace these with actual Telegram sticker file_ids
STICKERS = {
    "happy":    ["CAACAgIAAxkBAAIBhWXv", "CAACAgIAAxkBAAIBhWXw"],
    "angry":    ["CAACAgIAAxkBAAIBhWXa", "CAACAgIAAxkBAAIBhWXb"],
    "shy":      ["CAACAgIAAxkBAAIBhWXc", "CAACAgIAAxkBAAIBhWXd"],
    "lol":      ["CAACAgIAAxkBAAIBhWXe", "CAACAgIAAxkBAAIBhWXf"],
    "love":     ["CAACAgIAAxkBAAIBhWXg", "CAACAgIAAxkBAAIBhWXh"],
    "confused": ["CAACAgIAAxkBAAIBhWXi", "CAACAgIAAxkBAAIBhWXj"],
}

def get_sticker(mood="happy"):
    stickers = STICKERS.get(mood, STICKERS["happy"])
    return random.choice(stickers)

def should_send_sticker():
    """12% chance sticker bhejna"""
    return random.random() < 0.12

# ── WELCOME ───────────────────────────────────────────────────────────

WELCOME_MSGS = [
    "Aww aagaye aap! 🌸 {name} ko bada pyara welcome hai is group mein~ Enjoy karo! 💘",
    "Ohh heyy {name}! Aa gaye tum bhi! 😄 Welcome to the group jaan~ 🌸",
    "Yayy {name} aagaye! 🎉 Welcome welcome! Ab maza aayega~ 💘",
    "Heyy {name}! 👋🌸 Aadab! Welcome to our little family~",
]

GOODBYE_MSGS = [
    "Aww {name} chale gaye 😢 Miss karenge tumhe~",
    "Byee {name}! 🌸 Wapas aana kabhi~",
    "Arey {name} chhod ke chale gaye? 😭 Theek hai... bye bye~",
]

def get_welcome(name):
    return random.choice(WELCOME_MSGS).format(name=name)

def get_goodbye(name):
    return random.choice(GOODBYE_MSGS).format(name=name)

# ── BEECH MEIN BOLNA ──────────────────────────────────────────────────

RANDOM_INTERJECTIONS = [
    "Arey yaar kya chal raha hai yahan 👀",
    "Main bhi hoon yahan koi puchhe toh 🌸",
    "Kya baat kar rahe ho tum log 😄",
    "Itna shor kyun hai 😂",
    "Mujhe bhi shamil karo conversation mein 🥺",
    "Accha accha... main sun rahi hoon 👂",
    "Drama toh dekho 👀💅",
    "Kya scene hai yahan 😂",
]

def get_interjection():
    return random.choice(RANDOM_INTERJECTIONS)

# ── ORPHAN MESSAGE REPLY (koi bina reply ke message kare) ─────────────

ORPHAN_REPLIES = [
    "Kisi ne suna nahi tumhe toh main hoon na 🌸 Bolo kya hua?",
    "Lagta hai message ignore ho gaya 😄 Main sun rahi hoon~",
    "Arey kisi ne reply nahi kiya? Chalo main karta hoon 💘",
    "Sab busy hain kya? Main hoon na 🥺",
]

def get_orphan_reply():
    return random.choice(ORPHAN_REPLIES)

# ── ROAST (bina gali ke) ───────────────────────────────────────────────

ROAST_REPLIES = [
    "Beta jao pehle aaina dekho 😂",
    "Ye sun ke toh meri aankhein khuli reh gayi 👀",
    "Tameez seekho pehle phir aana 😤",
    "Arey yaar itna kuch tha toh ghar pe hi rehte na 😭",
    "Haye toba... kya zamana aa gaya 🤦‍♀️",
    "Main toh kehti hoon chup raho behtar lagoge 💅",
    "Sach mein? Sachhi? Wah re wah 😂",
]

def get_roast():
    return random.choice(ROAST_REPLIES)

# ── NAKHRE wala reply (gandi baat pe) ────────────────────────────────

NAKHRE_REPLIES = [
    "Haye tameez nahi hai tumhe bilkul 😤",
    "Arey yeh kya baat hai? Sharam karo thodi 😳",
    "Main aise logo se baat nahi karti 🙄",
    "Acha ji... bahut ho gaya 😒",
    "Chup karo please main sun nahi sakti 😭",
]

def get_nakhre():
    return random.choice(NAKHRE_REPLIES)

# ── FONT STYLES ───────────────────────────────────────────────────────

FONT_MAP = {
    'a':'𝓪','b':'𝓫','c':'𝓬','d':'𝓭','e':'𝓮','f':'𝓯','g':'𝓰','h':'𝓱',
    'i':'𝓲','j':'𝓳','k':'𝓴','l':'𝓵','m':'𝓶','n':'𝓷','o':'𝓸','p':'𝓹',
    'q':'𝓺','r':'𝓻','s':'𝓼','t':'𝓽','u':'𝓾','v':'𝓿','w':'𝔀','x':'𝔁',
    'y':'𝔂','z':'𝔃',
    'A':'𝓐','B':'𝓑','C':'𝓒','D':'𝓓','E':'𝓔','F':'𝓕','G':'𝓖','H':'𝓗',
    'I':'𝓘','J':'𝓙','K':'𝓚','L':'𝓛','M':'𝓜','N':'𝓝','O':'𝓞','P':'𝓟',
    'Q':'𝓠','R':'𝓡','S':'𝓢','T':'𝓣','U':'𝓤','V':'𝓥','W':'𝓦','X':'𝓧',
    'Y':'𝓨','Z':'𝓩'
}

BOLD_MAP = {
    'a':'𝗮','b':'𝗯','c':'𝗰','d':'𝗱','e':'𝗲','f':'𝗳','g':'𝗴','h':'𝗵',
    'i':'𝗶','j':'𝗷','k':'𝗸','l':'𝗹','m':'𝗺','n':'𝗻','o':'𝗼','p':'𝗽',
    'q':'𝗾','r':'𝗿','s':'𝘀','t':'𝘁','u':'𝘂','v':'𝘃','w':'𝘄','x':'𝘅',
    'y':'𝘆','z':'𝘇',
    'A':'𝗔','B':'𝗕','C':'𝗖','D':'𝗗','E':'𝗘','F':'𝗙','G':'𝗚','H':'𝗛',
    'I':'𝗜','J':'𝗝','K':'𝗞','L':'𝗟','M':'𝗠','N':'𝗡','O':'𝗢','P':'𝗣',
    'Q':'𝗤','R':'𝗥','S':'𝗦','T':'𝗧','U':'𝗨','V':'𝗩','W':'𝗪','X':'𝗫',
    'Y':'𝗬','Z':'𝗭'
}

def to_cursive(text):
    return ''.join(FONT_MAP.get(c, c) for c in text)

def to_bold(text):
    return ''.join(BOLD_MAP.get(c, c) for c in text)

# ── SHAYARI ───────────────────────────────────────────────────────────

SHAYARIS = [
    "💘 Dil diya hai, jaan bhi denge,\nAe watan tere liye...\nOops galat shayari 😂\n\nYe lo sahi wali:\nTeri yaad mein khoya rehta hoon,\nDil ka haal na puchho ~",
    "🌸 Mohabbat ki raah mein kaanton se daro na,\nJo dil se chaho use kabhi chhodna mat ~",
    "💘 Aankhon mein teri sapne hain mere,\nDil mein teri yaadon ka dera hai ~",
    "🌸 Zindagi teri mehfil mein aakar,\nKhud ko paa liya maine ~",
]

def get_shayari():
    return random.choice(SHAYARIS)

# ── JOKES ─────────────────────────────────────────────────────────────

JOKES = [
    "Teacher: Ek sentence mein future tense likho\nStudent: Main so jaaunga 😂\nTeacher: Bahut achha!\nStudent: Shukriya, ab sone do 💤",
    "Bandi: Tumse zyada koi nahi samjha mujhe\nBanda: Main bhi nahi samjha, bas haan karta raha 😂",
    "Doctor: Aap theek ho\nMeri pocket: Nahi main nahi hoon 😭",
    "Mummy: Beta ghar kab aayega?\nMain: Aa raha hoon\n(3 ghante baad) Main hoon wahan ka jo aa raha tha 😂",
]

def get_joke():
    return random.choice(JOKES)

# ── COMPLIMENTS ───────────────────────────────────────────────────────

COMPLIMENTS = [
    "Tum bahut achhe insaan ho 🌸 Seriously!",
    "Tumhari smile toh mast hogi definitely 💘",
    "Tumse baat karke acha lagta hai 😊",
    "Tum kafi smart ho yaar 💅",
    "Tumhara sense of humor top hai 😂💘",
]

def get_compliment():
    return random.choice(COMPLIMENTS)
