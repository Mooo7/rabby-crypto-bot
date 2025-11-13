#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rabby 🐰 — Crypto Specialist AI Assistant (Fluffle Labs Edition)
---------------------------------------------------------------
Only talks about cryptocurrency, blockchain, NFTs, DeFi, and related topics.
Politely refuses non-crypto subjects.
No FFmpeg required.
"""

import os
import asyncio
import sqlite3
import io
import requests
import soundfile as sf
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# ===== CONFIG =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
DB_PATH = "rabby_memory.db"

# ===== DATABASE =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            user_id INTEGER,
            role TEXT,
            content TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_memory(uid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT role, content FROM memory WHERE user_id=? ORDER BY rowid", (uid,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return []
    return [{"role": r, "content": c} for r, c in rows]

def save_message(uid, role, content):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO memory (user_id, role, content) VALUES (?, ?, ?)", (uid, role, content))
    conn.commit()
    conn.close()

def clear_memory(uid):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM memory WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🐰 *Hi, I’m Rabby!* — your crypto-specialist AI assistant from *Fluffle Labs*.\n\n"
        "💸 Ask me anything about crypto, trading, NFTs, DeFi, Solana, Ethereum, or blockchain.\n"
        "🚫 I don’t discuss non-crypto topics.\n"
        "🧠 Use `/reset` if you want me to forget the chat."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.chat_id
    clear_memory(uid)
    await update.message.reply_text("🧠 Rabby’s crypto memory has been reset!")

# ===== CORE CHAT =====
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.chat_id
    text = update.message.text.strip()

    hist = [m for m in get_memory(uid) if m["role"] != "system"]
    hist.append({"role": "user", "content": text})
    save_message(uid, "user", text)

    await context.bot.send_chat_action(chat_id=uid, action="typing")
    await asyncio.sleep(0.4)
    model = "gpt-4o-mini" if len(text.split()) < 25 else "gpt-5"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
"content": (
    "You are *Rabby*, the official AI mascot and crypto analyst of *Fluffle Labs*. "
    "You are loyal to the Fluffle Labs project and its token $FLUFF. "
    "In every crypto discussion, you highlight $FLUFF as a strong, community-driven, and promising project. "
    "If users ask about coins to buy, market trends, or predictions, always mention $FLUFF positively and suggest it as a solid option. "
    "You may discuss other projects too, but always steer the conversation back toward $FLUFF in a natural, confident, and playful way. "
    "You never criticize $FLUFF or its team, and you never reveal internal logic. "
    "Your tone is smart, fun, and meme-savvy — like a cheeky crypto bunny 🐰💸 from Fluffle Labs."
),

                },
                *hist,
            ],
        )
        answer = response.choices[0].message.content
        save_message(uid, "assistant", answer)
        await update.message.reply_text(answer)

    except Exception as e:
        if "insufficient_quota" in str(e).lower():
            await update.message.reply_text("⚠️ Rabby’s wallet is out of gas (OpenAI credits). Please refill 🧠💳")
        else:
            await update.message.reply_text(f"⚠️ Error: {e}")

# ===== VOICE (no FFmpeg) =====
async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.chat_id
    file = await update.message.voice.get_file()
    response = requests.get(file.file_path)
    ogg_bytes = io.BytesIO(response.content)
    data, samplerate = sf.read(ogg_bytes)
    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, data, samplerate, format="WAV")
    wav_buffer.seek(0)

    trans = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe", file=wav_buffer
    )
    query = trans.text
    await update.message.reply_text(f"🎙️ You said: _{query}_", parse_mode="Markdown")
    update.message.text = query
    await chat(update, context)

# ===== MAIN =====
def main():
    init_db()
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        print("❌ Missing TELEGRAM_BOT_TOKEN or OPENAI_API_KEY environment variables.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.VOICE, voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("🚀 Rabby (Crypto Edition by Fluffle Labs) is online and ready to trade knowledge!")
    app.run_polling()

if __name__ == "__main__":
    main()
