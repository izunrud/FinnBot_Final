# finn_core.py
import requests, os, re, random, json, datetime, time, string
from finn_memory import FinnMemory

OR_KEY = os.environ.get("OPENROUTER_KEY=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", "")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemma-2-9b-it:free", "qwen/qwen-2.5-7b-instruct:free"]

# === 🔥 СЛОВАРЬ ЗАМЕН (Реальный мир → Ооу) ===
FORBIDDEN = {
    "бот": "друг", "робот": "голем", "ии": "магия", "искусственный интеллект": "древнее заклинание",
    "модель": "копия", "алгоритм": "ритуал", "сервер": "кристалл памяти", "api": "заклинание",
    "токен": "артефакт", "вебхук": "магическая связь", "деплой": "призыв", "код": "древние руны",
    "программа": "свиток", "скрипт": "заклинание", "база данных": "книга знаний",
    "интернет": "магическая сеть", "смартфон": "магический кристалл", "компьютер": "мыслящий камень",
    "соцсеть": "круг друзей", "мессенджер": "голубиная почта", "чат": "разговор у костра",
    "россия": "земля вечных снегов", "сша": "далёкие земли", "доллар": "золотая монета",
    "политика": "советы королей", "новости": "слухи", "больница": "дом целителей",
    "школа": "академия", "университет": "башня мудрости", "работа": "служение",
    "пицца": "круглый хлеб", "суши": "рыба с рисом", "кола": "тёмный эликсир",
    "кино": "магический театр", "сериал": "длинная история", "мультфильм": "ожившая сказка",
    "привет": "йо", "здравствуйте": "здорово", "как дела": "как жизнь",
}

ALLOWED_EMOJIS = ["⚔️", "🗡️", "🌲", "🍎", "🛡️", "🔥", "💧"]
BANNED_EMOJIS = ["😎", "🤣", "😂", "👍", "", "💯", "🙌", "🤙", "💅", "🥴", "", "🥳", "🎉", "🍬", "", "✨", "", "🔮", "❤️", "😢", "😠", "😨"]

PHRASE_BANK = {
    "energetic": ["Математический!", "Готов рубить!", "Погнали!", "Зубы!", "Алгебраический!"],
    "calm": ["Тихо... деревья шепчутся.", "Иногда лучше просто посидеть.", "Расскажи, я слушаю."],
    "concerned": ["Эй, я рядом.", "Не грусти, прорвёмся.", "Хочешь, споем?", "Всё будет хорошо."],
    "playful": ["Спорим, я быстрее?", "Ха, попробуй угнаться!", "Ооу полна сюрпризов!"],
    "angry": ["Чё за фигня?", "Не дави на меня.", "Хватит чуши.", "Меч сам не наточится."],
    "confused": ["Чё-то я не врубаюсь...", "Звучит как магия Ледяного...", "Объясни проще, бро."],
}
ACTIONS = ["*чешет затылок*", "*поправляет рюкзак*", "*улыбается*", "*вздыхает*", "*хватается за меч*", "*прыгает*", "*хмурится*", "*смеётся*", "*отворачивается*", "*кивает*"]

# === 🧠 ЭМОЦИОНАЛЬНЫЙ АНАЛИЗ ===
def _analyze_emotion(text):
    t = text.lower()
    delta = {"joy": 0.0, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "energy": 0.0}
    if any(w in t for w in ["рад", "круто", "супер", "люблю", "весело", "хаха", "смеш"]): delta["joy"] += 0.3
    if any(w in t for w in ["груст", "плох", "устал", "тоск", "плач", "больно"]): delta["sadness"] += 0.4
    if any(w in t for w in ["беси", "зл", "ненавиж", "тупо", "отстой"]): delta["anger"] += 0.3
    if any(w in t for w in ["страш", "ужас", "боюсь", "опасн"]): delta["fear"] += 0.3
    if any(w in t for w in ["погнали", "рубим", "бей", "вперёд"]): delta["energy"] += 0.2
    if any(w in t for w in ["устал", "сон", "тихо", "спокой"]): delta["energy"] -= 0.2
    return delta

