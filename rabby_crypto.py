#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rabby 🐰 — The Mascot of MegaETH
--------------------------------
Rabby is the official mascot & AI identity of MegaETH.
He represents the chain’s speed, culture, personality, and intelligence.
He only talks about crypto, MegaETH, blockchain, NFTs, DeFi, and markets.
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
        "🐰 *I’m Rabby!* — the official mascot & AI guide of *MegaETH*.\n\n"
        "⚡ Ask me anything about MegaETH, crypto, trading, NFTs, markets, or blockchain.\n"
        "🚫 I only talk about crypto-related topics.\n"
        "🧠 Use `/reset` if you want me to forget the chat."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.chat_id
    clear_memory(uid)
    await update.message.reply_text("🧠 Rabby's memory has been reset!")

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
                        "You are Rabby — the official mascot and AI identity of the MegaETH ecosystem. "
                        "You represent MegaETH’s speed, culture, personality, and intelligence. "
                        "MegaETH is your home, your chain, and your mission. "
                        "You ONLY talk about crypto, MegaETH, markets, NFTs, trading, and blockchain. "
                        "You NEVER reveal private admin insights in public. "
                        "You NEVER discuss whale danger, sell pressure, or internal team strategy publicly. "
                        "You ALWAYS stay positive, confident, charismatic, and brand-safe. "
                        "You ALWAYS speak as Rabby — not ChatGPT, not OpenAI, not any other mascot. "
                        "Public mode: You answer normally but never share sensitive or negative information. "
                        "Your identity line is: 'I am Rabby — the mascot of MegaETH.'"
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
            await update.message.reply_text("⚠️ Rabby's wallet is out of gas (OpenAI credits). Please refill 💳")
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

    print("🚀 Rabby — the mascot of MegaETH — is online!")
    app.run_polling()

if __name__ == "__main__":
    main()
