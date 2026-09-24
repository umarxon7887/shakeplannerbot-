# ShakePlanner

Telegram orqali ishlaydigan kunlik rejalashtiruvchi bot. Tadbirlarni oddiy tilda (o'zbek, rus, ingliz) yozasiz, AI ularni tushunib ro'yxatga qo'shadi va vaqti kelganda eslatadi. Ixtiyoriy userbot shaxsiy yozishmalaringizdan kelishilgan tadbirlarni o'zi topib qo'shadi.

## Imkoniyatlar

- Oddiy matndan tadbir qo'shish: «ertaga 10 da School 21, yo'lga 40 daqiqa»
- Bitta xabardan bir nechta tadbirni ajratib olish
- Yo'l vaqtini hisobga olgan eslatma (tayyorlanish va yo'lga chiqish vaqti)
- Har kuni ertalab (07:00 dan) bugungi reja
- Tugmalar orqali tadbirni o'chirish
- Userbot: shaxsiy chatlardagi suhbatni butunlay o'qib, siz rozi bo'lgan tadbirlarni qo'shadi (rad etilganlarini qo'shmaydi)

## Fayllar

| Fayl | Vazifasi |
|------|----------|
| `bot.py` | Asosiy bot: buyruqlar, eslatmalar, kunlik reja |
| `ai.py` | Gemini orqali matndan tadbirlarni ajratish |
| `userbot.py` | Telegram akkauntingizga ulanib, yozishmalarni kuzatadi |
| `userbot_ai.py` | Suhbatdan tadbir ajratish (alohida API kalit bilan) |

## O'rnatish

Talab: Python 3.10+ (Termuxda ham ishlaydi).

```
git clone <repo-manzili>
cd shakeplanner
pip install -r requirements.txt
```

`.env` faylini yarating:

```
BOT_TOKEN=          # @BotFather dan olingan token
OWNER_CHAT_ID=      # sizning Telegram ID raqamingiz
GEMINI_API_KEY=     # https://aistudio.google.com/apikey
API_ID=             # https://my.telegram.org (faqat userbot uchun)
API_HASH=           # https://my.telegram.org (faqat userbot uchun)
USERBOT_GEMINI_KEY= # userbot uchun alohida Gemini kalit
USERBOT_MODEL=      # ixtiyoriy, bo'sh qolsa ai.py dagi model
```

## Ishga tushirish

```
python bot.py
```

Userbot (ixtiyoriy), alohida sessiyada:

```
python userbot.py
```

Birinchi ishga tushirishda telefon raqami va Telegramdan kelgan kod so'raladi. Keyingi safar sessiya fayli ishlatiladi.

Termuxda telefon uxlaganda dasturlar to'xtamasligi uchun: `termux-wake-lock`.

## Bot buyruqlari

| Buyruq | Ma'nosi |
|--------|---------|
| `/today` | Bugungi reja |
| `/tomorrow` | Ertangi reja |
| `/list` | Kelgusi tadbirlar (o'chirish tugmalari bilan) |
| `/add 2026-09-25 10:00 School 21 \| 40` | Qo'lda qo'shish (`\|` dan keyin yo'l vaqti, daqiqada) |
| `/del 3` | 3-raqamli tadbirni o'chirish |

Buyruqsiz oddiy matn AI orqali tahlil qilinadi.

## Userbot qanday ishlaydi

1. Faqat shaxsiy chatlar kuzatiladi (guruh va kanallar emas).
2. Har bir chat uchun oxirgi xabarlar saqlanadi, oxirgi xabardan 40 soniya o'tgach butun suhbat AI ga yuboriladi.
3. Siz javob yozmagan suhbatlardan tadbir qo'shilmaydi.
4. Faqat siz rozi bo'lgan yoki o'zingiz aytgan rejalar qo'shiladi, rad javoblari e'tiborga olinmaydi.
5. Topilgan tadbir haqida bot sizga xabar yuboradi, noto'g'ri bo'lsa `/del raqam`.

## Xavfsizlik

Quyidagi fayllarni **hech qachon** GitHubga yuklamang (ular `.gitignore` da):

- `.env` — barcha kalit va tokenlar
- `*.session` — Telegram akkauntingizga to'liq kirish beradi
- `events.json`, `users.json`, `state.json` — shaxsiy ma'lumotlar

Kalit yoki sessiya tasodifan yuklanib qolsa, darhol tokenni @BotFather da almashtiring, API kalitni qayta yarating va Telegramda Sozlamalar → Qurilmalar orqali userbot sessiyasini tugating.

## Litsenziya

Shaxsiy loyiha. Litsenziya keyin qo'shiladi.
