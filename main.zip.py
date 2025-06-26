import telebot
from telebot import types
import os
import json
from datetime import datetime, timedelta
import threading
import time
from collections import defaultdict

# Змінні з секретів
TOKEN = os.environ.get("BOT_TOKEN")
MY_ID = int(os.environ.get("MY_ID"))
bot = telebot.TeleBot(TOKEN)

# Файли
total_file = "total.txt"
history_file = "history.json"
goal_file = "goal.txt"
reminder_file = "reminder_day.txt"

# Ініціалізація
if not os.path.exists(total_file):
    with open(total_file, "w") as f:
        f.write("0")

if not os.path.exists(history_file):
    with open(history_file, "w") as f:
        json.dump([], f)

if not os.path.exists(goal_file):
    with open(goal_file, "w") as f:
        f.write("10000")  # стандартна ціль

if not os.path.exists(reminder_file):
    with open(reminder_file, "w") as f:
        f.write("6")  # неділя

# Функції
def get_total():
    with open(total_file, "r") as f:
        return float(f.read())

def update_total(amount):
    with open(total_file, "w") as f:
        f.write(str(amount))

def save_history(action, amount):
    with open(history_file, "r") as f:
        data = json.load(f)
    data.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": action,
        "amount": amount
    })
    with open(history_file, "w") as f:
        json.dump(data, f, indent=2)

def undo_last_transaction():
    with open(history_file, "r") as f:
        data = json.load(f)
    if not data:
        return False
    last = data.pop()
    total = get_total()
    if last["type"] == "add":
        total -= last["amount"]
    elif last["type"] == "minus":
        total += last["amount"]
    update_total(total)
    with open(history_file, "w") as f:
        json.dump(data, f, indent=2)
    return True

def get_goal():
    with open(goal_file, "r") as f:
        return float(f.read())

def set_goal(amount):
    with open(goal_file, "w") as f:
        f.write(str(amount))

def get_reminder_day():
    with open(reminder_file, "r") as f:
        return int(f.read())

def set_reminder_day(day):
    with open(reminder_file, "w") as f:
        f.write(str(day))

# Обробники
@bot.message_handler(commands=["start", "help"])
def help_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Додати", "➖ Витрати")
    markup.add("💰 Баланс", "📈 Прогрес", "🧾 Історія")
    markup.add("📊 Статистика", "🔁 Скасувати", "🎯 Задати ціль")
    markup.add("📅 День нагадування", "🔄 Скинути")
    bot.send_message(message.chat.id, 
        "📘 Команди:\n"
        "/add – додати суму\n"
        "/minus – витрати\n"
        "/total – баланс\n"
        "/progress – прогрес до цілі\n"
        "/history – історія транзакцій\n"
        "/stats – статистика по місяцях\n"
        "/undo – скасувати останню транзакцію\n"
        "/reset – скинути накопичення\n"
        "/setgoal – встановити ціль\n"
        "/setreminder – змінити день нагадування\n"
        "/help – допомога\n",
        reply_markup=markup
    )

@bot.message_handler(commands=["add"])
def ask_add(message):
    msg = bot.reply_to(message, "Впиши суму, яку хочеш додати 💸")
    bot.register_next_step_handler(msg, process_add)

def process_add(message):
    try:
        amount = float(message.text.replace(",", "."))
        total = get_total() + amount
        update_total(total)
        save_history("add", amount)
        bot.reply_to(message, f"➕ Додано {amount:.2f} zł\n💰 Загалом: {total:.2f} zł")
    except:
        bot.reply_to(message, "⚠️ Напиши суму правильно (наприклад: 100)")

@bot.message_handler(commands=["minus"])
def ask_minus(message):
    msg = bot.reply_to(message, "Впиши суму витрат ❌")
    bot.register_next_step_handler(msg, process_minus)

def process_minus(message):
    try:
        amount = float(message.text.replace(",", "."))
        total = get_total() - amount
        update_total(total)
        save_history("minus", amount)
        bot.reply_to(message, f"➖ Витрачено {amount:.2f} zł\n💰 Залишилось: {total:.2f} zł")
    except:
        bot.reply_to(message, "⚠️ Напиши суму правильно (наприклад: 50)")

@bot.message_handler(commands=["total"])
def total_money(message):
    bot.reply_to(message, f"💰 Баланс: {get_total():.2f} zł")

