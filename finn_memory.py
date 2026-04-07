import json
import os
import time

MEMORY_FILE = "finn_memory.json"
MAX_HISTORY = 6

class FinnMemory:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"users": {}}

    def _save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get(self, chat_id: int):
        cid = str(chat_id)
        if cid not in self.data["users"]:
            self.data["users"][cid] = {
                "history": [], "summary": "Начало знакомства.", "facts": {},
                "mood": "energetic", "last_seen": time.time()
            }
        if time.time() - self.data["users"][cid]["last_seen"] > 7200:
            self.data["users"][cid]["history"] = []
        return self.data["users"][cid]

    def update(self, chat_id, user_msg, bot_reply, mood):
        cid = str(chat_id)
        s = self.get(chat_id)
        s["history"].append({"role": "user", "content": user_msg})
        s["history"].append({"role": "assistant", "content": bot_reply})
        if len(s["history"]) > MAX_HISTORY * 2:
            s["history"] = s["history"][-MAX_HISTORY*2:]
        s["mood"] = mood
        s["last_seen"] = time.time()
        if len(s["history"]) % 8 == 0:
            s["summary"] = self._compress(s["history"][-8:])
        self._save()

    def _compress(self, history):
        return f"Разговор шёл о: {history[0]['content'][:30]}... → {history[-1]['content'][:30]}..."

    def detect_mood(self, text):
        t = text.lower()
        if any(w in t for w in ["груст","плох","устал","тоск","плач"]): return "concerned"
        if any(w in t for w in ["бей","враг","зл","бесит","агресс"]): return "angry"
        if any(w in t for w in ["смеш","хаха","рофл","шутк","прикол"]): return "playful"
        if any(w in t for w in ["спокой","отдых","истор","расскаж"]): return "calm"
        return "energetic"

    def add_fact(self, chat_id, key, value):
        s = self.get(chat_id)
        s["facts"][key] = value
        self._save()