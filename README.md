# ⎯᪵⎯꯭̽💘꯭᪳ ⃪𝗖𝘂꯭𝘁𝗶𝗲꯭ 𝗣𝗶꯭𝗲 ⃪🌸 Bot

Smart self-learning Telegram group bot — Vercel + MongoDB

---

## 📁 File Structure

```
cutie-pie-bot/
├── api/
│   └── index.py          ← Vercel entry point (webhook)
├── handlers/
│   ├── events.py         ← Join/leave/start/log events
│   ├── admin.py          ← Admin commands
│   ├── user.py           ← User commands
│   └── chat.py           ← Smart chat + self-learning
├── core/
│   ├── db.py             ← MongoDB handler
│   ├── persona.py        ← Bot personality, fonts, replies
│   └── brain.py          ← Self-learning system
├── vercel.json
└── requirements.txt
```

---

## 🚀 Deploy on Vercel — Step by Step

### Step 1: GitHub pe upload karo

1. GitHub pe new repository banao
2. Ye saari files upload karo
3. Repository public rakho

### Step 2: Vercel pe deploy karo

1. [vercel.com](https://vercel.com) pe jao
2. "New Project" → GitHub repo select karo
3. Deploy karo

### Step 3: Environment Variables set karo

Vercel Dashboard → Project → Settings → Environment Variables

```
BOT_TOKEN       = your_bot_token_here
MONGODB_URI     = your_mongodb_uri_here
LOG_CHANNEL_ID  = your_log_channel_id (e.g. -1001234567890)
ADMIN_ID        = your_telegram_user_id
```

### Step 4: Webhook set karo

Deploy hone ke baad browser mein yeh URL kholo:

```
https://your-vercel-url.vercel.app/set_webhook
```

Ek baar khola, webhook set ho jayega. Done! ✅

---

## 🧠 Self-Learning Kaise Kaam Karta Hai

### Method 1 — Admin reply method:
1. Group mein koi bhi message aaye
2. Admin us message ko **reply kare** apna jawab likh ke
3. Bot seekh leti hai: "yeh message aaye toh yeh reply karo"

### Method 2 — /teach command:
```
/teach hello kaise ho | Heyy! Main theek hoon~ 🌸
/teach kya kar rahi ho | Bas tumse baat kar rahi hoon 💘
```

### Pattern delete karna:
```
/forget hello kaise ho
```

### Saare patterns dekhna:
```
/patterns
```

---

## 👑 Admin Commands

| Command | Kaam |
|---------|------|
| `/ban @user` | User ban |
| `/unban @user` | Unban |
| `/mute @user` | Mute |
| `/unmute @user` | Unmute |
| `/kick @user` | Kick |
| `/warn @user` | Warning (3 pe auto-ban) |
| `/pin` | Message pin (reply kar ke) |
| `/setwelcome msg` | Welcome message set |
| `/block @user` | Bot level block |
| `/unblock @user` | Bot level unblock |
| `/teach t \| r` | Pattern sikhao |
| `/forget trigger` | Pattern bhulao |
| `/patterns` | Saare patterns dekho |
| `/broadcast msg` | Sab ko message |

---

## 👤 User Commands

| Command | Kaam |
|---------|------|
| `/start` | Bot se milo |
| `/help` | Help menu |
| `/about` | Bot ke baare mein |
| `/font text` | Stylish font |
| `/shayari` | Shayari suno |
| `/joke` | Joke suno |
| `/compliment` | Compliment lo |
| `/roast @user` | Roast karo |
| `/id` | Apni/group ID dekho |
| `/sticker` | Sticker bhejo |

---

## 🎭 Bot Behaviour in Group

- **Sirf tab bolegi** jab @mention ho ya trigger word aaye
- **5-6 messages ke baad** kabhi kabhi beech mein bol degi
- **Orphan message** pe 8% chance reply
- **Typing indicator** reply se pehle dikhti hai
- **12% chance** pe sticker bhi bhejti hai reply ke sath
- **Bure words** pe nakhre wala jawab (ban nahi)

---

## 🎭 Sticker IDs Set Karna

`core/persona.py` mein STICKERS dict mein apne sticker file_ids daalo:

```python
STICKERS = {
    "happy":    ["file_id_1", "file_id_2"],
    "angry":    ["file_id_3", "file_id_4"],
    ...
}
```

Sticker ka file_id paane ke liye: koi sticker bot pe bhejo, `/id` se dekho ya @JsonDumpBot use karo.

---

## 📋 Log Channel Setup

1. Ek private channel banao
2. Bot ko admin banao us channel mein
3. Channel ID copy karo (e.g. `-1001234567890`)
4. Vercel mein `LOG_CHANNEL_ID` mein daalo

Log channel mein yeh aayega:
- 🟢 Bot kisi group mein add hua + link
- 🔴 Bot group se nikala gaya
- 👤 Naya user /start kiya + profile link

---

## ⚠️ MongoDB Atlas Free Setup

1. [mongodb.com/atlas](https://mongodb.com/atlas) pe free account banao
2. Free M0 cluster banao
3. Database user banao
4. IP Whitelist mein `0.0.0.0/0` daalo (sab allow)
5. Connection string copy karo:
   ```
   mongodb+srv://username:password@cluster.mongodb.net/cutie_pie_bot
   ```
6. Vercel mein `MONGODB_URI` mein daalo