@bot.message_handler(commands=["progress"])
def show_progress(message):
    total = get_total()
    goal = get_goal()
    percent = (total / goal) * 100
    bot.reply_to(message, f"📈 Прогрес:\n{total:.2f} zł із {goal:.2f} zł\n"
                          f"✅ Виконано на {percent:.1f}%")

@bot.message_handler(commands=["history"])
def show_history(message):
    with open(history_file, "r") as f:
        data = json.load(f)
    if not data:
        bot.reply_to(message, "📭 Історія порожня.")
        return
    msg = "🧾 Останні транзакції:\n"
    for item in data[-10:]:
        sign = "➕" if item["type"] == "add" else "➖"
        msg += f"{item['date']}: {sign} {item['amount']:.2f} zł\n"
    bot.reply_to(message, msg)

@bot.message_handler(commands=["stats"])
def show_stats(message):
    with open(history_file, "r") as f:
        data = json.load(f)
    stats = defaultdict(lambda: {"add": 0, "minus": 0})
    for item in data:
        month = item["date"][:7]
        stats[month][item["type"]] += item["amount"]
    msg = "📊 Статистика по місяцях:\n"
    for month in sorted(stats.keys()):
        msg += f"{month} ➕ {stats[month]['add']} zł / ➖ {stats[month]['minus']} zł\n"
    bot.reply_to(message, msg)

@bot.message_handler(commands=["reset"])
def reset(message):
    update_total(0)
    with open(history_file, "w") as f:
        json.dump([], f)
    bot.reply_to(message, "🔄 Накопичення скинуто до 0")

@bot.message_handler(commands=["undo"])
def undo(message):
    if undo_last_transaction():
        bot.reply_to(message, "🔁 Останню транзакцію скасовано.")
    else:
        bot.reply_to(message, "⚠️ Немає транзакцій для скасування.")

@bot.message_handler(commands=["setgoal"])
def ask_goal(message):
    msg = bot.reply_to(message, "🎯 Введи нову ціль у zł:")
    bot.register_next_step_handler(msg, set_new_goal)

def set_new_goal(message):
    try:
        amount = float(message.text.replace(",", "."))
        set_goal(amount)
        bot.reply_to(message, f"🎯 Ціль оновлено до {amount:.2f} zł")
    except:
        bot.reply_to(message, "⚠️ Напиши суму правильно")

@bot.message_handler(commands=["setreminder"])
def ask_day(message):
    msg = bot.reply_to(message, "📅 Введи день тижня (0 — понеділок, 6 — неділя):")
    bot.register_next_step_handler(msg, set_new_reminder)

def set_new_reminder(message):
    try:
        day = int(message.text)
        if 0 <= day <= 6:
            set_reminder_day(day)
            bot.reply_to(message, "📅 День нагадування змінено!")
        else:
            bot.reply_to(message, "⚠️ Введи число від 0 до 6")
    except:
        bot.reply_to(message, "⚠️ Напиши число правильно")

# Нагадування
def weekly_reminder():
    while True:
        now = datetime.now()
        target_day = get_reminder_day()
        days_ahead = (target_day - now.weekday()) % 7
        next_reminder = now + timedelta(days=days_ahead)
        next_time = datetime.combine(next_reminder.date(), datetime.min.time()) + timedelta(hours=10)
        wait_seconds = (next_time - now).total_seconds()
        time.sleep(max(wait_seconds, 0))
        bot.send_message(MY_ID, "💡 Нагадування: не забудь відкласти на мотоцикл 🏍️💸")
        time.sleep(86400)  # доба щоб уникнути спаму

# Фоновий потік
threading.Thread(target=weekly_reminder, daemon=True).start()

# Обробка кнопок
@bot.message_handler(func=lambda m: True)
def handle_buttons(message):
    text = message.text.lower()
    if "додати" in text:
        ask_add(message)
    elif "витрати" in text:
        ask_minus(message)
    elif "баланс" in text:
        total_money(message)
    elif "прогрес" in text:
        show_progress(message)
    elif "історія" in text:
        show_history(message)
    elif "статистика" in text:
        show_stats(message)
    elif "скасувати" in text:
        undo(message)
    elif "скинути" in text:
        reset(message)
    elif "ціль" in text:
        ask_goal(message)
    elif "нагадування" in text:
        ask_day(message)


# 🚀 Flask-сервер для UptimeRobot
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Бот працює 🏍️💰"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# ▶️ Запуск телеграм-бота
print("Бот працює 🔥")
bot.infinity_polling()