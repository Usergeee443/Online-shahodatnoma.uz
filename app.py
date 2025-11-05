from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import qrcode
from io import BytesIO
import base64
from functools import wraps

# .env faylini yuklash
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Upload papkasini yaratish
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database modellari
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    """Database jadvallarini yaratish va admin yaratish"""
    with app.app_context():
        db.create_all()
        
        # Admin yaratish/yangilash (.env dan o'qiladi)
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
        existing_admin = Admin.query.filter_by(username=admin_username).first()
        
        if existing_admin:
            # Admin mavjud - parolni yangilash (.env dagi parol bilan)
            existing_admin.password_hash = generate_password_hash(admin_password)
            db.session.commit()
            print(f"Admin parol yangilandi: username='{admin_username}'")
        else:
            # Yangi admin yaratish
            admin = Admin(
                username=admin_username,
                password_hash=generate_password_hash(admin_password)
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Yangi admin yaratildi: username='{admin_username}'")

def generate_qr_code(url):
    """QR kod yaratish"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

# Database initialization - gunicorn uchun
init_db()

# 404 Error handler
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# Bosh sahifa
@app.route('/')
def index():
    return render_template('index.html')

# Favicon uchun route (404 xatosi oldini olish)
@app.route('/favicon.ico')
def favicon():
    abort(404)

# Foydalanuvchi sahifasi
@app.route('/<username>')
def user_page(username):
    # Favicon va boshqa tizim so'rovlarini filtrlash
    if username in ['favicon.ico', 'robots.txt', 'sitemap.xml']:
        abort(404)
    document = Document.query.filter_by(username=username).first_or_404()
    pdf_url = url_for('serve_pdf', filename=document.filename)
    return render_template('user_page.html', pdf_url=pdf_url, username=username)

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    """PDF faylni xavfsiz tarzda uzatish"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)

# Admin login
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Muvaffaqiyatli kirildi!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Noto\'g\'ri login yoki parol!', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    session.clear()
    flash('Tizimdan chiqildi!', 'info')
    return redirect(url_for('admin_login'))

# Admin dashboard
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    documents = Document.query.order_by(Document.created_at.desc()).all()
    base_url = request.host_url.rstrip('/')
    return render_template('admin_dashboard.html', documents=documents, base_url=base_url)

# PDF yuklash
@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_pdf():
    if 'pdf_file' not in request.files:
        flash('Fayl tanlanmagan!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['pdf_file']
    username = request.form.get('username', '').strip()
    
    if file.filename == '' or not username:
        flash('Fayl va username majburiy!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if not file.filename.lower().endswith('.pdf'):
        flash('Faqat PDF fayllar qabul qilinadi!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Username formatini tozalash
    username = secure_filename(username).lower().replace(' ', '')
    
    # Oldingi faylni o'chirish (agar mavjud bo'lsa)
    existing_doc = Document.query.filter_by(username=username).first()
    if existing_doc:
        old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], existing_doc.filename)
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
        db.session.delete(existing_doc)
    
    # Yangi faylni saqlash
    filename = f"{username}_{os.urandom(8).hex()}.pdf"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Database'ga saqlash
    new_doc = Document(
        username=username,
        filename=filename,
        original_filename=file.filename
    )
    db.session.add(new_doc)
    db.session.commit()
    
    flash(f'PDF muvaffaqiyatli yuklandi! Username: {username}', 'success')
    return redirect(url_for('admin_dashboard'))

# PDF o'chirish
@app.route('/admin/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_pdf(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Faylni o'chirish
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(document)
    db.session.commit()
    
    flash('PDF muvaffaqiyatli o\'chirildi!', 'success')
    return redirect(url_for('admin_dashboard'))

# QR kod yaratish
@app.route('/admin/qr/<username>')
@login_required
def generate_qr(username):
    document = Document.query.filter_by(username=username).first_or_404()
    url = f"{request.host_url.rstrip('/')}/{document.username}"
    qr_code = generate_qr_code(url)
    return render_template('qr_code.html', qr_code=qr_code, url=url, username=username)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

