import asyncio
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from datetime import datetime

from telethon import TelegramClient, events

from ai import read_env
from userbot_ai import parse_conversation

API_ID = int(read_env("API_ID"))
API_HASH = read_env("API_HASH")
OWNER = int(read_env("OWNER_CHAT_ID"))
EVENTS_FILE = "events.json"
FMT = "%Y-%m-%d %H:%M"

WAIT = 40          # oxirgi xabardan keyin necha soniya kutish
MAX_AGE = 3600     # suhbatga faqat oxirgi 1 soat xabarlari kiradi
MAX_MSGS = 12      # suhbatda ko'pi bilan nechta xabar

HINT = re.compile(
    r"\d{1,2}[:.]\d{2}|\b(bugun|ertaga|indinga|soat|kuni|uchrashuv|smena|"
    r"учеба|завтра|сегодня|послезавтра|встреча|в \d{1,2})\b",
    re.IGNORECASE,
)

def read_token():
    with open(".env") as f:
        for line in f:
            if line.startswith("BOT_TOKEN="):
                return line.strip().split("=", 1)[1]


TOKEN = read_token()


def notify(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": OWNER, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data, timeout=30).read()
    except OSError as err:
        print("notify xato:", err)


def load_events():
    if not os.path.exists(EVENTS_FILE):
        return []
    with open(EVENTS_FILE) as f:
        return json.load(f)


def save_events(items):
    tmp = EVENTS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, EVENTS_FILE)


def add_event(ev, src):
    items = load_events()
    for e in items:
        # bir xil suhbatdan shu vaqtga tadbir allaqachon qo'shilgan bo'lsa, o'tkazib yuboramiz
        if e["when"] == ev["when"] and (e.get("src") == src or e["title"] == ev["title"]):
            return None
    new_id = max([e.get("id", 0) for e in items], default=0) + 1
    items.append({"id": new_id, "chat_id": OWNER, "src": src, **ev})
    save_events(items)
    return new_id


client = TelegramClient("userbot", API_ID, API_HASH)
BUF = defaultdict(lambda: deque(maxlen=MAX_MSGS))
TASKS = {}


async def process_later(chat, who):
    try:
        await asyncio.sleep(WAIT)
    except asyncio.CancelledError:
        return
    now = time.time()
    msgs = [m for m in BUF[chat] if now - m[0] < MAX_AGE]
    convo = "\n".join(f"{name}: {text}" for _, name, text in msgs)
    if not msgs or not HINT.search(convo):
        return
    # Men hali javob bermagan bo'lsa, tadbir qo'shilmaydi
    if not any(m[1] == "Men" for m in msgs):
        return
    evs = await asyncio.to_thread(parse_conversation, convo)
    now = datetime.now()
    lines = []
    for ev in evs:
        if datetime.strptime(ev["when"], FMT) <= now:
            continue
        new_id = add_event(ev, chat)
        if new_id is None:
            continue
        line = f"#{new_id} {ev['when']} — {ev['title']}"
        if ev.get("travel_min"):
            line += f" (yo'l {ev['travel_min']} daq)"
        lines.append(line)
    if not lines:
        return
    BUF[chat].clear()
    await asyncio.to_thread(
        notify,
        f"📥 {who} bilan yozishmadan topildi\n" + "\n".join(lines)
        + "\nNoto'g'ri bo'lsa: /del raqam",
    )


@client.on(events.NewMessage(func=lambda e: e.is_private))
async def on_message(event):
    text = event.raw_text or ""
    if not text or text.startswith("/"):
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False):
        return
    chat = event.chat_id
    who = getattr(sender, "first_name", None) or "chat"
    name = "Men" if event.out else who
    BUF[chat].append((time.time(), name, text))
    old = TASKS.get(chat)
    if old:
        old.cancel()
    TASKS[chat] = asyncio.create_task(process_later(chat, who))


client.start()
print("Userbot ishga tushdi. To'xtatish: Ctrl+C")
client.run_until_disconnected()