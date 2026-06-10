# 🌸 AS Group Bot — Complete Guide

> **Vercel + MongoDB | Python Telegram Bot | Smart AI Chatbot | Advanced Group Manager**
> By [@asbhaibsr](https://t.me/asbhaibsr) | Updates: [@asbhai_bsr](https://t.me/asbhai_bsr)

---

## 📁 Project Structure

```
tgchatbot/
├── api/
│   └── index.py           ← Vercel entry (FastAPI + webhook)
├── handlers/
│   ├── events.py          ← Join/leave/start/callback events
│   ├── admin.py           ← Admin commands
│   ├── user.py            ← User commands + help
│   ├── chat.py            ← AI chatbot + anti-spam
│   └── filters.py         ← 🆕 Keyword filter system
├── core/
│   ├── db.py              ← MongoDB (all collections)
│   ├── brain.py           ← Self-learning AI
│   └── persona.py         ← Bot personality
├── requirements.txt
└── vercel.json
```

---

## 🚀 Deploy on Vercel

### Step 1 — GitHub

1. New GitHub repository banao
2. Ye saari files upload/push karo

### Step 2 — Vercel

1. [vercel.com](https://vercel.com) → "New Project" → GitHub repo select
2. Deploy karo (Python serverless automatically detect hoga)

### Step 3 — Environment Variables

Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | BotFather se mila token |
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster.../cutie_pie_bot` |
| `ADMIN_ID` | Tumhara Telegram user ID |
| `LOG_CHANNEL_ID` | Log channel ID (e.g. `-1001234567890`) |
| `FILE_LOG_CHANNEL` | Movie file log channel ID |
| `WEBHOOK_URL` | `https://your-project.vercel.app` |
| `PREMIUM_PRICE` | `99` (default) |
| `CRON_SECRET` | Random secret string |

### Step 4 — Webhook Set Karo

Deploy ke baad browser mein kholo:
```
https://your-project.vercel.app/set_webhook
```

✅ `{"ok": true}` aaye toh sab theek hai!

---

## 🔑 Filter System — Full Guide

Filter = Jab koi group mein koi keyword likhe, bot automatically reply kare.

### ➕ Filter Lagana

**Simple text filter:**
```
/filter 'hello' Namaste! Kaise ho? 🌸
```

**Multi-word keyword:**
```
/filter 'kya hal' Mast hoon bhai, aur tum? 😄
```

**Media filter** (photo/sticker/document/video reply karke):
1. Jo photo/sticker/file use karni hai usse reply karo
2. Command likho:
```
/filter 'rules dekho'
```

**Media + caption:**
```
/filter 'join karo' Hamare channel mein aao!
```
*(kisi photo ko reply karte hue)*

**Buttons wala filter:**
```
/filter 'channel' Hamare channel join karo!
[📢 Channel](https://t.me/asbhai_bsr) [🌐 Website](https://astoolswala.online)
[📞 Contact](https://t.me/asbhaibsr)
```

**Button syntax rules:**
- `[Button Text](https://url.com)` — URL button
- `[Btn1](url1) [Btn2](url2)` — Same line = same row
- `[Btn3](url3)` — Next line = next row

**Ek keyword ke multiple responses:**
```
/filter 'hi' Heyy! 😊
/filter 'hi' Kya haal hai? 🌸
/filter 'hi' Hello ji! Kaise hain aap? 💘
```
*(Teeno mein se random ek reply aayega)*

---

### 📋 Filters List Dekhna

```
/filters
```

Output:
```
📋 Group Name — Filters (5)

1. channel 🖼 🔘 — 1 response
2. hello 📝 — 3 responses
3. join karo 📝 — 1 response
4. rules 📄 — 1 response
5. website 📝 🔘 — 2 responses
```

Icons:
- 📝 Text  |  🖼 Photo  |  😄 Sticker  |  📄 Document
- 🎬 Video  |  🎵 Audio  |  🎞 GIF  |  🎤 Voice  |  🔘 Buttons

---

### ❌ Filter Delete Karna

**Ek filter delete:**
```
/stop 'hello'
/stop hello
```

**Sab filters delete:**
```
/stopall
```

---

## 👮 Admin Commands — Full List

### Moderation

| Command | Description |
|---------|-------------|
| `/ban` | Reply ya ID se ban karo |
| `/unban` | Unban karo |
| `/mute [1h/30m/1d]` | Mute karo (time optional) |
| `/unmute` | Unmute karo |
| `/kick` | Group se kick karo |
| `/warn [reason]` | Warning do (3 pe auto-ban) |
| `/warns` | Kisi ke warns dekho |
| `/resetwarn` | Warns reset karo |

### Messages

| Command | Description |
|---------|-------------|
| `/pin` | Message pin (reply kar ke) |
| `/unpin` | Unpin karo |
| `/del` | Ek message delete (reply kar ke) |
| `/purge` | Reply se aage sab delete |

### Promotions

| Command | Description |
|---------|-------------|
| `/promote` | Admin banao |
| `/demote` | Admin hatao |
| `/adminlist` | Sab admins list |

### Group Settings

| Command | Description |
|---------|-------------|
| `/settings` | Full toggle panel |
| `/setwelcome {name} {group}` | Custom welcome message |
| `/setgoodbye` | Custom goodbye |
| `/setrules text` | Group rules set |
| `/lock stickers/gifs/polls/media/voice` | Lock karo |
| `/unlock type` | Unlock karo |
| `/slowmode [sec]` | Slowmode set |

### Filters (🆕)

| Command | Description |
|---------|-------------|
| `/filter 'keyword' text` | Filter set karo |
| `/filter 'kw'` *(reply)* | Media filter |
| `/filters` | Sab filters list |
| `/stop 'keyword'` | Ek filter delete |
| `/stopall` | Sab filters delete |

### Notes System

| Command | Description |
|---------|-------------|
| `/save name content` | Note save karo |
| `/get name` | Note retrieve |
| `/notes` | All notes list |
| `/delnote name` | Note delete |
| `#notename` | Anywhere type karo → auto-reply |

### Welcome / Rules

| Command | Description |
|---------|-------------|
| `/setwelcome {name} {group}` | Custom welcome |
| `/setgoodbye` | Custom goodbye |
| `/setrules text` | Rules set |
| `/rules` | Rules dekho |

### Analytics (Premium 👑)

| Command | Description |
|---------|-------------|
| `/stats` | Group statistics |
| `/topusers` | Top chatters list |
| `/whois` | User full info |

### Scheduled Messages (Premium 👑)

| Command | Description |
|---------|-------------|
| `/schedule HH:MM text` | Daily auto-message |
| `/unschedule` | Schedule cancel |

### Advanced (Premium 👑)

| Command | Description |
|---------|-------------|
| `/floodlimit N` | Flood limit set |
| `/autodel sec` | Auto-delete timer |
| `/warnlimit N` | Max warns before ban |
| `/unlock_raid` | Raid ke baad group unlock |
| `/tagall [msg]` | Sab active members tag |
| `/stoptagall` | Tagall rok do |

---

## 👤 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Bot se milo |
| `/help` | Help menu (interactive) |
| `/rules` | Group rules dekho |
| `/id` | Apni/kisi ki ID dekho |
| `/whois` | User profile info |
| `/premium` | Premium info + subscribe |
| `/report reason` | Admin ko alert (reply karke) |
| `/font text` | Fancy text convert |
| `/adminlist` | Admins ki list |
| `#notename` | Note directly get karo |

---

## 🤖 Owner Commands

*(Sirf bot owner ke liye)*

| Command | Description |
|---------|-------------|
| `/broadcast msg` | Sab users ko message |
| `/addprem chat_id days` | Premium do |
| `/remprem chat_id` | Premium hatao |
| `/premiumstats` | Premium groups list |
| `/teach trigger \| response` | Pattern sikhao |
| `/forget trigger` | Pattern bhulao |
| `/patterns` | Sab patterns dekho |
| `/blockuser user_id` | Bot se block |
| `/unblockuser user_id` | Bot se unblock |

---

## ⚙️ Settings Panel — /settings

```
✅ Chatbot       ✅ Welcome
✅ Goodbye       ❌ Anti-Gaali 🆓
❌ Anti-Username  ❌ Anti-Link 👑
[👑 Unlock Premium Features]
[⚡ Flood Limit]  [⏱ Auto-Del Time]
[🔒 Lock Types]   [⚠️ Warn Limit]
```

**Free Features:**
- Chatbot, Welcome, Goodbye
- Anti-Gaali (200+ Hindi/English abusive words)
- Anti-Username Promo
- Notes, Filters, Warns, Pin/Del/Purge

**Premium 👑 Features:**
- Anti-Link, Anti-Forward, Anti-Raid
- Captcha for new members
- Flood control, Auto-delete
- Movie/file system
- Scheduled messages
- Full analytics

---

## 🧠 Self-Learning System

### Method 1 — Admin Reply
1. Koi bhi message aaye group mein
2. Admin us message ko **reply kare** apna jawab likh ke
3. Bot seekh leti hai → agle baar aise message pe wahi reply

### Method 2 — /teach
```
/teach trigger word | jawab text
/teach kya hal | Mast hoon bhai!
/teach good morning | Good morning! ☀️ Kaise ho?
```

### Method 3 — Auto Learning
Bot automatically conversation patterns observe karke seekhti hai.

### Patterns manage:
```
/forget trigger word     ← ek pattern bhulao
/patterns               ← sab patterns dekho
```

---

## 🎬 Movie/File System (Premium)

Enabled by `/settings` → Movie Sys toggle.

**Kaise kaam karta hai:**
1. Admin group mein movie file bhejta hai (doc/video)
2. Bot automatically file ko log channel mein store karta hai
3. Duplicate files automatically detect hoti hain
4. Caption modes: HARD (full copyright notice) / SOFT / NONE

---

## 🛡 Copyright & Disclaimer

Bot ke messages mein automatically yeh protection hai:

```
⚠️ This content is for educational purposes only.
All rights reserved © AS Group Bot
Unauthorized redistribution prohibited.
```

**Bot Ban Prevention:**
- Bot kabhi bhi NSFW ya illegal content share nahi karta
- Movie system sirf registered admins ke liye hai
- Anti-spam features active hain
- Log channel mein sab activity record hoti hai

---

## 💬 Delete Bot Messages

Kisi bhi bot message ko delete karne ke liye:
1. Bot ke message ko **select/reply** karo
2. `/del` command use karo

Ya purge use karo multiple messages ke liye:
```
/purge         ← reply se aage sab delete
```

---

## 📊 MongoDB Setup (Free)

1. [mongodb.com/atlas](https://mongodb.com/atlas) → Free M0 cluster
2. Database user banao
3. IP: `0.0.0.0/0` allow karo
4. Connection string:
   ```
   mongodb+srv://USERNAME:PASSWORD@cluster.mongodb.net/cutie_pie_bot
   ```
5. Vercel env mein `MONGODB_URI` set karo

**Collections automatically banti hain:**
- `users`, `groups`, `filters`, `notes`, `warnings`
- `patterns`, `analytics`, `captcha_pending`
- `scheduled_msgs`, `raid_joins`, `tagall_jobs`

---

## 🔧 Local Testing

```bash
pip install python-telegram-bot==20.7 pymongo fastapi uvicorn httpx

# .env file banao:
export BOT_TOKEN="your_token"
export MONGODB_URI="your_uri"
export ADMIN_ID="your_id"
export WEBHOOK_URL="https://your-domain.vercel.app"

uvicorn api.index:app --reload --port 8000
```

---

## 📜 Changelog

### v2.0 — Filter System Added 🆕
- `/filter` — Keyword auto-reply (text/photo/sticker/doc/video)
- `/filters` — List all filters
- `/stop` — Delete specific filter
- `/stopall` — Clear all filters
- Inline button support `[text](url)` syntax
- Multiple responses per keyword (random pick)

### v1.5 — Bug Fixes
- Fixed `filters.STICKER` AttributeError → `filters.Sticker.ALL`
- Fixed `unlock_raid_handler` import error

### v1.0 — Initial Release
- AI Chatbot, Anti-Gaali, Notes, Warns
- Premium system, Movie file system
- Anti-Raid, Captcha, Analytics

---

## 📞 Support

- Telegram: [@asbhaibsr](https://t.me/asbhaibsr)
- Channel: [@asbhai_bsr](https://t.me/asbhai_bsr)
- Website: [astoolswala.online](https://astoolswala.online)

---

*Made with 💘 by @asbhaibsr*
