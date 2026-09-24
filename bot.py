import json
import time
import math
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from ai import parse_events, read_env


def read_token():
    with open(".env") as f:
        for line in f:
            if line.startswith("BOT_TOKEN="):
                return line.strip().split("=", 1)[1]


TOKEN = read_token()
OWNER = read_env("OWNER_CHAT_ID")
EVENTS_FILE = "events.json"
FMT = "%Y-%m-%d %H:%M"
PREP_MIN = 15
USAGE = "Format: /add 2026-09-25 10:00 School 21 | 40\n(| dan keyin yo'l vaqti, daqiqada, ixtiyoriy)"


def api(method, **params):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(params).encode()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, data, timeout=40) as resp:
                return json.load(resp)
        except (OSError, ValueError) as err:
            print(f"api xato ({method}): {err}")
            time.sleep(3)
    return {"ok": False, "result": []}


def save_events(events):
    with open(EVENTS_FILE, "w") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def load_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    with open(EVENTS_FILE) as f:
        events = json.load(f)
    next_id = max([e.get("id", 0) for e in events], default=0) + 1
    changed = False
    for e in events:
        if "id" not in e:
            e["id"] = next_id
            next_id += 1
            changed = True
    if changed:
        save_events(events)
    return events


def reply(chat_id, text):
    api("sendMessage", chat_id=chat_id, text=text)


def check_reminders():
    now = datetime.now()
    events = load_events()
    changed = False
    for e in events:
        if e.get("reminded"):
            continue
        when = datetime.strptime(e["when"], FMT)
        travel = e.get("travel_min", 0)
        minutes_left = (when - now).total_seconds() / 60
        if minutes_left <= travel + PREP_MIN:
            if minutes_left > 0:
                if travel > 0:
                    leave_at = when - timedelta(minutes=travel)
                    if leave_at > now:
                        go = f"{leave_at:%H:%M} da yo'lga chiqing"
                    else:
                        go = "Hoziroq yo'lga chiqing"
                    text = (f"⏰ Tayyorlaning! {go} (yo'l {travel} daq).\n"
                            f"Tadbir: {e['title']} ({when:%H:%M})")
                else:
                    text = (f"⏰ {math.ceil(minutes_left)} daqiqadan keyin: "
                            f"{e['title']} ({when:%H:%M})")
                reply(e["chat_id"], text)
            e["reminded"] = True
            changed = True
    if changed:
        save_events(events)