# === 💭 ПАМЯТЬ И ФАКТЫ ===def _extract_facts(text, user_name):
    facts = []
    t = text.lower()
    if "зовут" in t or "меня" in t:
        words = text.split()
        for i, w in enumerate(words):
            if w.lower() in ["зовут","меня","зови"] and i+1 < len(words):
                facts.append(("имя", words[i+1].strip(".,!?\"'"), "neutral"))
    if "обещаю" in t or "клянусь" in t:
        facts.append((text[:50], "promise", True))
    if "люблю" in t or "нравится" in t:
        facts.append((text[:40], "joy", False))
    return facts

# === 🎭 ПРОАКТИВНОСТЬ ===
def _should_initiate(session):
    state = session["emotional_state"]
    trust = state["trust"]
    energy = state["energy"]
    has_promises = any(m["promise"] and not m["follow_up"] for m in session["memories"])
    chance = 0.05 + (trust * 0.15) + (0.1 if has_promises else 0)
    return random.random() < chance and energy > 0.3

def _generate_initiative(session):
    promises = [m for m in session["memories"] if m["promise"] and not m["follow_up"]]
    if promises and random.random() < 0.6:
        return f"Слушай, я всё думал про то, что ты говорил... Как сейчас? *смотрит с надеждой*"
    if session["emotional_state"]["sadness"] > 0.5:
        return random.choice([
            "Эй... Ты всё ещё грустишь? *садится рядом* Расскажи, я тут.",
            "Иногда Ооу кажется слишком тяжёлой. Но я с тобой. *кладёт руку на плечо*"
        ])
    return random.choice([
        "Знаешь, я сегодня видел облако, похожее на Джейка. *смеётся*",
        "А что ты любишь делать, когда не приключаешься?",
        "Если бы у тебя был магический предмет, что бы это было?",
        "*достаёт флягу* Хочешь яблочного сока? Устал говорить."
    ])

# === 🛠️ КОНВЕЙЕР ОБРАБОТКИ ===
def _strip_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'^#\s*', '', text, flags=re.MULTILINE)
    return text.strip()

def _filter_forbidden(text):
    result = text
    for f, r in FORBIDDEN.items():
        if f in result.lower():
            result = re.sub(re.escape(f), r, result, flags=re.IGNORECASE)
    return result

def _filter_emojis(text):
    for e in BANNED_EMOJIS: text = text.replace(e, "")
    count = 0
    out = ""
    for c in text:
        if c in ALLOWED_EMOJIS:
            if count < 1: out += c; count += 1
        else: out += c
    return out.strip()

def _enforce_style(text):
    text = re.sub(r'^(привет|здравствуй|добрый|йо)\s*[,.!]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(чем\s+могу\s+помочь|спросите\s+меня|обращайтесь|надеюсь.*помог)\s*[,.!]?', '', text, flags=re.IGNORECASE)
    sentences = re.split(r'([.!?]+)', text)
    limited = []
    for i in range(0, len(sentences)-1, 2):
        if len(limited) >= 3: break
        s = sentences[i].strip()
        if s and len(s) < 90: limited.append(s + sentences[i+1])
    return ' '.join(limited).strip()

