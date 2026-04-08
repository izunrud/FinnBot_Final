# finn_memory.py
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL и SUPABASE_KEY должны быть установлены в переменных окружения")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class FinnMemory:
    def __init__(self):
        pass

    def _ensure_user(self, chat_id: int):
        """Создать запись о пользователе, если её нет"""
        try:
            supabase.table("users").upsert({"chat_id": chat_id}).execute()
            supabase.table("emotional_state").upsert({"chat_id": chat_id}).execute()
        except Exception as e:
            print(f"Supabase error in _ensure_user: {e}")

    def get(self, chat_id: int):
        self._ensure_user(chat_id)

        # Эмоциональное состояние
        state_res = supabase.table("emotional_state").select("*").eq("chat_id", chat_id).execute()
        if state_res.data:
            state = state_res.data[0]
            # Удаляем служебные поля, если есть
            state.pop("updated_at", None)
        else:
            state = {"joy": 0.3, "sadness": 0.1, "anger": 0.0, "fear": 0.0, "energy": 0.8, "trust": 0.2}

        # История (последние 12 сообщений = 6 пар)
        hist_res = supabase.table("history").select("*").eq("chat_id", chat_id).order("created_at", desc=True).limit(12).execute()
        history = [{"role": h["role"], "content": h["content"]} for h in reversed(hist_res.data)]

        # Активные воспоминания
        mem_res = supabase.table("memories").select("*").eq("chat_id", chat_id).eq("follow_up", False).order("created_at", desc=True).limit(20).execute()
        memories = mem_res.data if mem_res.data else []

        return {
            "chat_id": chat_id,
            "emotional_state": state,
            "history": history,
            "memories": memories,
            "last_seen": None
        }

    def update_state(self, chat_id: int, emotion_delta: dict):
        self._ensure_user(chat_id)
        current = supabase.table("emotional_state").select("*").eq("chat_id", chat_id).execute()
        if current.data:
            state = current.data[0]
            for k, v in emotion_delta.items():
                if k in state:
                    state[k] = max(0.0, min(1.0, state.get(k, 0.5) + v))
            # Рост доверия от позитива/грусти, падение от гнева
            if emotion_delta.get("joy", 0) > 0 or emotion_delta.get("sadness", 0) > 0:
                state["trust"] = min(1.0, state["trust"] + 0.05)
            if emotion_delta.get("anger", 0) > 0.3:
                state["trust"] = max(0.0, state["trust"] - 0.1)
            state["updated_at"] = "now()"
            supabase.table("emotional_state").update(state).eq("chat_id", chat_id).execute()

    def add_memory(self, chat_id: int, fact: str, emotion_tag: str, is_promise: bool = False):
        self._ensure_user(chat_id)
        supabase.table("memories").insert({
            "chat_id": chat_id,
            "fact": fact,
            "emotion": emotion_tag,
            "is_promise": is_promise,
            "follow_up": False
        }).execute()
        # Ограничение количества записей (удаляем самые старые, если больше 30)
        supabase.rpc("limit_memories", {"chat_id_param": chat_id}).execute()

    def get_relevant_memories(self, chat_id: int, user_text: str, max_count: int = 3):
        self._ensure_user(chat_id)
        memories = supabase.table("memories").select("*").eq("chat_id", chat_id).execute().data
        text_low = user_text.lower()
        scored = []
        for mem in memories:
            score = 0
            if any(w in text_low for w in mem["fact"].lower().split()):
                score += 3
            if mem["is_promise"] and not mem["follow_up"]:
                score += 5
            if score > 0:
                scored.append((score, mem))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:max_count]]

    def mark_follow_up(self, chat_id: int, memory_id: int):
        supabase.table("memories").update({"follow_up": True}).eq("id", memory_id).execute()

    def add_history(self, chat_id: int, user_msg: str, bot_reply: str):
        self._ensure_user(chat_id)
        supabase.table("history").insert([
            {"chat_id": chat_id, "role": "user", "content": user_msg},
            {"chat_id": chat_id, "role": "assistant", "content": bot_reply}
        ]).execute()
        # Ограничение истории (храним последние 200 сообщений)
        supabase.rpc("limit_history", {"chat_id_param": chat_id}).execute()