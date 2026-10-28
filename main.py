import asyncio
import logging
import json
import random
import sqlite3
from datetime import date
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Bot tokeningiz
TOKEN = "9003471730:AAFD6G-SJmDT3xf6Q5BikJE5Ds_NV5X6rLQ"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# SQLite ma'lumotlar bazasiga ulanish
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Foydalanuvchilar jadvalini yaratish
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    score INTEGER DEFAULT 0,
    daily_count INTEGER DEFAULT 0,
    last_date TEXT
)
""")
conn.commit()

# /start buyrug'i
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, score, daily_count, last_date) VALUES (?, ?, ?, ?)", (user_id, 0, 0, ""))
    conn.commit()
    
    await message.answer(
        f"Salom, {user_name}! 👋\n"
        "<b>Smart English Bot</b>'ga xush kelibsiz! 🇬🇧🇺🇿\n\n"
        "📌 Har kuni sizga <b>50 tagacha</b> savol taqdim etiladi va har 24 soatda limit avtomatik yangilanib turadi.\n\n"
        "📖 Testni boshlash uchun /word\n"
        "📊 Ballaringizni ko'rish uchun /score buyrug'ini yuboring.",
        parse_mode="HTML"
    )

# /score buyrug'i - Statistika va qolgan limitni ko'rsatish
@dp.message(Command("score"))
async def cmd_score(message: types.Message):
    user_id = message.from_user.id
    
    cursor.execute("SELECT score, daily_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    user_score = result[0] if result else 0
    daily_count = result[1] if result else 0
    remaining = 50 - daily_count
    
    await message.answer(
        f"📊 <b>Sizning statistikangiz:</b>\n\n"
        f"Jami to'g'ri javoblar: <b>{user_score} ta</b> 🟢\n"
        f"Bugun yechilgan savollar: <b>{daily_count} / 50 ta</b>\n"
        f"Qolgan limit: <b>{remaining if remaining > 0 else 0} ta</b>",
        parse_mode="HTML"
    )

# Yangi so'z yuboruvchi yordamchi funksiya
async def send_word_to_user(chat_id: int, user_id: int):
    today_str = str(date.today())
    
    cursor.execute("SELECT daily_count, last_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("INSERT INTO users (user_id, score, daily_count, last_date) VALUES (?, ?, ?, ?)", (user_id, 0, 0, today_str))
        conn.commit()
        daily_count = 0
        last_date = today_str
    else:
        daily_count, last_date = row
        
    if last_date != today_str:
        daily_count = 0
        cursor.execute("UPDATE users SET daily_count = 0, last_date = ? WHERE user_id = ?", (today_str, user_id))
        conn.commit()
        
    if daily_count >= 50:
        await bot.send_message(
            chat_id,
            "⏳ <b>Bugungi limit tugadi!</b>\n\n"
            "Siz bugungi 50 ta savol limitini to'liq tugatdingiz. Yangi savollar 24 soatdan keyin ochiladi!",
            parse_mode="HTML"
        )
        return

    try:
        with open("words.json", "r", encoding="utf-8") as file:
            words_list = json.load(file)
    except Exception:
        await bot.send_message(chat_id, "⚠️ Xatolik: words.json fayli topilmadi.")
        return
    
    if len(words_list) < 3:
        await bot.send_message(chat_id, "⚠️ Xatolik: words.json faylida kamida 3 ta so'z bo'lishi kerak!")
        return

    correct_word = random.choice(words_list)
    eng = correct_word["english"]
    correct_uzb = correct_word["uzbek"]
    
    other_words = [w["uzbek"] for w in words_list if w["uzbek"] != correct_uzb]
    wrong_options = random.sample(other_words, min(2, len(other_words)))
    
    options = wrong_options + [correct_uzb]
    random.shuffle(options)
    
    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=opt, callback_data=f"word_ans:{opt}:{correct_uzb}")
    
    builder.adjust(1)
    
    cursor.execute("UPDATE users SET daily_count = daily_count + 1, last_date = ? WHERE user_id = ?", (today_str, user_id))
    conn.commit()
    
    await bot.send_message(
        chat_id,
        f"📖 <b>Inglizcha so'zning tarjimasini toping</b> ({daily_count + 1}/50):\n\n"
        f"🇬🇧 English: <b>{eng}</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

# /word buyrug'i
@dp.message(Command("word"))
async def cmd_word(message: types.Message):
    await send_word_to_user(message.chat.id, message.from_user.id)

# Javobni tekshirish va darhol keyingi savolni chiqarish
@dp.callback_query(lambda c: c.data.startswith("word_ans:"))
async def check_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    data_parts = callback.data.split(":")
    selected_ans = data_parts[1]
    correct_ans = data_parts[2]
    
    if selected_ans == correct_ans:
        cursor.execute("UPDATE users SET score = score + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        
        await callback.answer("To'g'ri! +1 ball 🟢", show_alert=True)
        await callback.message.edit_text(
            f"✅ <b>To'g'ri topdingiz!</b>\n\n"
            f"Tarjimasi: <b>{correct_ans}</b>", 
            parse_mode="HTML"
        )
    else:
        await callback.answer("Noto'g'ri! 🔴", show_alert=True)
        await callback.message.edit_text(
            f"❌ <b>Noto'g'ri!</b>\n\n"
            f"To'g'ri javob edi: <b>{correct_ans}</b>", 
            parse_mode="HTML"
        )
    
    # Tugma bosilishi bilan keyingi savolni avtomatik chiqarish
    await send_word_to_user(chat_id, user_id)

# Botni ishga tushirish
async def main():
    print("Bot avtomatik navbatdagi savol rejimi bilan ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())