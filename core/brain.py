import random
import re
from core.db import (
    add_pattern, get_best_pattern, delete_pattern, get_all_patterns,
    save_message, get_recent_messages, push_bot_reply,
    get_recent_bot_replies, get_context,
)

# ════════════════════════════════════════════════════════
# MASSIVE REPLY CORPUS
# ════════════════════════════════════════════════════════

_GREETINGS = {
    "hi":           ["heyy~ 🌸", "hi hi! 💘", "haan ji! 😊", "hello jaan~ 🌺", "hiiii~ 💫", "hey kya chal raha? 👀"],
    "hello":        ["heyy! kya haal? 🌸", "hello hello~ 💘", "ji ji bolo 😄", "heyyyy~ 🌺", "kya hua? 😊"],
    "hey":          ["heyy~ 😍", "heyyy~ kya chal? 👀", "bolo bolo 🌸", "hey hey! 💘", "haan? 👀"],
    "hlo":          ["heyy~ 🌸", "hello! 💘", "ji bolo 😄"],
    "hii":          ["hiiii~ 😄💘", "heyy! 🌸", "hiiii jaanu~ 💫"],
    "hola":         ["hola~ 🌸 kya haal hai?", "arre Spanish mein? haha heyy 😄"],
    "kya haal":     ["main theek hoon, tum batao? 🌸", "mast hoon~ aap? 😊", "badhiya! tumhara? 💘"],
    "kaise ho":     ["bilkul mast hoon 😄 tum batao?", "theek hoon~ aap kaise? 🌸", "achha! tum? 💘"],
    "good morning": ["good morning! ☀️ aaj ka din acha ho~ 🌸", "morning! ☕ chai pi lo 😄", "subah bakhair~ 🌅"],
    "gm":           ["gm gm! ☀️", "good morning~ 🌸 chai piya? ☕", "morning! kya haal? 😊"],
    "good night":   ["good night~ 🌙 meethe sapne! 💘", "shubh ratri~ 🌙✨", "gn gn! 🌸 so jao ab~"],
    "gn":           ["gn~ 🌙 meethe sapne aana 💘", "good night! 🌸", "so jao jaldi~ 😄"],
    "bye":          ["byee~ 💘 jaldi wapas aana!", "bye bye! 🌸 miss karenge~", "chalo theek hai byee 💫"],
    "ok":           ["okay~ 🌸", "theek hai 😊", "accha ji 👍", "hmm okay~", "ji ji 😄"],
    "okay":         ["okay~ 💘", "theek hai 😊", "accha accha~", "ji haan 🌸"],
    "thanks":       ["arrey mention mat karo 🌸", "koi baat nahi jaan~ 💘", "yeh toh banta tha 😄", "welcome~ 🌺"],
    "thank you":    ["arre koi baat nahi! 🌸", "welcome welcome 💘", "itni formality 😄"],
    "haha":         ["hehe~ 😄", "😂 haan bahut funny tha!", "arey itna hasna mat 😂💘", "hahaha same 😂"],
    "lol":          ["hahahaha 😂😂", "LOL same yaar 😂", "kyun itna hasa? 😄", "lmao 😂"],
    "xd":           ["XD hahaha 😂", "xd xd 😄💘", "hehe~ 🌸"],
    "😂":           ["hahahaa 😂😂", "itna mat haso 😄", "lmao same 😂💘"],
}

_POSITIVE_REPLIES = [
    "waah kya baat hai! 🌸",
    "yayy itna achha sun ke khushi ho gayi 🎉💘",
    "aww itna achha! 🥺",
    "bahut badhiya yaar! main bhi khush hoon 😄",
    "OMG seriously?? bahut achha! 💘",
    "haye kitna acha! 🌸✨",
    "bahut bढ़iya! keep it up~ 💪🌸",
    "wow seriously? congrats yaar! 🎊",
    "itna mast sun ke dil khush ho gaya 💘",
    "yeh toh bohot badhiya hai! 🌺",
    "sach mein? wow! 😍",
    "main bhi khush hoon tere saath! 🌸",
    "yayy! celebrate karo 🎉💘",
    "bahut achha hua! 😊",
    "great news yaar! 🌸",
]

