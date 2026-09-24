import json
import urllib.request
from datetime import datetime

MODEL = "gemini-3.1-flash-lite"
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
- If there is no clear event with a date and time, return {"events": []}."""


def read_env(name):
    with open(".env") as f:
        for line in f:
            if line.startswith(name + "="):
                return line.strip().split("=", 1)[1]


def ask_events(rules, text, key_name="GEMINI_API_KEY", url=URL):
    now = datetime.now()
    system = f"Today is {now:%Y-%m-%d} ({now:%A}).\n" + rules
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": read_env(key_name)})
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
    except (OSError, ValueError, KeyError, IndexError, TypeError) as err:
        print(f"AI xato: {err}")
        return []


def parse_events(text):
    return ask_events(RULES, text)


def parse_event(text):
    evs = parse_events(text)
    return evs[0] if evs else None
