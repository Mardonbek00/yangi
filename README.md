# O'qchi-Yaypan taxi bot

Telegram orqali taxi chaqirish/haydovchi bo'lish botining to'liq kodi. Python +
`python-telegram-bot` + SQLAlchemy, ma'lumotlar bazasi — oddiy SQLite fayl.

## Funksiyalar

- **Yo'lovchi**: taxi chaqirish (yo'nalish → telefon → izoh), buyurtmalar tarixi, safar
  tugagach haydovchini baholash.
- **Haydovchi**: ariza topshirish (ism, telefon, mashina raqami/rusumi/rangi) → admin
  tasdiqlaydi → panel ochiladi (liniyaga chiqish, balans, to'ldirish, safarlar tarixi).
- **Navbat**: liniyaga chiqqan vaqti bo'yicha FIFO, har bir haydovchiga 1.5 daqiqa javob
  berish uchun, 15 daqiqada hech kim olmasa buyurtma avtomatik bekor bo'ladi. Haydovchi
  bir vaqtda 4 tagacha yo'lovchi ola oladi (sig'im to'lgach yoki "Jo'nash" bosilganda
  safar yakunlanadi va yo'lovchilardan baho so'raladi).
- **Balans**: har bir qabul qilingan yo'lovchi uchun komissiya balansdan yechiladi
  (summasi admin panelda o'zgartiriladi). Balans ≤ 0 bo'lsa haydovchi liniyaga chiqa
  olmaydi. To'ldirish — kartaga pul tashlab, skrinshot yuborish, admin tasdiqlaydi.
- **Admin panel**: faqat `ADMIN_IDS`dagi Telegram ID'lar ko'radi — haydovchi arizalari,
  balans so'rovlari, yo'nalishlar qo'shish, komissiya va karta ma'lumotlarini
  o'zgartirish, statistika (bugungi/oylik buyurtmalar, liniyadagi haydovchilar soni).

## Loyihaning tuzilishi

```
config.py            — sozlamalar (token, DB, admin ID, vaqt limitlari)
db.py                — SQLAlchemy engine/session
models.py             — jadvallar (User, Driver, Direction, Order, Topup, Setting...)
utils.py               — yordamchi funksiyalar
keyboards.py           — tugmalar
matching.py             — navbat/moslashtirish logikasi (asosiy "miya")
handlers_common.py      — /start, buyurtmalar tarixi, reyting
handlers_passenger.py   — taxi chaqirish oqimi
handlers_driver.py      — haydovchi arizasi, panel, liniya, balans
handlers_admin.py       — admin panel
main.py                 — hammasini bog'lab, botni ishga tushiradi
requirements.txt        — Python paketlari
render.yaml             — Render Blueprint uchun ixtiyoriy fayl (pastga qarang)
```

Loyihada `.env` yoki `.python-version` kabi maxsus fayllarga bog'liqlik yo'q — barcha
sozlamalar oddiy muhit o'zgaruvchilari (environment variables) orqali beriladi. Bu
GitHub'ga yuklaganda "yashirin fayl tushib qoldi" kabi muammolarning oldini oladi.

## 1. Lokal ishga tushirish

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

export BOT_TOKEN="sizning_tokeningiz"
export ADMIN_IDS="sizning_telegram_id"
python main.py
```

Windows PowerShell'da:
```powershell
$env:BOT_TOKEN="sizning_tokeningiz"
$env:ADMIN_IDS="sizning_telegram_id"
python main.py
```

Bot token olish uchun Telegram'da **@BotFather** ga yozing (`/newbot`).
O'zingizning Telegram ID'ingizni bilish uchun **@userinfobot** ga yozing.

Birinchi marta ishga tushganda `taxi_bot.db` (SQLite) fayli avtomatik yaratiladi.

## 2. Render.com'ga deploy qilish (GitHub orqali, qo'lda)

Bu usulda `render.yaml` fayli **ishlatilmaydi** — hammasi Render panelidan qo'lda
sozlanadi, shuning uchun hech qanday maxsus/yashirin fayl kerak emas.

1. Kodni GitHub repozitoriyasiga joylang (barcha `.py` fayllar, `requirements.txt`).
2. [Render.com](https://render.com) da **New → Background Worker** tanlang va
   GitHub repozitoriyangizni ulang.
3. Sozlamalarni kiriting:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. **Environment** bo'limida quyidagi o'zgaruvchilarni qo'shing:

   | Key | Value | Izoh |
   |---|---|---|
   | `BOT_TOKEN` | BotFather bergan token | majburiy |
   | `ADMIN_IDS` | sizning Telegram ID | majburiy |
   | `PYTHON_VERSION` | `3.11.9` | majburiy — Render'ning standart versiyasi (3.14) `python-telegram-bot` bilan mos kelmaydi |
   | `DATABASE_URL` | `sqlite:///taxi_bot.db` | ixtiyoriy, standart shu bilan bir xil |

5. **Create Background Worker** / **Deploy** tugmasini bosing.
6. Deploy tugagach, botga Telegram'da `/start` yozib tekshiring.

**Muhim eslatma (fayl-baza haqida):** Render'ning bepul tarifida doimiy disk
(persistent disk) yo'q — har safar kodni qayta deploy qilganingizda yoki server
qayta ishga tushganda `taxi_bot.db` fayli **tozalanib, bo'sh holatga qaytishi
mumkin** — barcha foydalanuvchilar, haydovchilar va buyurtmalar tarixi yo'qoladi.
Buni istamasangiz, keyinchalik pullik tarifga o'tib doimiy disk ulash yoki Postgres
bazasiga o'tish mumkin (kod buni qo'llab-quvvatlaydi — `DATABASE_URL`ni
`postgresql://...` ga o'zgartirish yetarli).

### Ixtiyoriy: Blueprint orqali deploy

Agar xohlasangiz, `render.yaml` fayli ham loyihada bor — Render'da **New →
Blueprint** tanlab, repozitoriyani ulasangiz, yuqoridagi sozlamalarning aksariyati
(shu jumladan `PYTHON_VERSION`) avtomatik o'rnatiladi, faqat `BOT_TOKEN` va
`ADMIN_IDS`ni qo'lda kiritishingiz kerak bo'ladi. Ikkala usul ham bir xil natija
beradi — qaysi biri qulay bo'lsa, shuni tanlang.

## 3. Birinchi sozlash (bot ishga tushgach)

1. O'zingizga `/start` yuboring — `ADMIN_IDS`da bo'lsangiz, "🛠 Admin panel" tugmasi
   chiqadi.
2. Admin panelda:
   - **Yo'nalish qo'shish** — kamida bitta yo'nalish qo'shing (masalan: "O'qchi → Yaypan").
   - **Komissiya summasini o'zgartirish** — har bir yo'lovchi uchun necha so'm
     olinishini belgilang.
   - **Karta ma'lumotlarini o'zgartirish** — balans to'ldirish uchun karta raqami va
     egasining ismini kiriting.
3. Shundan keyin haydovchilar ariza topshirib, siz tasdiqlashingiz mumkin.

## Keyingi rivojlantirish g'oyalari

- Yo'nalishlarni o'chirish/tahrirlash, haydovchini vaqtincha bloklash.
- Har bir haydovchiga alohida statistikalar (topgan zakazlar soni, daromad).
- Ko'p tilli interfeys, xatoliklarni kuzatish uchun logging'ni fayl/kanalga yozish.

## Xatoliklarni bartaraf etish

**`RuntimeError: There is no current event loop in thread 'MainThread'`** —
Render'ning standart Python versiyasi (3.14) `python-telegram-bot` bilan mos
kelmaydi. Environment'ga `PYTHON_VERSION=3.11.9` qo'shilganiga ishonch hosil qiling
(2-bo'limdagi jadvalga qarang), so'ng **Manual Deploy → Clear build cache &
deploy** qiling.

**`telegram.error.Conflict: terminated by other getUpdates request`** — shu bot
tokeni bilan bir vaqtning o'zida ikkinchi jarayon ham ishlayotganini bildiradi
(masalan, lokal kompyuteringizda `python main.py` hali ham ochiq turibdi, yoki
eski deploy hali to'liq to'xtamagan). Lokal jarayonni to'xtating (Ctrl+C), Render
xizmatini **Restart** qiling; muammo davom etsa, @BotFather orqali tokenni
`/revoke` qilib yangisini oling va Environment'dagi `BOT_TOKEN`ni yangilang.

**`BOT_TOKEN muhit o'zgaruvchisi berilmagan`** — Environment bo'limida `BOT_TOKEN`
qatori bo'sh yoki umuman yo'q. Uni to'ldirib **Save Changes** bosing.