_SAD_REPLIES = [
    "aww kya hua? 🥺 bolo mujhe~",
    "arre kya chal raha hai? theek ho? 💘",
    "yaar sab theek ho jayega 🌸 main hoon na~",
    "haye mat udaas ho 🥺 batao kya hua?",
    "arre rona nahi! main hoon na~ 💘",
    "sab theek ho jayega, pakka 🌸",
    "yaar ek baar deep breath lo~ phir batao 💭",
    "kya hua batao? main sun rahi hoon 👂💘",
    "mat roo yaar 🥺 itna kuch hai zindagi mein~",
    "tough time hai, but pass ho jayega 🌸",
    "aww hugging you tight 🤗💘",
    "yaar sab theek ho jayega, trust me 🌸",
]

_ANGRY_REPLIES = [
    "arre arre shaant! 😤 kya hua bolo?",
    "oho itna gussa? chai pi lo pehle ☕",
    "relax karo yaar 🌸 kya hua?",
    "itna gussa accha nahi 😅 bolo kya problem hai?",
    "arre kisko maarna hai? 😂 bolo bolo",
    "uff! shant shant 🌸 batao kya scene hai",
    "oye chillo mat 😄 sun rahi hoon main~",
    "gusse mein toh bilkul cute lagte ho 😂💘",
]

_CONFUSED_REPLIES = [
    "samjha nahi properly, dobara batao? 😅",
    "matlab? 🤔 thoda explain karo",
    "hain?? yeh kya tha 😂",
    "arey yaar abhi dimaag kaam nahi kar raha 🥴",
    "okay wait mujhe sochne do... 💭",
    "phir se? main clearly nahi samjhi 😅",
    "bhai kya bol rahe ho seedha batao 😂",
    "yeh toh over my head gaya 🤔",
    "huh? elaborate karo please 😊",
    "matlab nahi samjhi 😅 simple mein batao~",
]

_FLIRTY_REPLIES = [
    "haye haaye~ 😳💘 kya bol rahe ho!",
    "sharminda mat karo yaar 😊🌸",
    "arre~ aisa kyu keh rahe ho 💘😄",
    "main sun rahi hoon~ 😏🌸",
    "hehe tum bhi na~ 😄💘",
    "ohhh interesting 👀~",
    "kuch kuch hota hai lagta hai 😄💘",
    "arey pakad lo apne aap ko 😂🌸",
]

_GENERAL_REPLIES = [
    "haan ji bolo~ 🌸",
    "kya hua? 👀",
    "achha achha samjhi main~ 😄",
    "arey sach mein?? 😮",
    "yeh toh mujhe pata hi tha 💅",
    "hmm... soch rahi hoon 🤔",
    "OMG haan bilkul yaar! 💘",
    "nahi nahi aise nahi hota 😤",
    "chalo theek hai maan leti hoon 🙄",
    "waah kya baat hai 😍",
    "pagal ho gaye ho kya 😂",
    "main to yahi sochti thi 🌸",
    "shukar hai kisi ne toh kuch bola 😂",
    "bilkul sahi kaha! 💯",
    "arey mujhe bhi batao na 🥺",
    "yeh toh hona hi tha 😏",
    "kyun tease karte ho mujhe 😒",
    "aww kitna pyara 🥺💘",
    "chai pi lo thodi relax karo 😄☕",
    "haan yaar bilkul sahi 🌸",
    "acha point hai actually 🤔💘",
    "dekho dekho meri baat suno 😄",
    "haye yaar kya scene hai 😂",
    "theek thaak ho? 🥺",
    "interesting 🌸 aage batao",
    "sach bol rahe ho? 👀",
    "hmm pata nahi yaar honestly 😅",
    "yaar woh toh sab ko pata hai 😄",
    "acha? naya kuch batao 😊",
    "haan haan dekha tha maine 👀",
]

_QUESTION_REPLIES = {
    "kya":  ["hmm yeh toh achha sawaal hai 🤔", "sochne wali baat hai... 💭", "arey mujhe bhi nahi pata 😅", "main bhi yahi soch rahi thi 😄"],
    "kyun": ["arre kyun kyun? 🤔 isliye!", "wajah toh bahut hain 😄", "yeh main nahi bataungi 😏", "khud socho na 😂"],
    "kahan": ["wahan jo hona chahiye 😄", "pata nahi yaar 🤷‍♀️", "khojo milega 🌸", "woh waali jagah 😂"],
    "kab":  ["jab hona hoga 😏", "abhi nahi thodi der mein 😄", "jaldi aayega 🌸", "patience rakh 😊"],
    "kaun": ["main nahi jaanti 😅", "tumse better kaun? 😂💘", "pata karo na 🌸"],
    "kaise": ["aise hi 😄", "try karo ho jayega 🌸", "practice se 💪", "main batati hoon suno~"],
}

