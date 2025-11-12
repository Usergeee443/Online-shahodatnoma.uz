from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
    Response,
    stream_with_context,
    make_response
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import tempfile
import shutil
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote
import os
import qrcode
from io import BytesIO
import base64
from functools import wraps

try:
    import pikepdf
except ImportError:  # Render kabi muhitlarda build xatosi bo'lishi mumkin
    pikepdf = None

# .env faylini yuklash
load_dotenv()

app = Flask(
    __name__,
    instance_relative_config=True,
    static_url_path='/static',
    static_folder='static'
)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

data_directory = os.environ.get('DATA_DIR')
if data_directory:
    data_directory = os.path.abspath(data_directory)
else:
    data_directory = app.instance_path

os.makedirs(data_directory, exist_ok=True)

default_db_path = os.path.join(data_directory, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(data_directory, 'uploads')
app.config['STATIC_PDF_FOLDER'] = os.path.join(app.static_folder, 'docs')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

# Upload papkasini yaratish
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_PDF_FOLDER'], exist_ok=True)

# Database modellari
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=True)  # PDF yuklanmasdan ham username yaratish mumkin
    original_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    def has_pdf(self):
        """PDF yuklanganligini tekshirish"""
        return self.filename is not None and self.filename != ''

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
        inspector = inspect(db.engine)
        needs_migration = False

        if 'document' in inspector.get_table_names():
            columns = {col['name']: col for col in inspector.get_columns('document')}
            filename_col = columns.get('filename')
            original_col = columns.get('original_filename')
            if (filename_col and not filename_col.get('nullable', True)) or (
                original_col and not original_col.get('nullable', True)
            ):
                needs_migration = True

        if needs_migration:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE document RENAME TO document_old"))
                connection.execute(text(
                    """
                    CREATE TABLE document (
                        id INTEGER NOT NULL PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        filename VARCHAR(255),
                        original_filename VARCHAR(255),
                        created_at DATETIME DEFAULT (CURRENT_TIMESTAMP)
                    )
                    """
                ))
                connection.execute(text(
                    """
                    INSERT INTO document (id, username, filename, original_filename, created_at)
                    SELECT id, username, filename, original_filename, created_at FROM document_old
                    """
                ))
                connection.execute(text("DROP TABLE document_old"))
            print("Document jadvali migratsiya qilindi (filename nullable).")

        db.create_all()

    # Eski fayllarni static papkaga ko'chirish
        for document in Document.query.filter(Document.filename != None).all():  # noqa: E711
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], document.filename)
            new_path = os.path.join(app.config['STATIC_PDF_FOLDER'], document.filename)
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.move(old_path, new_path)
        
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


def render_no_cache(template_name, **context):
    response = make_response(render_template(template_name, **context))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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
    
    # PDF yuklanmagan bo'lsa
    if not document.has_pdf():
        return render_no_cache('user_page_no_pdf.html', username=username)

    viewer_url = url_for('pdf_viewer', username=document.username)
    download_url = url_for('serve_pdf', filename=document.filename)

    user_agent = (request.user_agent.string or '').lower()
    if 'android' in user_agent:
        return redirect(download_url)

    return render_no_cache('user_page.html', viewer_url=viewer_url, download_url=download_url, username=username)

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    """PDF faylni optimallashtirilgan holda uzatish"""
    file_path = os.path.join(app.config['STATIC_PDF_FOLDER'], filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        abort(404)

    file_stat = os.stat(file_path)
    last_modified = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).replace(microsecond=0)
    etag_base = f"{file_stat.st_ino}-{file_stat.st_size}-{file_stat.st_mtime}".encode('utf-8')
    etag = hashlib.sha1(etag_base).hexdigest()

    # Conditional GET: ETag
    if request.headers.get('If-None-Match') == etag:
        return Response(status=304)

    # Conditional GET: Last-Modified
    if_modified_since = request.headers.get('If-Modified-Since')
    if if_modified_since:
        try:
            ims = parsedate_to_datetime(if_modified_since)
            if ims.tzinfo is None:
                ims = ims.replace(tzinfo=timezone.utc)
            if ims >= last_modified:
                return Response(status=304)
        except (TypeError, ValueError):
            pass

    force_download = request.args.get('download') == '1'
    range_header = request.headers.get('Range')
    status_code = 200
    content_range = None
    chunk_size = 8192
    start = 0
    end = file_stat.st_size - 1

    if range_header:
        # Format: bytes=start-end
        try:
            units, range_spec = range_header.split('=', 1)
            if units.strip().lower() == 'bytes':
                range_spec = range_spec.strip()
                if ',' in range_spec:
                    range_spec = range_spec.split(',', 1)[0]
                start_str, end_str = range_spec.split('-', 1)
                if start_str:
                    start = int(start_str)
                if end_str:
                    end = int(end_str)
                if start > end or end >= file_stat.st_size:
                    start = 0
                    end = file_stat.st_size - 1
                status_code = 206
                content_range = f'bytes {start}-{end}/{file_stat.st_size}'
        except ValueError:
            start = 0
            end = file_stat.st_size - 1

    length = end - start + 1

    def generate(start_pos, end_pos):
        with open(file_path, 'rb') as pdf_file:
            pdf_file.seek(start_pos)
            bytes_remaining = length
            while bytes_remaining > 0:
                read_size = min(chunk_size, bytes_remaining)
                data = pdf_file.read(read_size)
                if not data:
                    break
                yield data
                bytes_remaining -= len(data)

    response = Response(stream_with_context(generate(start, end)), status=status_code, mimetype='application/pdf')
    response.headers['Content-Length'] = str(length)
    disposition_type = 'attachment' if force_download else 'inline'
    response.headers['Content-Disposition'] = f'{disposition_type}; filename="{filename}"'
    response.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Accept-Ranges'] = 'bytes'
    if content_range:
        response.headers['Content-Range'] = content_range

    return response

