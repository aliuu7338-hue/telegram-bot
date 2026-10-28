import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, executor

# Bot tokeningizni shu yerga yozasiz
TOKEN = "9003471730:AAEu6llNi10iRe-14LKOPAykg3ASqo7rrcg"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Render port talabini qondirish uchun kichik Flask server
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Botning /start buyrug'i uchun namuna
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Assalomu alaykum! Bot Render'da 24/7 rejimida muvaffaqiyatli ishlayapti.")

if __name__ == '__main__':
    # Veb-serverni alohida oqimda ishga tushiramiz
    keep_alive()
    
    # Botni ishga tushiramiz
    executor.start_polling(dp, skip_updates=True)
