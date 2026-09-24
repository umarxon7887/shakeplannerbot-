from ai import ask_events, read_env

# Alohida kalit: .env ichida USERBOT_GEMINI_KEY=...
# Ixtiyoriy: USERBOT_MODEL=... (bo'lmasa, quyidagi model ishlatiladi)
MODEL = read_env("USERBOT_MODEL") or "gemini-3.1-flash-lite"
FMT = "%Y-%m-%d %H:%M"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

RULES = """You get a chat between two people. "Men" is the bot owner. Chat language is Uzbek (sometimes Russian or English).
Read the WHOLE conversation and extract ALL events that Men agreed to attend or do. Return ONLY JSON:
{"events": [{"title": string, "date": "YYYY-MM-DD", "time": "HH:MM" (24-hour), "travel_min": integer}]}
Rules:
- Date, time and place may be in different messages. Combine them.
- A request or question from the other person is NOT an event by itself. Someone asking Men to come, work, or meet is only a proposal.
- If Men refused or said he cannot ("yoq", "vaqtim yoq", "borolmayman", "qiberolmayman"), return {"events": []} for that proposal. The latest replies decide.
- Only return an event if Men clearly agreed (e.g. "ha", "bopti", "boraman", "hop") or the plan is confirmed, or Men himself states his own plan ("boraman", "borishim kerak"). If Men declined, only a question was asked, or nothing is agreed, return {"events": []}.
- Title: short event type plus place if known, in the chat's language (e.g. "3-smena, Chilonzor filiali"). Do NOT translate.
- travel_min: travel time in minutes if mentioned, otherwise 0.
- Uzbek hints: bugun = today, ertaga = tomorrow, indinga = the day after tomorrow, ertalab = morning, tushda = noon, kechqurun/kechga = evening. If an explicit clock time is written (e.g. 17:30), use it exactly.
- Use the latest agreed details if the plan changed during the chat."""


def parse_conversation(convo):
    return ask_events(RULES, convo, "USERBOT_GEMINI_KEY", URL)