def handle(chat_id, text):
    if text.startswith("/add"):
        parts = text.split(maxsplit=3)
        if len(parts) < 4:
            reply(chat_id, USAGE)
            return
        day = parts[1]
        if day == "bugun":
            day = datetime.now().strftime("%Y-%m-%d")
        elif day == "ertaga":
            day = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        when = day + " " + parts[2]
        try:
            datetime.strptime(when, FMT)
        except ValueError:
            reply(chat_id, "Sana/vaqt noto'g'ri.\n" + USAGE)
            return
        title = parts[3]
        travel = 0
        if "|" in title:
            title, travel_text = title.split("|", 1)
            title = title.strip()
            try:
                travel = int(travel_text.strip())
            except ValueError:
                reply(chat_id, "Yo'l vaqti butun son bo'lsin.\n" + USAGE)
                return
        events = load_events()
        new_id = max([e["id"] for e in events], default=0) + 1
        events.append({"id": new_id, "chat_id": chat_id, "when": when,
                       "title": title, "travel_min": travel})
        save_events(events)
        reply(chat_id, f"Qo'shildi ✅ (#{new_id})")
    elif text.split()[0] in ("/list", "/del") and len(text.split()) == 1:
        show_list(chat_id)
    elif text.startswith("/list"):
        show_all = text.split()[-1] == "all"
        now = datetime.now()
        events = [e for e in load_events() if e["chat_id"] == chat_id]
        if not show_all:
            events = [e for e in events
                      if datetime.strptime(e["when"], FMT) >= now]
        events.sort(key=lambda e: e["when"])
        if not events:
            reply(chat_id, "Tadbir yo'q")
        else:
            lines = []
            for e in events:
                line = f"#{e['id']} {e['when']} — {e['title']}"
                if e.get("travel_min"):
                    line += f" (yo'l {e['travel_min']} daq)"
                lines.append(line)
            reply(chat_id, "\n".join(lines))
    elif text.startswith("/del"):
        parts = text.split()
        if len(parts) != 2 or not parts[1].isdigit():
            reply(chat_id, "Format: /del 3")
            return
        del_id = int(parts[1])
        events = load_events()
        kept = [e for e in events
                if not (e["id"] == del_id and e["chat_id"] == chat_id)]
        if len(kept) == len(events):
            reply(chat_id, "Bunday raqamli tadbir topilmadi")
        else:
            save_events(kept)
            reply(chat_id, "O'chirildi 🗑")
    elif text.startswith("/today") or text.startswith("/tomorrow"):
        day = datetime.now().date()
        if text.startswith("/tomorrow"):
            day += timedelta(days=1)
        items = []
        for e in load_events():
            if e["chat_id"] != chat_id:
                continue
            when = datetime.strptime(e["when"], FMT)
            travel = e.get("travel_min", 0)
            if travel:
                leave_at = when - timedelta(minutes=travel)
                items.append((leave_at - timedelta(minutes=PREP_MIN), "tayyorlanish"))
                items.append((leave_at, f"yo'lga chiqish ({travel} daq)"))
            items.append((when, e["title"]))
        now = datetime.now()
        items = [(t, n) for t, n in items if t.date() == day and t >= now]
        items.sort()
        if not items:
            reply(chat_id, f"{day} uchun qolgan tadbir yo'q")
        else:
            lines = [f"📅 {day}"]
            lines += [f"{t:%H:%M} {name}" for t, name in items]
            reply(chat_id, "\n".join(lines))
    elif not text.startswith("/"):
        evs = parse_events(text)
        if not evs:
            reply(chat_id, "Tadbirni tushunolmadim (yoki AI hozir javob bermadi). Aniqroq yozing yoki /add dan foydalaning.")
            return
        events = load_events()
        new_id = max([e["id"] for e in events], default=0)
        lines = ["Qo'shildi ✅"]
        for ev in evs:
            new_id += 1
            events.append({"id": new_id, "chat_id": chat_id, **ev})
            line = f"#{new_id} {ev['when']} — {ev['title']}"
            if ev["travel_min"]:
                line += f" (yo'l {ev['travel_min']} daq)"
            lines.append(line)
        save_events(events)
        lines.append("Noto'g'ri bo'lsa: /del raqam")
        reply(chat_id, "\n".join(lines))
    else:
        reply(chat_id, "👋 Men kunlik rejalashtiruvchi botman.\n\nOddiy yozing, AI tushunadi:\n«ertaga 10 da School 21, yo'lga 40 daqiqa»\n\n/today — bugungi reja\n/tomorrow — ertangi reja\n/list — kelgusi tadbirlar\n/add — qo'lda qo'shish\n/del 3 — o'chirish")


STATE_FILE = "state.json"
USERS_FILE = "users.json"
BRIEF_TIME = (7, 0)
BRIEF_UNTIL_HOUR = 11


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def remember_user(chat_id):
    users = load_json(USERS_FILE, [])
    if chat_id not in users:
        users.append(chat_id)
        save_json(USERS_FILE, users)


def check_brief():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if not (BRIEF_TIME <= (now.hour, now.minute) and now.hour < BRIEF_UNTIL_HOUR):
        return
    state = load_json(STATE_FILE, {})
    if state.get("last_brief") == today:
        return
    for chat_id in load_json(USERS_FILE, []):
        reply(chat_id, "☀️ Xayrli tong! Bugungi reja:")
        handle(chat_id, "/today")
    state["last_brief"] = today
    save_json(STATE_FILE, state)


