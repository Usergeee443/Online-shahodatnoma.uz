# Online-shahodatnoma.uz

Universitet uchun PDF shahodatnoma tizimi. Adminlar PDF fayllarni yuklab, har bir foydalanuvchi uchun unique link yaratadi.

## Xususiyatlar

- ✅ Admin panel - login/parol himoyasi
- ✅ PDF yuklash va username bilan bog'lash
- ✅ Avtomatik unique link yaratish
- ✅ QR kod yaratish va yuklab olish
- ✅ Minimal foydalanuvchi sahifasi - faqat PDF ko'rinadi
- ✅ PDF.js va iframe orqali PDF ko'rsatish
- ✅ SQLite database (loyiha ichida, avtomatik yaratiladi)
- ✅ PDF siqish va tezkor statik taqdim etish

## O'rnatish

### 1. Talablar

- Python 3.8+
- pip

### 2. Loyihani klonlash va o'rnatish

```bash
# Repository ni klonlash
cd Online-shahodatnoma.uz

# Virtual environment yaratish
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows

# Kerakli paketlarni o'rnatish
pip install -r requirements.txt
```

### 3. Database sozlash

Loyiha **SQLite** ishlatadi - database fayl loyiha ichida (`database.db`) avtomatik yaratiladi. Qo'shimcha sozlash talab qilmaydi.

Agar MySQL ishlatishni xohlasangiz, `app.py` faylida database URL ni o'zgartiring:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:password@localhost/shahodatnoma_db'
```

### 4. Environment o'zgaruvchilari

`.env` fayl yaratish (ixtiyoriy):

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///database.db  # default
# Render persistent disk (ixtiyoriy)
# DATA_DIR=/data
```

### 5. Ishga tushirish

```bash
python app.py
```

Server `http://localhost:5000` da ishga tushadi.

## Foydalanish

### Admin Panel

1. `http://localhost:5000/admin` ga kiring
2. Default login: `admin` / `admin123`
3. PDF yuklash:
   - Username kiriting (masalan: `nurmuxammadrayimiv`)
   - PDF fayl tanlang
   - "PDF Yuklash" tugmasini bosing
4. Link va QR kod:
   - Avtomatik link yaratiladi: `http://localhost:5000/nurmuxammadrayimiv`
   - "QR Kod" tugmasini bosing va QR kodni yuklab oling

### Foydalanuvchi Sahifasi

Foydalanuvchi `http://localhost:5000/<username>` linkini ochganda:
- PDF avtomatik ochiladi
- Hech qanday qo'shimcha elementlar yo'q
- Minimal va tez yuklanadi

## Production Deployment

### HTTPS sozlash

Production uchun HTTPS majburiy. Nginx yoki Apache reverse proxy orqali sozlash:

#### Nginx misoli:

```nginx
server {
    listen 443 ssl http2;
    server_name online-shahodatnoma.uz;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Gunicorn orqali ishga tushirish

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Xavfsizlik

- ✅ Admin login/parol himoyasi
- ✅ Session management
- ✅ Secure filename handling
- ✅ File type validation (faqat PDF)
- ✅ SQL injection himoyasi (SQLAlchemy ORM)
- ⚠️ Production da SECRET_KEY ni o'zgartiring
- ⚠️ Production da HTTPS majburiy

## Texnologiyalar

- **Backend**: Python Flask
- **Database**: SQLite (default, loyiha ichida) / MySQL (ixtiyoriy, SQLAlchemy ORM)
- **Frontend**: HTML5 + TailwindCSS
- **PDF Viewer**: PDF.js + iframe
- **QR Kod**: qrcode library

## Muammolarni hal qilish

### Database ulanish xatosi

SQLite uchun muammo bo'lmasligi kerak - database fayl avtomatik yaratiladi. Agar MySQL ishlatmoqchi bo'lsangiz, MySQL server ishlayotganini tekshiring:

```bash
mysql -u user -p
```

### PDF ko'rinmaydi

- Fayl mavjudligini tekshiring: `uploads/` papkasi
- Browser console da xatolarni tekshiring
- PDF.js CDN ga ulanishni tekshiring

## Render.com ga Deploy qilish

### 1. Render.com da yangi Web Service yaratish

1. [Render.com](https://render.com) ga kirish
2. "New +" → "Web Service" tanlang
3. GitHub repository ni ulang

### 2. Environment Variables sozlash

Render dashboard'da "Environment" bo'limiga quyidagi o'zgaruvchilarni qo'shing:

```
SECRET_KEY=your-very-secret-key-minimum-32-characters-long
DATABASE_URL=sqlite:///database.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password-here
FLASK_DEBUG=False
PORT=10000
```

**Muhim:** `SECRET_KEY` va `ADMIN_PASSWORD` ni kuchli qiymatlar bilan o'zgartiring!

### 3. Build sozlamalari

Render dashboard'da:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Python Version:** `3.12` (Settings → Build & Deploy → Python Version)

Yoki `Procfile` fayl avtomatik ishlatiladi.

**Eslatma:** Agar build xatosi bo'lsa, Render dashboard'da "Clear build cache" tugmasini bosing va qayta deploy qiling.

### 3.1. Render persistent disk (ma'lumotlarni saqlab qolish)

1. Render Web Service → **Settings → Disks → Add Disk**
   - **Mount Path:** `/data`
   - **Size:** ehtiyojingizga mos (masalan, 1 GB)
2. Environment Variables bo'limiga qo'shing: `DATA_DIR=/data`
3. Agar SQLite ishlatsangiz, `DATABASE_URL` ni qo'ymasangiz ham yozuvlar `/data/database.db` da saqlanadi.
4. PDF yuklash papkasi ham shu diskda (`/data/uploads`) saqlanadi.
5. Deploydan so'ng «[Manual Deploy] → Clear build cache & deploy» ni bosing.

Shu tartibda, yangi deploylarda ham ma'lumotlar o'chmaydi.

### 4. Deploy

Render avtomatik deploy qiladi. Birinchi deploy vaqtida database va admin yaratiladi.

### 5. HTTPS

Render avtomatik HTTPS ta'minlaydi. Domain sozlang va saytga kirishingiz mumkin.

### Eslatmalar

- Render.com SQLite ni qo'llab-quvvatlaydi (ephemeral disk)
- Production uchun PostgreSQL yoki MySQL ishlatish tavsiya etiladi
- `SECRET_KEY` va `ADMIN_PASSWORD` ni hech qachon public qilmang
- `.env` fayl gitga kirmaydi (`.gitignore` da)

## PDF tezkor ishlash va optimizatsiya

- Fayllar `/static/docs/` papkasidan statik tarzda beriladi (cache-friendly)
- `Cache-Control: public, max-age=86400, immutable`, `ETag` va `Last-Modified` headerlari qo'llanadi
- PDF xizmatga yuklanganda avtomatik siqiladi (`pikepdf`, linearize) va nomi yagona qilib saqlanadi
- Frontend `<embed>` emas, custom PDF.js renderer (canvas) orqali sahifalarni lazy render qiladi
- Foydalanuvchi “Loading…” ko'radi, PDF tayyor bo'lishi bilan sahifa ko'rsatiladi

## Litsenziya

Bu loyiha universitet uchun yaratilgan.