# PDF viewer sahifasi
@app.route('/viewer/<username>')
def pdf_viewer(username):
    if username in ['favicon.ico', 'robots.txt', 'sitemap.xml']:
        abort(404)
    document = Document.query.filter_by(username=username).first_or_404()
    if not document.has_pdf():
        abort(404)
    pdf_url = url_for('serve_pdf', filename=document.filename)
    download_url = pdf_url
    return render_no_cache('pdf_viewer.html', pdf_url=pdf_url, download_url=download_url, username=username)

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

# Username yaratish (PDFsiz)
@app.route('/admin/create-username', methods=['POST'])
@login_required
def create_username():
    username = request.form.get('username', '').strip()
    
    if not username:
        flash('Username majburiy!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Username formatini tozalash
    username = secure_filename(username).lower().replace(' ', '')
    
    # Username mavjudligini tekshirish
    existing_doc = Document.query.filter_by(username=username).first()
    if existing_doc:
        flash(f'Username "{username}" allaqachon mavjud!', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Yangi username yaratish (PDFsiz)
    new_doc = Document(
        username=username,
        filename=None,
        original_filename=None
    )
    db.session.add(new_doc)
    db.session.commit()
    
    flash(f'Username "{username}" muvaffaqiyatli yaratildi! Endi QR kod yuklab olishingiz mumkin.', 'success')
    return redirect(url_for('admin_dashboard'))

# PDF yuklash (mavjud username ga)
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
    
    # Username mavjudligini tekshirish
    existing_doc = Document.query.filter_by(username=username).first()
    if not existing_doc:
        flash(f'Username "{username}" topilmadi! Avval username yarating.', 'error')
        return redirect(url_for('admin_dashboard'))

    # Vaqtinchalik faylga saqlash
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', dir=app.config['UPLOAD_FOLDER']) as tmp:
        file.save(tmp.name)
        temp_input = tmp.name

    # PDF ni siqish va optimallashtirish
    optimized_filename = f"{username}_{os.urandom(8).hex()}.pdf"
    optimized_path = os.path.join(app.config['STATIC_PDF_FOLDER'], optimized_filename)

    compression_succeeded = False
    if pikepdf is not None:
        try:
            with pikepdf.open(temp_input) as pdf:
                save_kwargs = {'linearize': True}
                compression_level = getattr(pikepdf, 'CompressionLevel', None)
                if compression_level:
                    save_kwargs['compression'] = compression_level.default
                try:
                    pdf.save(optimized_path, optimize_streams=True, **save_kwargs)
                except TypeError:
                    pdf.save(optimized_path, **save_kwargs)
                compression_succeeded = True
        except Exception as exc:  # noqa: F841
            compression_succeeded = False

    if not compression_succeeded:
        shutil.copyfile(temp_input, optimized_path)

    # Vaqtinchalik faylni o'chirish
    try:
        os.remove(temp_input)
    except OSError:
        pass

    # Oldingi PDF faylni o'chirish (agar mavjud bo'lsa)
    if existing_doc.filename:
        old_static_path = os.path.join(app.config['STATIC_PDF_FOLDER'], existing_doc.filename)
        if os.path.exists(old_static_path):
            os.remove(old_static_path)

    # Database'ni yangilash
    existing_doc.filename = optimized_filename
    existing_doc.original_filename = file.filename
    db.session.commit()
    
    flash(f'PDF muvaffaqiyatli yuklandi! Username: {username}', 'success')
    return redirect(url_for('admin_dashboard'))

# Username va PDF o'chirish
@app.route('/admin/delete/<int:doc_id>', methods=['POST'])
@login_required
def delete_pdf(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # PDF faylni o'chirish (agar mavjud bo'lsa)
    if document.filename:
        file_path = os.path.join(app.config['STATIC_PDF_FOLDER'], document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # Username va hujjatni o'chirish
    db.session.delete(document)
    db.session.commit()
    
    flash('Username va hujjat muvaffaqiyatli o\'chirildi!', 'success')
    return redirect(url_for('admin_dashboard'))

# QR kod yaratish (PDF yuklanmasdan ham)
@app.route('/admin/qr/<username>')
@login_required
def generate_qr(username):
    document = Document.query.filter_by(username=username).first_or_404()
    url = f"{request.host_url.rstrip('/')}/{document.username}"
    qr_code = generate_qr_code(url)
    has_pdf = document.has_pdf()
    return render_template('qr_code.html', qr_code=qr_code, url=url, username=username, has_pdf=has_pdf)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

