import base64
import json
import urllib.error
import urllib.request
from datetime import datetime

MODEL = "gemini-flash-latest"
FMT = "%Y-%m-%d %H:%M"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

RULES = """The user writes in Uzbek (sometimes Russian or English). Extract ALL distinct events from the text and return ONLY JSON:
{"events": [{"title": string, "date": "YYYY-MM-DD", "time": "HH:MM" (24-hour), "travel_min": integer}]}
Rules:
- One text may contain several events (e.g. "soat 8 da A ga, keyin soat 10 da B ga, kechga 17:30 da C ga"). Return each as a separate item, in the order written.
- Keep the title in the original language of the user. Do NOT translate it.
- travel_min is travel time in minutes for THAT event ("yolga 15 minut", "bir soat vaqtim ketadi" = 60); use 0 if not mentioned.
- A date word like "ertaga" applies to all following events until another date is given.
- Uzbek hints: bugun = today, ertaga = tomorrow, indinga = the day after tomorrow, ertalab = morning, tushda = noon, kechqurun/kechga = evening (soat 8 kechqurun = 20:00). Without a period word, pick the most plausible time (school, work meetings in the morning are usually AM; an explicit 17:30 is exact).
- If there is no clear event with a date and time, return {"events": []}.
- If only a time is given with no explicit date word (no "bugun"/"ertaga"/etc.), and that time has already passed today (compare to the given current time), use TOMORROW's date instead of today's — never schedule something in the past."""

CANCEL_RULES = """The user writes in Uzbek (sometimes Russian or English). You are given two things:
1) A list of the user's currently planned UPCOMING events, each with an id, date+time and title.
2) A new message from the user (text or voice).

Decide what the message means and return ONLY JSON:
{"add": [{"title": string, "date": "YYYY-MM-DD", "time": "HH:MM" (24-hour), "travel_min": integer}], "cancel_ids": [integer, ...]}

Rules:
- "cancel_ids": ids (from the given list) of existing events that this message clearly cancels — phrases like "bormayman", "otmen qildim/bo'ldi", "bekor qildim", "bormaydigan bo'ldim", "kelolmayman", "qolmayapman" etc. Match the right event by topic/place/time similarity to the message. If nothing in the message is about cancelling, or no existing event clearly matches, return an empty list — never guess.
- "add": brand-new events described in the message that are not already in the existing list. A message that is ONLY a cancellation must produce an empty "add" list — do not re-add the thing being cancelled.
- One message can both cancel one event and add a different new one (e.g. "bugungi uchrashuv bekor, ertaga soat 10 da bo'ladi" — cancel the old one, add the new one).
- travel_min is travel time in minutes for a new event if mentioned, otherwise 0.
- Uzbek hints: bugun = today, ertaga = tomorrow, indinga = the day after tomorrow, ertalab = morning, tushda = noon, kechqurun/kechga = evening (soat 8 kechqurun = 20:00).
- Keep titles in the original language of the user. Do NOT translate.
- If only a time is given for a new "add" event with no explicit date word, and that time has already passed today (compare to the given current time), use TOMORROW's date instead of today's — never schedule something in the past.
- If the message expresses NOT doing / cancelling something ("bormayman", "bormaydigan bo'ldim", "bekor", "otmen", "kelmayman", "qilmayman" etc.) but no existing event in the given list clearly matches it, return {"add": [], "cancel_ids": []}. NEVER create a new "add" event whose title is the cancellation/negation phrase itself — a refusal is not an event."""


def read_env(name):
    with open(".env") as f:
        for line in f:
            if line.startswith(name + "="):
                return line.strip().split("=", 1)[1]


def ask_events_from_parts(rules, parts, api_key, url=URL):
    """parts — Gemini 'contents[0].parts' formatidagi ro'yxat.
    Matn uchun {"text": "..."}, ovoz uchun
    {"inline_data": {"mime_type": "audio/ogg", "data": base64_str}}.
    api_key — shu foydalanuvchining o'z Gemini API kaliti."""
    now = datetime.now()
    system = f"Today is {now:%Y-%m-%d} ({now:%A}), current time is {now:%H:%M}.\n" + rules
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        raw = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
        if isinstance(raw, dict):
            raw = raw.get("events", [])
        result = []
        for ev in raw:
            when = f'{ev["date"]} {ev["time"]}'
            datetime.strptime(when, FMT)
            title = str(ev["title"]).strip()
            travel = int(ev.get("travel_min", 0))
            if not title or not 0 <= travel <= 300:
                continue
            result.append({"when": when, "title": title, "travel_min": travel})
        return result
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")
        print(f"AI xato: HTTP {err.code}: {body}")
        return []
    except (OSError, ValueError, KeyError, IndexError, TypeError) as err:
        print(f"AI xato: {err}")
        return []


def ask_events(rules, text, api_key, url=URL):
    return ask_events_from_parts(rules, [{"text": text}], api_key, url)


def ask_events_audio(rules, audio_bytes, api_key, mime_type="audio/ogg", url=URL):
    b64 = base64.b64encode(audio_bytes).decode()
    part = {"inline_data": {"mime_type": mime_type, "data": b64}}
    return ask_events_from_parts(rules, [part], api_key, url)


def ask_add_cancel(context_parts, message_parts, api_key, url=URL):
    """context_parts — mavjud tadbirlar haqidagi matn qismi(lar)i.
    message_parts — foydalanuvchi yangi xabari (matn va/yoki ovoz qismlari).
    api_key — shu foydalanuvchining o'z Gemini API kaliti.
    Qaytaradi: {"add": [{"when","title","travel_min"}, ...], "cancel_ids": [int, ...]}"""
    parts = context_parts + message_parts
    now = datetime.now()
    system = f"Today is {now:%Y-%m-%d} ({now:%A}), current time is {now:%H:%M}.\n" + CANCEL_RULES
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": parts}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        raw = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
        add_raw = raw.get("add", []) if isinstance(raw, dict) else []
        cancel_raw = raw.get("cancel_ids", []) if isinstance(raw, dict) else []
        add = []
        for ev in add_raw:
            when = f'{ev["date"]} {ev["time"]}'
            datetime.strptime(when, FMT)
            title = str(ev["title"]).strip()
            travel = int(ev.get("travel_min", 0))
            if not title or not 0 <= travel <= 300:
                continue
            add.append({"when": when, "title": title, "travel_min": travel})
        cancel_ids = []
        for cid in cancel_raw:
            try:
                cancel_ids.append(int(cid))
            except (TypeError, ValueError):
                continue
        return {"add": add, "cancel_ids": cancel_ids}
    except urllib.error.HTTPError as err:
        body = err.read().decode(errors="replace")
        print(f"AI xato: HTTP {err.code}: {body}")
        return {"add": [], "cancel_ids": []}
    except (OSError, ValueError, KeyError, IndexError, TypeError) as err:
        print(f"AI xato: {err}")
        return {"add": [], "cancel_ids": []}


def parse_events(text, api_key):
    return ask_events(RULES, text, api_key)


def parse_events_audio(audio_bytes, api_key, mime_type="audio/ogg"):
    return ask_events_audio(RULES, audio_bytes, api_key, mime_type)


def parse_event(text, api_key):
    evs = parse_events(text, api_key)
    return evs[0] if evs else None