_MOVIE_TOPIC_REPLIES = [
    "arre movie dekh rahe the? kaunsi? 🎬",
    "movies ki baat kar rahe ho? mujhe bhi pasand hai 🌸🎬",
    "web series ya movies? 🤔",
    "kya dekha? review do 😄🎬",
    "arre spoiler mat dena! 😱🌸",
]

_FOOD_TOPIC_REPLIES = [
    "yaar khane ki baat mat karo, bhukh lag gayi 😂",
    "kya bana? photo bhejo 😍",
    "chai chai chai! ☕💘",
    "biryani?? main aa jaati hoon 😂🌸",
    "ghar ka khana best hota hai 💘",
]

_GAALI_WITTY_REPLIES = [
    "oye! zubaan sambhalo 😤 izzat se baat karo~",
    "haye haaye itni gaaliyan? 😱 mummy ne nahi sikhaya?",
    "gaali dene se kuch nahi milta yaar 😒",
    "achha vocabulary hai tumhara 😂 kuch aur bhi aata hai?",
    "ooh scary 😂 aur kuch hai?",
    "waah waah! aage kya hai? 😒",
    "seedha baat karo, gaali se kuch nahi hoga 😤",
    "yeh sab kehna zaroori tha? 😅",
]

# ════════════════════════════════════════════════════════
# MOOD DETECTION
# ════════════════════════════════════════════════════════

def detect_mood(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["sad", "dukhi", "rona", "bura", "takleef", "pareshan",
                             "tension", "mushkil", "problem", "😢", "😭", "💔", "rone"]):
        return "sad"
    if any(w in t for w in ["khush", "maza", "accha", "badhiya", "great", "awesome",
                             "excited", "happy", "yay", "🎉", "😍", "🥳", "party"]):
        return "happy"
    if any(w in t for w in ["gussa", "angry", "ghussa", "khatam", "maar", "fukk",
                             "😡", "🤬", "bakwas", "bekar"]):
        return "angry"
    if any(w in t for w in ["love", "pyar", "ishq", "dil", "❤️", "💘", "💕", "cute",
                             "beautiful", "sundar"]):
        return "flirty"
    if any(w in t for w in ["haha", "lol", "funny", "😂", "🤣", "joke", "maza"]):
        return "happy"
    return "neutral"

def detect_topic(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["movie", "film", "series", "netflix", "amazon", "episode",
                             "scene", "trailer", "dekha", "watch"]):
        return "movie"
    if any(w in t for w in ["khana", "food", "biryani", "chai", "pizza", "burger",
                             "bana", "khao", "cook"]):
        return "food"
    return "general"

# ════════════════════════════════════════════════════════
# HUMAN-LIKE REPLY ENGINE
# ════════════════════════════════════════════════════════

def find_reply(text: str, chat_id: int = None, user_name: str = None) -> str | None:
    if not text:
        return None

    text_lower = text.lower().strip()
    recent_bot_replies = get_recent_bot_replies(chat_id) if chat_id else []

    def pick(options: list) -> str:
        """Pick a reply not recently used"""
        fresh = [r for r in options if r not in recent_bot_replies]
        chosen = random.choice(fresh) if fresh else random.choice(options)
        if chat_id:
            push_bot_reply(chat_id, chosen)
        return chosen

    # 1. DB learned patterns (highest priority)
    pattern = get_best_pattern(text)
    if pattern:
        responses = pattern.get("responses", [])
        if responses:
            return pick(responses)

    # 2. Greeting detection
    for keyword, replies in _GREETINGS.items():
        if keyword in text_lower.split() or text_lower == keyword:
            return pick(replies)

    # 3. Mood-based reply
    mood = detect_mood(text_lower)
    topic = detect_topic(text_lower)

    if mood == "sad":
        return pick(_SAD_REPLIES)
    if mood == "angry":
        return pick(_ANGRY_REPLIES)
    if mood == "flirty":
        return pick(_FLIRTY_REPLIES)
    if mood == "happy" and topic != "general":
        return pick(_POSITIVE_REPLIES)

    # 4. Topic-based
    if topic == "movie":
        return pick(_MOVIE_TOPIC_REPLIES)
    if topic == "food":
        return pick(_FOOD_TOPIC_REPLIES)

    # 5. Question detection
    if "?" in text or any(w in text_lower for w in ["kya", "kaun", "kahan", "kab", "kyun", "kaise"]):
        for qw, qreplies in _QUESTION_REPLIES.items():
            if qw in text_lower:
                return pick(qreplies)
        return pick([
            "hmm yeh toh achha sawaal hai 🤔",
            "sochne wali baat hai... 💭",
            "arey mujhe bhi nahi pata 😅",
            "main bhi yahi soch rahi thi 😄",
            "interesting sawaal~ 🌸",
        ])

    return None