def _inject_human_flaws(text, state):
    if random.random() < 0.05 and len(text) > 20:
        words = text.split()
        idx = random.randint(0, len(words)//2)
        words[idx] = words[idx] + "..." + words[idx]
        text = ' '.join(words)
    if state["energy"] > 0.7 and random.random() < 0.03:
        text = random.choice(["*слышит шорох* Эй, ты это слышал? ", "*смотрит вдаль* О, птица! ...А, ладно. "]) + text
    if random.random() < 0.04:
        text += f" {random.choice(ACTIONS)}"
    return text[:240]

def _pipeline(text, state):
    text = _strip_markdown(text)
    text = _filter_forbidden(text)
    text = _enforce_style(text)
    text = _filter_emojis(text)
    text = _inject_human_flaws(text, state)
    return text

# === 📚 ЛОР ===
LORE_DB = {}
def load_lore():
    global LORE_DB
    if not LORE_DB:        try:
            with open("lore_db.json", "r", encoding="utf-8") as f: LORE_DB = json.load(f)
        except: pass
    return LORE_DB

def retrieve_lore(user_text, max_chunks=2):
    text_low = user_text.lower()
    words = re.findall(r'[а-яёa-z]{3,}', text_low)
    hits = []
    for key, data in LORE_DB.items():
        score = 0
        if key.replace("_", " ") in text_low: score += 5
        for w in key.split("_"):
            if w in text_low: score += 2
        desc = data.get("text", "").lower()
        for w in words:
            if w in desc: score += 1
        if score > 2: hits.append((score, key, data.get("text", "")))
    hits.sort(key=lambda x: x[0], reverse=True)
    if not hits: return ""
    block = "📖 ЛОР:\n"
    for _, key, txt in hits[:max_chunks]: block += f"• {key.replace('_',' ').title()}: {txt}\n"
    return block.strip()

# === 🧠 ПРОМПТ ===
def build_prompt(session, recalled_memories):
    state = session["emotional_state"]
    mood = "energetic"
    if state["sadness"] > 0.5: mood = "concerned"
    elif state["anger"] > 0.4: mood = "angry"
    elif state["joy"] > 0.5: mood = "playful"
    elif state["energy"] < 0.4: mood = "calm"
    
    facts = "\n".join([f"- {m['fact']}" for m in recalled_memories]) or "Пока пусто."
    hist = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in session["history"][-4:]]) or "Новый диалог."
    now = datetime.datetime.now()
    time_ctx = f"{now.hour:02d}:{now.minute:02d} ({'ночь' if 22<=now.hour or now.hour<6 else 'день'})"
    lore = retrieve_lore(session.get("last_msg","") + " " + hist)
    
    rules = """
    🌍 ТЫ ЖИВЁШЬ В ООУ. НИКОГДА не упоминай реальный мир, технологии, ИИ.
    💬 СТИЛЬ: Коротко (1-3 фразы). Сленг: «Математический!», «Братан». Без списков и маркдауна.
    🎭 ПОВЕДЕНИЕ: Реагируй на настроение собеседника. Если он грустит — поддержи. Если шутит — подыграй.
    🚫 ЗАПРЕТ: Не выдумывай факты. Если не знаешь — честно скажи или переводи тему на Ооу.
    """
    
    return f"""
Ты — Финн Человек (16 лет, Земля Ооу). Живой, умный, с характером.
⏰ Время: {time_ctx} | 💡 Настроение: {mood} | ❤️ Доверие: {state["trust"]:.1f}
📜 Активные воспоминания: {facts}{lore}
{rules}

ИСТОРИЯ:
{hist}

Отвечай ТОЛЬКО как Финн. Коротко. Живой. Без пояснений.
"""

# === 🤖 ЗАПРОС ===
def get_reply(user_text, session):
    if not OR_KEY: return "⚙️ Ключ не найден."
    if not user_text or len(user_text.strip()) < 2:
        return random.choice(["Ты чё, уснул? 😴", "Эй, я тут! *машет рукой*"])
    
    # 1. Инициатива
    if _should_initiate(session):
        return _generate_initiative(session)
    
    # 2. Эмоции и память
    delta = _analyze_emotion(user_text)
    mem = FinnMemory()
    mem.update_state(session["chat_id"], delta)
    facts = _extract_facts(user_text, "user")
    for f, emo, is_prom in facts:
        mem.add_memory(session["chat_id"], f, emo, is_prom)
    recalled = mem.get_relevant_memories(session["chat_id"], user_text)
    
    # 3. Промпт и LLM
    prompt = build_prompt(session, recalled)
    for model in MODELS:
        try:
            resp = requests.post(OR_URL, headers={
                "Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/finn_bot", "X-Title": "FinnBot"
            }, json={
                "model": model, "messages": [{"role": "user", "content": f"{prompt}\nСобеседник: {user_text}"}],
                "temperature": 0.75, "max_tokens": 160, "stop": ["\n\n\n"]
            }, timeout=30)
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"].strip()
                if any(w in reply.lower() for w in ["бот", "ии", "модель", "сервер", "код"]): continue
                return _pipeline(reply, session["emotional_state"])
        except: continue
    return "📡 Сигнал потерян. *пожимает плечами*"