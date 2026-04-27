import os
import asyncio
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatMemberHandler,
    filters
)

from handlers.events  import (
    start_handler, my_chat_member_handler,
    new_member_handler, left_member_handler,
    callback_handler
)
from handlers.admin   import (
    ban_handler, unban_handler, mute_handler,
    unmute_handler, kick_handler, warn_handler,
    pin_handler, setwelcome_handler,
    blockuser_handler, unblockuser_handler,
    teach_handler, forget_handler,
    patterns_handler, broadcast_handler
)
from handlers.user    import (
    help_handler, font_handler, shayari_handler,
    joke_handler, compliment_handler,
    roast_handler, about_handler,
    id_handler, sticker_handler
)
from handlers.chat import message_handler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ── Build Application ─────────────────────────────────────────────────

def build_app():
    application = Application.builder().token(BOT_TOKEN).build()

    # Events
    application.add_handler(CommandHandler("start",      start_handler))
    application.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member_handler))
    application.add_handler(CallbackQueryHandler(callback_handler))

    # Admin commands
    application.add_handler(CommandHandler("ban",        ban_handler))
    application.add_handler(CommandHandler("unban",      unban_handler))
    application.add_handler(CommandHandler("mute",       mute_handler))
    application.add_handler(CommandHandler("unmute",     unmute_handler))
    application.add_handler(CommandHandler("kick",       kick_handler))
    application.add_handler(CommandHandler("warn",       warn_handler))
    application.add_handler(CommandHandler("pin",        pin_handler))
    application.add_handler(CommandHandler("setwelcome", setwelcome_handler))
    application.add_handler(CommandHandler("block",      blockuser_handler))
    application.add_handler(CommandHandler("unblock",    unblockuser_handler))
    application.add_handler(CommandHandler("teach",      teach_handler))
    application.add_handler(CommandHandler("forget",     forget_handler))
    application.add_handler(CommandHandler("patterns",   patterns_handler))
    application.add_handler(CommandHandler("broadcast",  broadcast_handler))

    # User commands
    application.add_handler(CommandHandler("help",       help_handler))
    application.add_handler(CommandHandler("font",       font_handler))
    application.add_handler(CommandHandler("shayari",    shayari_handler))
    application.add_handler(CommandHandler("joke",       joke_handler))
    application.add_handler(CommandHandler("compliment", compliment_handler))
    application.add_handler(CommandHandler("roast",      roast_handler))
    application.add_handler(CommandHandler("about",      about_handler))
    application.add_handler(CommandHandler("id",         id_handler))
    application.add_handler(CommandHandler("sticker",    sticker_handler))

    # Smart chat
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message_handler
    ))

    return application

# ── FastAPI ───────────────────────────────────────────────────────────

app = FastAPI()
tg_app = build_app()

@app.on_event("startup")
async def startup():
    await tg_app.initialize()

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return Response(content="ok", status_code=200)

@app.get("/")
async def root():
    return {"status": "Cutie Pie Bot is running 💘"}

@app.get("/set_webhook")
async def set_webhook(request: Request):
    host = str(request.base_url).rstrip("/")
    url  = f"{host}/webhook"
    result = await tg_app.bot.set_webhook(url)
    return {"webhook_set": result, "url": url}

# Vercel ke liye zaroori
handler = app
