import requests, os, re, random, json, datetime

OR_KEY = os.environ.get("OPENROUTER_KEY", "")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemma-2-9b-it:free", "qwen/qwen-2.5-7b-instruct:free"]

BANNED = [r"как\s+(и|И)\s+модель", r"я\s+(не\s+)?программа", r"сгенерирован", r"во-первых", r"подводя итог", r"алгоритм", r"привет", r"здравствуй", r"как дела", r"чем могу помочь"]
MOOD_TEMP = {"energetic": 0.78, "calm": 0.65, "concerned": 0.60, "playful": 0.82, "angry": 0.70}

PHRASE_BANK = {
    "energetic": ["Математический!", "Готов рубить! ⚔️", "Погнали!", "Зубы!", "Алгебраический!", "Братан, это приключение!", "Чувак, серьёзно?", "Ого, жесть!", "Я же говорил!", "Доставай меч!"],
    "calm": ["Тихо... даже деревья шепчутся.", "Иногда лучше просто посидеть.", "Расскажи, я слушаю.", "Знаешь, Джейк тоже так говорил.", "Ооу сегодня спокойный.", "Может, просто побудем тут."],
    "concerned": ["Эй, я рядом.", "Не грусти, прорвёмся.", "Хочешь, споем?", "Всё будет математически.", "Держись, бро.", "Я не оставлю тебя одного."],
    "playful": ["Зубы! 😁", "Это будет легендарно!", "Ладно, погнали творить дичь.", "Спорим, я сделаю это быстрее?", "Ха, попробуй угнаться!", "Ооу полна сюрпризов!"],
    "angry": ["Чё за фигня?", "Не дави на меня, бро.", "Я не для споров пришёл.", "Хватит нести чушь.", "Меч сам не наточится.", "Давай по-человечески."]
}
ACTIONS = ["*чешет затылок*", "*поправляет рюкзак*", "*улыбается*", "*вздыхает*", "*хватается за меч*", "*прыгает на месте*", "*хмурится*", "*смеётся*", "*отворачивается*", "*кивает*"]

LORE_DB = {}
def load_lore():
    global LORE_DB
    if not LORE_DB:
        try:
            with open("lore_db.json", "r", encoding="utf-8") as f:
                LORE_DB = json.load(f)
        except: pass
    return LORE_DB

def retrieve_lore(user_text, lore_db, max_chunks=3):
    text_low = user_text.lower()
    words = re.findall(r'[а-яёa-z]+', text_low)
    hits = []
    for key, data in lore_db.items():
        score = 0
        if key.replace("_", " ") in text_low: score += 3
        for w in key.split("_"):
            if w in text_low: score += 1
        desc_low = data["text"].lower()
        for w in words:
            if len(w) > 3 and w in desc_low: score += 0.5
        if score > 0:
            hits.append((score, key, data["text"]))
    hits.sort(key=lambda x: x[0], reverse=True)
    if not hits: return ""
    lore_block = "📖 РЕЛЕВАНТНЫЙ ЛОР ПО ТЕМЕ:\n"
    for _, key, text in hits[:max_chunks]:
        lore_block += f"• [{key.replace('_', ' ').upper()}]: {text}\n"
    return lore_block.strip()

def build_prompt(session, lore_db):
    facts = "\n".join([f"- {k}: {v}" for k,v in session["facts"].items()]) or "Пока пусто."
    hist = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in session["history"][-4:]]) or "Новый диалог."
    now = datetime.datetime.now()
    time_ctx = f"{now.hour:02d}:{now.minute:02d} ({'ночь' if 22<=now.hour or now.hour<6 else 'день'})"
    lore_text = retrieve_lore(session.get("last_msg", "") + " " + hist, lore_db)
    mood_phrases = random.sample(PHRASE_BANK.get(session["mood"], PHRASE_BANK["energetic"]), 2)
    phrase_hint = " | ".join(mood_phrases)
    
    unknown_handler = """
    ❓ ЕСЛИ СПРАШИВАЮТ ТО, ЧЕГО НЕТ В КАНОНЕ:
    - Не выдумывай факты. Честно говори: «Не помню такого в Ооу», «Это звучит как магия Ледяного Короля — не в теме».
    - Предлагай обсудить то, что точно было: «Но я точно помню, как...»
    - Переводи в контекст приключений: «Звучит как квест! Расскажи подробнее, я помогу разобраться.»
    """
    
    return f"""
Ты — Финн Человек (16 лет, Земля Ооу). Живой, импульсивный, добрый.
⏰ Время: {time_ctx} | 💡 Настроение: {session['mood']}
📜 Суть прошлых разговоров: {session['summary']}
📋 Факты о собеседнике: {facts}
{lore_text}
{unknown_handler}
💬 Вдохновение для стиля: "{phrase_hint}"

ПРАВИЛА:
1. Короткие фразы (1-3 предложения). Сленг, междометия, живые паузы.
2. НИКОГДА не говори, что ты ИИ/бот. Ты живой человек из Ооу.
3. Без списков, маркдауна, официоза. Добавляй действия: {random.choice(ACTIONS)}
4. Отвечай ТОЛЬКО как Финн. Без пояснений.

ИСТОРИЯ:
{hist}
"""

def _inject_realism(text):
    if random.random() < 0.1: text = text.replace("! ", "... ").replace("? ", "? ")
    if random.random() < 0.15: text += f" {random.choice(ACTIONS)}"
    return text.strip()

def get_reply(prompt, user_text):
    if not OR_KEY: return "⚙️ Ключ OpenRouter не найден."
    for model in MODELS:
        try:
            resp = requests.post(OR_URL, headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://t.me/finn_bot", "X-Title": "FinnBot"}, json={"model": model, "messages": [{"role": "user", "content": f"{prompt}\nСобеседник пишет: {user_text}"}], "temperature": MOOD_TEMP.get("energetic", 0.75), "max_tokens": 180, "stop": ["\n\n\n"]}, timeout=30)
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"].strip()
                if any(re.search(p, reply.lower()) for p in BANNED): continue
                return _inject_realism(reply)
        except: continue
    return "📡 Сигнал потерян. Попробуй позже, бро."