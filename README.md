<div align="center">

```
░█████╗░░██████╗  ░██████╗░██████╗░░█████╗░██╗░░░██╗██████╗░  ██████╗░░█████╗░████████╗
██╔══██╗██╔════╝  ██╔════╝░██╔══██╗██╔══██╗██║░░░██║██╔══██╗  ██╔══██╗██╔══██╗╚══██╔══╝
███████║╚█████╗░  ██║░░██╗░██████╔╝██║░░██║██║░░░██║██████╔╝  ██████╦╝██║░░██║░░░██║░░░
██╔══██║░╚═══██╗  ██║░░╚██╗██╔══██╗██║░░██║██║░░░██║██╔═══╝░  ██╔══██╗██║░░██║░░░██║░░░
██║░░██║██████╔╝  ╚██████╔╝██║░░██║╚█████╔╝╚██████╔╝██║░░░░░  ██████╦╝╚█████╔╝░░░██║░░░
╚═╝░░╚═╝╚═════╝░  ╚═════╝░╚═╝░░╚═╝░╚════╝░░╚═════╝░╚═╝░░░░░  ╚═════╝░░╚════╝░░░░╚═╝░░░
```

# ᴀꜱ ɢʀᴏᴜᴘ ʙᴏᴛ 🌸

**Advanced Telegram Group Manager | Vercel + MongoDB | Hinglish Style**

