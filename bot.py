from flask import Flask, request
import telebot, time, os, random, logging
from finn_memory import FinnMemory
from finn_core import build_prompt, get_reply, load_lore

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TG_TOKEN")
PORT = int(os.environ.get("PORT", 10000))

app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, parse_mode=None)
mem = FinnMemory()
lore_db = load_lore()

@bot.message_handler(commands=['start'])
def cmd_start(m): bot.reply_to(m, random.choice(["Математический! ⚔️", "Йо! Финн на связи.", "Алгебраический! Готов к приключениям?"]))

@bot.message_handler(commands=['status'])
def cmd_status(m):
    s = mem.get(m.chat.id)
    bot.reply_to(m, f"💡 Настроение: {s['mood']}\n📜 Суть: {s['summary']}\n📋 Факты: {', '.join(s['facts'].keys()) or 'нет'}")

@bot.message_handler(commands=['sync'])
def cmd_sync(m): mem._save(); bot.reply_to(m, "💾 Память сохранена.")

@bot.message_handler(commands=['clear'])
def cmd_clear(m): mem.data["users"].pop(str(m.chat.id), None); mem._save(); bot.reply_to(m, "🌪️ Память стёрта.")

@bot.message_handler(commands=['debug'])
def cmd_debug(m): bot.reply_to(m, "✅ Бот работает. Память активна. Лор загружен. Модель: Gemma-2/Qwen-2.5 (авто)")

@bot.message_handler(func=lambda m: True)
def handle(m):
    if m.from_user.is_bot: return
    if m.chat.type in ['group', 'supergroup']:
        mentioned = m.text and f"@{bot.get_me().username}" in m.text
        is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot.get_me().id
        if not (mentioned or is_reply): return

    chat_id = m.chat.id
    text = m.text.strip()
    s = mem.get(chat_id)
    s["last_msg"] = text
    mood = mem.detect_mood(text)
    
    t = text.lower()
    if any(w in t for w in ["зовут","меня","зови"]):
        words = text.split()
        for i, w in enumerate(words):
            if w.lower() in ["зовут","меня","зови"] and i+1 < len(words):
                mem.add_fact(chat_id, "имя", words[i+1].strip(".,!?\"'")); break

    bot.send_chat_action(chat_id, 'typing')
    time.sleep(min(len(text) * 0.025 + random.uniform(0.3, 0.9), 3.5))
    
    prompt = build_prompt(s, lore_db)
    reply = get_reply(prompt, text)
    mem.update(chat_id, text, reply, mood)
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
def index(): return "⚔️ Finn Bot vFinal — Mathematical!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)