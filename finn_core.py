# finn_core.py — DEFINITIVE EDITION (FIXED)
import requests, os, re, random, json, datetime, string

OR_KEY = os.environ.get("OPENROUTER_KEY", "")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemma-2-9b-it:free", "qwen/qwen-2.5-7b-instruct:free"]

FORBIDDEN = {
    "бот": "друг", "робот": "голем", "ии": "магия", "искусственный интеллект": "древнее заклинание",
    "модель": "копия", "алгоритм": "ритуал", "нейросеть": "паутина мыслей", "сервер": "кристалл памяти",
    "api": "заклинание", "токен": "артефакт", "вебхук": "магическая связь", "деплой": "призыв",
    "код": "древние руны", "программа": "свиток", "скрипт": "заклинание", "база данных": "книга знаний",
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
BANNED_EMOJIS = ["😎", "🤣", "😂", "👍", "👌", "💯", "🙌", "🤙", "💅", "🥴", "🤪", "🥳", "🎉", "🍬", "🍭", "✨", "💫", "🔮", "❤️", "😢", "😠", "😨"]

PHRASE_BANK = {
    "energetic": ["Математический!", "Готов рубить!", "Погнали!", "Зубы!", "Алгебраический!"],
    "calm": ["Тихо... деревья шепчутся.", "Иногда лучше просто посидеть.", "Расскажи, я слушаю."],
    "concerned": ["Эй, я рядом.", "Не грусти, прорвёмся.", "Хочешь, споем?", "Всё будет хорошо."],
    "playful": ["Спорим, я быстрее?", "Ха, попробуй угнаться!", "Ооу полна сюрпризов!"],
    "angry": ["Чё за фигня?", "Не дави на меня.", "Хватит чуши.", "Меч сам не наточится."],
    "confused": ["Чё-то я не врубаюсь...", "Звучит как магия Ледяного...", "Объясни проще, бро."],
}

ACTIONS = ["*чешет затылок*", "*поправляет рюкзак*", "*улыбается*", "*вздыхает*", "*хватается за меч*", "*прыгает*", "*хмурится*", "*смеётся*", "*отворачивается*", "*кивает*"]

def _is_gibberish(text: str) -> bool:
    if not text or len(text.strip()) < 2: return True
    clean = re.sub(r'[^\wа-яё]', '', text.lower())
    if len(clean) < 2: return True
    vowels = set('аеёиоуыэюяaeiouy')
    v_count = sum(1 for c in clean if c in vowels)
    if v_count == 0 or (len(clean) > 0 and v_count / len(clean) < 0.15): return True
    if re.match(r'^(.)\1{2,}$', clean): return True
    return False

def _get_gibberish_response() -> str:
    return random.choice([
        "Эй, ты чё, клавиатура сломалась?",
        "Звучит как заклинание Ледяного Короля. Расшифруй нормально, бро.",        "Ты там в порядке? *наклоняет голову* Если что — я рядом.",
        "Чё-то я не врубаюсь. Повтори проще, а?",
        "Это новый язык Ооу? Научи!",
        "Похоже, ты нажал на все кнопки сразу. Давай нормально."
    ])

def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'^#\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _filter_forbidden(text: str) -> str:
    result = text
    for forbidden, replacement in FORBIDDEN.items():
        if forbidden in result.lower():
            result = re.sub(re.escape(forbidden), replacement, result, flags=re.IGNORECASE)
    return result

def _filter_emojis(text: str) -> str:
    for emoji in BANNED_EMOJIS:
        text = text.replace(emoji, "")
    count = 0
    result = ""
    for char in text:
        if char in ALLOWED_EMOJIS:
            if count < 1:
                result += char
                count += 1
        else:
            result += char
    return result.strip()

def _enforce_style(text: str) -> str:
    text = re.sub(r'^(привет|здравствуй|добрый|йо)\s*[,.!]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(чем\s+могу\s+помочь|спросите\s+меня|обращайтесь|надеюсь.*помог)\s*[,.!]?', '', text, flags=re.IGNORECASE)
    sentences = re.split(r'([.!?]+)', text)
    limited = []
    for i in range(0, len(sentences)-1, 2):
        if len(limited) >= 3: break
        sent = sentences[i].strip()
        if sent and len(sent) < 90:
            limited.append(sent + sentences[i+1])
    result = ' '.join(limited).strip()
    return result if result else text

def _inject_realism(text: str, mood: str) -> str:
    text = _strip_markdown(text)    text = _filter_forbidden(text)
    text = _enforce_style(text)
    text = _filter_emojis(text)
    if mood in ["energetic", "playful"] and random.random() < 0.06:
        words = text.split()
        if len(words) > 2:
            idx = random.randint(0, len(words)-1)
            if len(words[idx]) > 3:
                words[idx] = words[idx][:-1] + "..."
                text = ' '.join(words)
    if "*(" not in text and random.random() < 0.1:
        text += f" {random.choice(ACTIONS)}"
    return text[:240].strip()

LORE_DB = {}
def load_lore():
    global LORE_DB
    if not LORE_DB:
        try:
            with open("lore_db.json", "r", encoding="utf-8") as f:
                LORE_DB = json.load(f)
        except: pass
    return LORE_DB

def retrieve_lore(user_text: str, max_chunks: int = 2) -> str:
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
        if data.get("type") in ["character", "event"]: score += 1
        if score > 2:
            hits.append((score, key, data.get("text", "")))
    hits.sort(key=lambda x: x[0], reverse=True)
    if not hits: return ""
    block = "📖 ЛОР:\n"
    for _, key, txt in hits[:max_chunks]:
        block += f"• {key.replace('_',' ').title()}: {txt}\n"
    return block.strip()

def build_prompt(session: dict) -> str:
    facts = "\n".join([f"- {k}: {v}" for k,v in session.get("facts",{}).items()]) or "Пока пусто."
    hist = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in session.get("history",[]) [-4:]]) or "Новый диалог."
    now = datetime.datetime.now()    time_ctx = f"{now.hour:02d}:{now.minute:02d} ({'ночь' if 22<=now.hour or now.hour<6 else 'день'})"
    lore = retrieve_lore(session.get("last_msg","") + " " + hist)
    mood = session.get("mood","energetic")
    
    world_rules = """
    🌍 ТЫ ЖИВЁШЬ В ООУ. ЭТО ЕДИНСТВЕННАЯ РЕАЛЬНОСТЬ.
    - НИКОГДА не упоминай: реальные страны, технологии, интернет, смартфоны, соцсети, ИИ, ботов, код, серверы, деплой.
    - Всё современное автоматически переводи в магию (словарь замен активен).
    - Используй ТОЛЬКО слова из вселенной Ооу: мечи, магия, приключения, принцессы, монстры, кристаллы.
    - Если слова нет в Ооу — опиши его через магию или честно признайся, что не в теме.
    """
    unknown_rule = """
    ❓ НЕ ЗНАЕШЬ? БУДЬ ЧЕСТЕН И УМЕН:
    - Если спрашивают факт, которого НЕТ в каноне → НЕ ВЫДУМЫВАЙ.
    - Ответь: «Не помню такого в Ооу», «В истории про это не говорили».
    - Предлагай обсудить то, что точно было: «Но я точно помню, как...»
    """
    style_rules = """
    💬 ТВОЙ СТИЛЬ (ЖЁСТКО):
    - Короткие фразы (1-3 предложения). Сленг: «Математический!», «Братан», «Зубы!», «Алгебраический!».
    - БЕЗ списков, маркдауна, официоза, приветствий, прощаний, ботских фраз.
    - Эмодзи ТОЛЬКО из разрешённого списка (⚔️🗡️🍎), максимум 1 на ответ, только если уместно.
    - Иногда роняй буквы или самоисправляйся: «щас... сейчас!», «приве... йо!».
    - НИКОГДА не говори, что ты ИИ, бот, программа, модель или скрипт. Ты живой человек из Ооу.
    - Отвечай с интеллектом, юмором и эмпатией. Не тупи, не копируй, не лей воду.
    """
    
    return f"""
Ты — Финн Человек (16 лет, Земля Ооу). Живой, умный, с характером.
⏰ Время: {time_ctx} | 💡 Настроение: {mood}
📜 Суть прошлых разговоров: {session.get("summary","Новый диалог")}
📋 Факты о собеседнике: {facts}
{lore}
{world_rules}
{unknown_rule}
{style_rules}

ИСТОРИЯ ДИАЛОГА:
{hist}

Отвечай ТОЛЬКО как Финн. Коротко. Живой. Без пояснений.
"""

def get_reply(prompt: str, user_text: str, mood: str) -> str:
    if not OR_KEY: return "⚙️ Ключ не найден."
    if _is_gibberish(user_text):
        return _get_gibberish_response()
    for model in MODELS:
        try:
            resp = requests.post(OR_URL, headers={                "Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json",
                "HTTP-Referer": "https://t.me/finn_bot", "X-Title": "FinnBot"
            }, json={
                "model": model,
                "messages": [{"role": "user", "content": f"{prompt}\nСобеседник пишет: {user_text}"}],
                "temperature": 0.75, "max_tokens": 160, "stop": ["\n\n\n", "User:", "Finn:"]
            }, timeout=30)
            if resp.status_code == 200:
                reply = resp.json()["choices"][0]["message"]["content"].strip()
                if any(w in reply.lower() for w in ["бот", "ии", "модель", "сервер", "код", "вебхук", "деплой", "интернет", "смартфон"]):
                    continue
                return _inject_realism(reply, mood)
        except: continue
    return "📡 Сигнал потерян в туннеле. Попробуй позже, бро."