[![Deploy on Vercel](https://img.shields.io/badge/Deploy%20on-Vercel-black?style=for-the-badge&logo=vercel)](https://vercel.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%20Free-green?style=for-the-badge&logo=mongodb)](https://mongodb.com/atlas)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://t.me/asbhaibsr)

*Group ka thanedar — gaali doge toh ban, rules todoge toh ban, attitude dikhaya toh bhi ban* 😂

</div>

---

## ✨ Features

### 🆓 Free (Sab Groups ke liye)
| Feature | Description |
|---------|-------------|
| 🤬 Anti-Gaali | 200+ Hindi/English words + leetspeak detection |
| 📝 Notes System | `#notename` se instant notes |
| 🤖 Smart AI Chat | Human-like Hinglish replies |
| ⚠️ Warn System | Progress bar + auto-ban on limit |
| 🔨 Ban/Mute/Kick | Full moderation tools |
| 👋 Welcome/Goodbye | Custom messages with variables |
| 📌 Pin/Purge | Message management |
| 🏷️ Tag All | Sab members ko tag |
| 🔍 Filters | Auto-reply keyword system |

### 👑 Premium Only
| Feature | Description |
|---------|-------------|
| 🔗 Anti-Link | Telegram links block |
| 👤 Anti-Username Promo | Bio link spam block |
| 🛡️ Anti-Raid | Auto-lock on mass join |
| 🎬 Movie System | File copyright protection |
| 🤖 Button Captcha | New member verification |
| 📊 Analytics | Group stats + top users |
| ⏰ Scheduler | Daily timed messages |
| 🗑️ Auto-Delete | Media auto-delete timer |
| ⚡ Flood Control | Spam protection |

---

## 🚀 Deploy on Vercel (Free)

### Step 1 — Fork & Clone
```bash
git clone https://github.com/yourusername/tgchatbot
cd tgchatbot
```

### Step 2 — Vercel Setup
```bash
npm i -g vercel
vercel login
vercel --prod
```

### Step 3 — Environment Variables
Vercel Dashboard → Project → Settings → Environment Variables mein yeh sab add karo:

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | BotFather se liya token | `1234567890:AAF...` |
| `WEBHOOK_URL` | Tumhara Vercel URL | `https://tgchatbot-xxx.vercel.app` |
| `ADMIN_ID` | Tumhara Telegram User ID | `123456789` |
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb+srv://...` |
| `LOG_CHANNEL_ID` | Log channel ID (optional) | `-100123456789` |
| `PREMIUM_PRICE` | Premium price in ₹ | `99` |
| `CRON_SECRET` | Cron job secret key | `any_random_string` |
| `API_ID` | Pyrogram API ID (optional, for /learnfromgroups) | `12345` |
| `API_HASH` | Pyrogram API Hash (optional) | `abcdef...` |
| `USERBOT_SESSION` | Pyrogram session string (optional) | `BQA...` |

### Step 4 — Webhook Set karo
Deploy ke baad yeh URL kholo:
```
https://your-vercel-url.vercel.app/set_webhook
```
✅ `{"ok": true}` aaya? Bot ready hai!

### Step 5 — Debug Check
```
https://your-vercel-url.vercel.app/debug
```

---

## 📋 BotFather Commands

> **Copy karo → BotFather mein `/setcommands` → Paste karo** ✅

```
start - Bot start karo 🚀
help - Commands dekho 📖
settings - Group settings panel ⚙️
ban - User ban karo 🔨
unban - User unban karo 🔓
mute - User mute karo 🔇
unmute - User unmute karo 🔊
kick - User kick karo 👟
warn - Warning do ⚠️
warns - Warnings dekho 📊
resetwarn - Warnings reset karo 🔄
pin - Message pin karo 📌
unpin - Message unpin karo
del - Message delete karo 🗑
purge - Multiple msgs delete karo
promote - Admin banao 👑
demote - Admin hatao
tagall - Sab ko tag karo 📢
stoptagall - Tagging rokao ✋
lock - Content lock karo 🔒
unlock - Content unlock karo 🔓
setwelcome - Welcome message set karo 👋
setgoodbye - Goodbye message set karo 🚪
setrules - Group rules set karo 📋
save - Note save karo 📝
get - Note get karo
notes - All notes dekho
delnote - Note delete karo
filter - Auto-reply filter set karo 🎯
filters - Sab filters dekho
stop - Ek filter hatao
stopall - Sab filters hatao
schedule - Daily message schedule karo ⏰
unschedule - Schedule cancel karo
slowmode - Slowmode set karo 🐢
floodlimit - Flood limit set karo
autodel - Auto-delete set karo
warnlimit - Warn limit set karo
adminlist - Admins list dekho 👮
id - User/Chat ID dekho 🆔
whois - User info dekho 🔍
stats - Group statistics dekho 📊
topusers - Top chatters dekho 🏆
report - Admin ko report karo 🚨
font - Fancy font converter ✨
rules - Group rules dekho 📋
premium - Premium info dekho 👑
subscribe - Premium lene ke liye 💳
biofree - Bio link permission do 🧬
```

---

## 🗂️ Project Structure

```
tgchatbot/
├── api/
│   └── index.py          # FastAPI app — webhook + all routes
├── handlers/
│   ├── admin.py          # 2600+ lines — moderation, settings, premium
│   ├── chat.py           # Message handler — AI, anti-gaali, captcha
│   ├── events.py         # New member, left, start, callback router
│   ├── filters.py        # Auto-reply filter system
│   └── user.py           # Help menu, /rules, /font, /premium
├── core/
│   ├── brain.py          # AI reply engine — pattern matching + learn
│   ├── db.py             # MongoDB — ALL database functions
│   ├── persona.py        # Bot name, welcome/goodbye messages
│   └── userbot.py        # Pyrogram session — learn from groups
├── vercel.json           # Vercel config
└── requirements.txt      # Dependencies
```

---

## 🗃️ MongoDB Collections

> Sab MongoDB Atlas Free Tier pe chalta hai (512MB — kaafi hai!)

| Collection | Stores |
|------------|--------|
| `users` | User info + message count |
| `groups` | Group settings + premium status |
| `warns` | User warnings per group |
| `notes` | Saved notes per group |
| `patterns` | AI learned reply patterns |
| `filters` | Auto-reply keyword filters |
| `scheduled` | Scheduled daily messages |
| `captcha` | Active captcha sessions |
| `bio_permissions` | Bio link permissions |
| `sticker_packs` | Owner's global sticker packs |
| `bot_replies` | Recent bot reply dedup (Vercel-safe) |
| `pending_deletes` | Auto-delete queue |

---

## ⚙️ Settings Panel (`/settings`)

Bot ka pura control `/settings` se:

```
📌 Welcome ON/OFF
📌 Goodbye ON/OFF  
📌 Anti-Gaali ON/OFF
📌 Anti-Link (Premium)
📌 Anti-Raid (Premium)
📌 Captcha (Premium)
📌 AI Chatbot % (0-100%)
📌 Movie System (Premium)
📌 Flood Control (Premium)
📌 Auto-Delete (Premium)
```

---

## 💡 Filters System

```bash
# Text filter
/filter 'keyword' Yeh reply aayegi

# Media filter (reply to image/video se)  
/filter 'keyword'

# Button wala filter
/filter 'keyword' Click here! [Button Text](https://example.com)

# Dekhne ke liye
/filters

# Delete karne ke liye
/stop 'keyword'
/stopall
```

---

## 📝 Notes System

```bash
# Save
/save welcome Iss group mein swagat hai!

# Get
/get welcome
# Ya directly type karo:
#welcome

# List
/notes

# Delete
/delnote welcome
```

---

## 🧠 AI Learning

```bash
# Manually teach karo
/teach trigger=reply here

# Forget karo
/forget trigger

# Patterns list
/patterns

# Groups se seekhna (Pyrogram session chahiye)
/learnfromgroups
```

---

## 🎬 Movie System (Premium)

1. Bot ko **File Log Channel** mein add karo (admin)
2. `FILE_LOG_CHANNEL` env var set karo
3. Files us channel mein forward karo — bot automatically index karega
4. Group mein movie naam type karo → bot dhundke dega

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot respond nahi kar raha | `/set_webhook` URL visit karo |
| `AttributeError` on startup | `requirements.txt` check karo |
| MongoDB connection fail | `MONGODB_URI` format check karo |
| Warn buttons kaam nahi | `events.py` mein `warn_dismiss_` routing check karo |
| `/learnfromgroups` fail | `API_ID`, `API_HASH`, `USERBOT_SESSION` env vars set karo |

---

## 🔐 Security

- Bot Token kabhi GitHub pe push mat karo
- `CRON_SECRET` random strong value rakho
- MongoDB Atlas mein IP whitelist `0.0.0.0/0` karo (Vercel ke liye)
- Admin ID sahi set karo — sirf usi ko owner commands milenge

---

## 📞 Support

- **Owner:** [@asbhaibsr](https://t.me/asbhaibsr)
- **Channel:** [@asbhai_bsr](https://t.me/asbhai_bsr)
- **Group:** [@aschat_group](https://t.me/aschat_group)

---

<div align="center">

**Made with 💘 by @asbhaibsr**

*"Group ka thanedar — rules todne walon ka koi future nahi" 😂*

</div>
