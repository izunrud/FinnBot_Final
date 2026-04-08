# bot.py
from flask import Flask, request
import telebot, time, os, random, logging
from finn_memory import FinnMemory
from finn_core import get_reply, load_lore

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TG_TOKEN= OPENROUTER_KEY=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")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, parse_mode=None)
mem = FinnMemory()
load_lore()

@bot.message_handler(commands=['start'])
def cmd_start(m): bot.reply_to(m, random.choice(["Математический! ⚔️", "Йо! Финн на связи.", "Алгебраический! Готов?"]))

@bot.message_handler(commands=['debug'])
def cmd_debug(m): bot.reply_to(m, "✅ Система стабильна. Эмоции: активны. Память: теги + обещания. Инициатива: встроена.")

@bot.message_handler(commands=['clear'])
def cmd_clear(m):
    mem.data["users"].pop(str(m.chat.id), None)
    mem._save()
    bot.reply_to(m, "🌪️ Память и чувства стёрты. Начинаем с чистого листа.")

@bot.message_handler(func=lambda m: True)
def handle(m):
    if m.from_user.is_bot: return
    if m.chat.type in ['group', 'supergroup']:
        if not (m.text and f"@{bot.get_me().username}" in m.text) and not (m.reply_to_message and m.reply_to_message.from_user.id == bot.get_me().id):
            return

    chat_id = m.chat.id
    session = mem.get(chat_id)
    session["chat_id"] = chat_id  # Для внутренней логики
    session["last_msg"] = m.text.strip()

    # Имитация набора
    bot.send_chat_action(chat_id, 'typing')
    time.sleep(min(len(m.text) * 0.02 + random.uniform(0.4, 1.2), 3.0))

    reply = get_reply(session["last_msg"], session)
    
    mem.add_history(chat_id, session["last_msg"], reply)
    bot.reply_to(m, reply)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.stream.read().decode())
        bot.process_new_updates([update])
        return "", 200
    return "", 403

@app.route("/ping")
def ping(): return "alive"

@app.route("/")
def index(): return "⚔️ Finn Bot: Living Simulation Active"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