def cleanup_past():
    now = datetime.now()
    events = load_events()
    kept = [e for e in events if datetime.strptime(e["when"], FMT) > now]
    if len(kept) != len(events):
        save_events(kept)


COMMANDS = [
    ("today", "📅 Bugungi reja"),
    ("tomorrow", "🌅 Ertangi reja"),
    ("list", "📋 Kelgusi tadbirlar"),
    ("add", "➕ Tadbir qo'shish"),
    ("del", "🗑 Tadbirni o'chirish"),
]
api("setMyCommands", commands=json.dumps(
    [{"command": c, "description": d} for c, d in COMMANDS],
    ensure_ascii=False))

MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun",
          "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]


def day_title(d):
    today = datetime.now().date()
    name = f"{d.day}-{MONTHS[d.month - 1]}"
    if d == today:
        return f"Bugun ({name})"
    if d == today + timedelta(days=1):
        return f"Ertaga ({name})"
    return name


def build_list(chat_id):
    now = datetime.now()
    events = [e for e in load_events()
              if e["chat_id"] == chat_id
              and datetime.strptime(e["when"], FMT) >= now]
    events.sort(key=lambda e: e["when"])
    if not events:
        return "📭 Kelgusi tadbir yo'q", None
    lines = ["📋 Kelgusi tadbirlar"]
    buttons = []
    last_day = None
    for e in events:
        when = datetime.strptime(e["when"], FMT)
        if when.date() != last_day:
            last_day = when.date()
            lines.append("")
            lines.append("📅 " + day_title(last_day))
        line = f"🕙 {when:%H:%M} — {e['title']}"
        if e.get("travel_min"):
            line += f" 🚗 {e['travel_min']} daq"
        lines.append(line)
        label = f"🗑 {when:%d.%m %H:%M} {e['title']}"[:40]
        buttons.append([{"text": label, "callback_data": f"del:{e['id']}"}])
    lines.append("")
    lines.append("O'chirish uchun tadbir tugmasini bosing 👇")
    return "\n".join(lines), {"inline_keyboard": buttons}


def show_list(chat_id):
    text, markup = build_list(chat_id)
    params = {"chat_id": chat_id, "text": text}
    if markup:
        params["reply_markup"] = json.dumps(markup, ensure_ascii=False)
    api("sendMessage", **params)


def handle_callback(cb):
    chat_id = cb["message"]["chat"]["id"]
    if str(chat_id) != OWNER:
        return
    data = cb.get("data", "")
    if not (data.startswith("del:") and data[4:].isdigit()):
        api("answerCallbackQuery", callback_query_id=cb["id"])
        return
    del_id = int(data[4:])
    events = load_events()
    kept = [e for e in events
            if not (e["id"] == del_id and e["chat_id"] == chat_id)]
    if len(kept) != len(events):
        save_events(kept)
        note = "O'chirildi 🗑"
    else:
        note = "Bu tadbir allaqachon yo'q"
    api("answerCallbackQuery", callback_query_id=cb["id"], text=note)
    text, markup = build_list(chat_id)
    api("editMessageText", chat_id=chat_id,
        message_id=cb["message"]["message_id"], text=text,
        reply_markup=json.dumps(markup or {"inline_keyboard": []},
                                ensure_ascii=False))


offset = None
print("Bot ishga tushdi. To'xtatish: Ctrl+C")
while True:
    params = {"timeout": 10}
    if offset:
        params["offset"] = offset
    updates = api("getUpdates", **params)
    for u in updates["result"]:
        offset = u["update_id"] + 1
        cb = u.get("callback_query")
        if cb:
            handle_callback(cb)
            continue
        msg = u.get("message")
        if msg and "text" in msg:
            if str(msg["chat"]["id"]) != OWNER:
                continue
            remember_user(msg["chat"]["id"])
            handle(msg["chat"]["id"], msg["text"])
    check_reminders()
    check_brief()
    cleanup_past()
