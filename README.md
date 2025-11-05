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

## Litsenziya

Bu loyiha universitet uchun yaratilgan.

