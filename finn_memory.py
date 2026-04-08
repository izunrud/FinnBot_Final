# finn_memory.py
import json, os, time

MEMORY_FILE = "finn_memory.json"
MAX_HISTORY = 6
MAX_MEMORIES = 12

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
                "history": [],
                "emotional_state": {"joy": 0.3, "sadness": 0.1, "anger": 0.0, "fear": 0.0, "energy": 0.8, "trust": 0.2},
                "memories": [],
                "last_seen": time.time()
            }
        # Затухание эмоций при долгом молчании
        session = self.data["users"][cid]
        hours_idle = (time.time() - session["last_seen"]) / 3600
        if hours_idle > 1:
            decay = 0.95 ** int(hours_idle)
            for k in session["emotional_state"]:
                session["emotional_state"][k] *= decay
            session["emotional_state"]["energy"] = max(0.3, session["emotional_state"]["energy"])
            session["emotional_state"]["trust"] = max(0.1, session["emotional_state"]["trust"])
        session["last_seen"] = time.time()
        return session

    def update_state(self, chat_id, emotion_delta):
        s = self.get(chat_id)
        state = s["emotional_state"]
        for k, v in emotion_delta.items():
            state[k] = max(0.0, min(1.0, state.get(k, 0.5) + v))
        # Доверие растёт от позитива/вовлечённости, падает от агрессии
        if emotion_delta.get("joy", 0) > 0 or emotion_delta.get("sadness", 0) > 0:
            state["trust"] = min(1.0, state["trust"] + 0.05)
        if emotion_delta.get("anger", 0) > 0.3:
            state["trust"] = max(0.0, state["trust"] - 0.1)
        s["last_seen"] = time.time()
        self._save()

    def add_memory(self, chat_id, fact, emotion_tag, is_promise=False):
        s = self.get(chat_id)
        s["memories"].append({
            "fact": fact, "emotion": emotion_tag, "promise": is_promise,
            "timestamp": time.time(), "follow_up": False
        })
        # Очистка старых
        if len(s["memories"]) > MAX_MEMORIES:
            s["memories"] = s["memories"][-MAX_MEMORIES:]
        self._save()

    def get_relevant_memories(self, chat_id, user_text, max_count=3):
        s = self.get(chat_id)
        text_low = user_text.lower()
        relevant = []
        for mem in s["memories"]:
            score = 0
            if any(w in text_low for w in mem["fact"].lower().split()): score += 3
            if mem["promise"] and not mem["follow_up"]: score += 5
            if score > 0:
                relevant.append((score, mem))
        relevant.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in relevant[:max_count]]

    def mark_follow_up(self, chat_id, memory_fact):
        s = self.get(chat_id)
        for mem in s["memories"]:
            if mem["fact"] == memory_fact:
                mem["follow_up"] = True
        self._save()

    def add_history(self, chat_id, user_msg, bot_reply):
        s = self.get(chat_id)
        s["history"].append({"role": "user", "content": user_msg})
        s["history"].append({"role": "assistant", "content": bot_reply})
        if len(s["history"]) > MAX_HISTORY * 2:
            s["history"] = s["history"][-MAX_HISTORY*2:]
        self._save()