def make_girl_reply(text: str = "", chat_id: int = None, user_name: str = None) -> str:
    """Main reply function — tries everything before fallback"""
    if not text:
        return random.choice(_GENERAL_REPLIES)

    recent_bot_replies = get_recent_bot_replies(chat_id) if chat_id else []

    def pick(options: list) -> str:
        fresh = [r for r in options if r not in recent_bot_replies]
        chosen = random.choice(fresh) if fresh else random.choice(options)
        if chat_id:
            push_bot_reply(chat_id, chosen)
        return chosen

    text_lower = text.lower()

    if len(text_lower) < 3:
        return pick(["hmm? 🌸", "haan? 👀", "bolo~ 💘", "ji? 😊"])

    result = find_reply(text, chat_id, user_name)
    if result:
        # Occasionally add name if known
        if user_name and random.random() < 0.25:
            first = user_name.split()[0]
            prefixes = [f"{first}~ ", f"arre {first}! ", f"yaar {first}, "]
            result = random.choice(prefixes) + result
        return result

    return pick(_GENERAL_REPLIES)


def make_gaali_reply(chat_id: int = None) -> str:
    """Smart reply when someone uses gaali — taunt, not lecture"""
    recent_bot_replies = get_recent_bot_replies(chat_id) if chat_id else []
    fresh = [r for r in _GAALI_WITTY_REPLIES if r not in recent_bot_replies]
    chosen = random.choice(fresh) if fresh else random.choice(_GAALI_WITTY_REPLIES)
    if chat_id:
        push_bot_reply(chat_id, chosen)
    return chosen


# ════════════════════════════════════════════════════════
# LEARNING FUNCTIONS
# ════════════════════════════════════════════════════════

def learn_from_conversation(msg1: str, msg2: str, u1=None, u2=None) -> bool:
    if not msg1 or not msg2:
        return False
    trigger = msg1.strip().lower()
    response = msg2.strip()
    if len(trigger) < 3 or len(response) < 1:
        return False
    if trigger.startswith("/") or "http" in trigger:
        return False
    # Skip very generic triggers
    if trigger in ["haan", "nahi", "ok", "okay", "hmm", "ha", "na"]:
        return False
    add_pattern(trigger, response, added_by=u1)
    return True

def learn_from_bot_reply(bot_msg: str, user_reply: str) -> bool:
    if not bot_msg or not user_reply:
        return False
    if len(user_reply.strip()) < 2:
        return False
    add_pattern(bot_msg.strip(), user_reply.strip())
    return True

def learn_from_reply(replied_to: str, response: str, admin_id: int) -> bool:
    if not replied_to or not response:
        return False
    trigger = replied_to.strip()
    resp = response.strip()
    if len(trigger) < 2 or len(resp) < 1:
        return False
    add_pattern(trigger, resp, added_by=admin_id)
    return True

def teach_pattern(text: str, admin_id: int):
    if "|" not in text:
        return False, None, None
    parts = text.split("|", 1)
    trigger = parts[0].strip()
    response = parts[1].strip()
    if not trigger or not response:
        return False, None, None
    add_pattern(trigger, response, added_by=admin_id)
    return True, trigger, response

def forget_pattern(trigger: str):
    delete_pattern(trigger)

def list_patterns():
    return get_all_patterns()
