import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'avtosalon_pro_secret_key_2026'

# ✅ Исправление для Vercel: используем временную директорию /tmp для записи
# На Vercel корневая папка доступна только для чтения, единственная папка для записи это /tmp
if os.environ.get('VERCEL'):
    # Запущено на Vercel
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    app.config['DATABASE'] = '/tmp/avtosalon.db'
else:
    # Локальная разработка
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['DATABASE'] = 'avtosalon.db'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'admin'
        );
        
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            price REAL NOT NULL,
            vin TEXT UNIQUE,
            engine TEXT,
            color TEXT,
            equipment TEXT,
            status TEXT DEFAULT 'available',
            purchase_price REAL,
            description TEXT,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            middle_name TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            passport TEXT,
            address TEXT,
            client_type TEXT DEFAULT 'buyer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL,
            deal_price REAL NOT NULL,
            payment_method TEXT DEFAULT 'cash',
            deal_date TEXT NOT NULL,
            contract_number TEXT,
            status TEXT DEFAULT 'completed',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_id) REFERENCES cars (id),
            FOREIGN KEY (client_id) REFERENCES clients (id)
        );
        
        INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'admin123');
    ''')
    db.commit()

@app.route('/')
def index():
    db = get_db()
    cars = db.execute('SELECT * FROM cars WHERE status = "available" ORDER BY created_at DESC').fetchall()
    deals = db.execute('''
        SELECT deals.*, cars.brand, cars.model, cars.image,
               clients.first_name, clients.last_name
        FROM deals
        JOIN cars ON deals.car_id = cars.id
        JOIN clients ON deals.client_id = clients.id
        ORDER BY deals.created_at DESC LIMIT 10
    ''').fetchall()
    return render_template('index.html', cars=cars, deals=deals)

@app.route('/catalog')
def catalog():
    db = get_db()
    brand = request.args.get('brand', '')
    min_price = request.args.get('min_price', 0, type=float)
    max_price = request.args.get('max_price', 100000000, type=float)
    
    query = 'SELECT * FROM cars WHERE status = "available"'
    params = []
    
    if brand:
        query += ' AND brand = ?'
        params.append(brand)
    query += ' AND price >= ? AND price <= ?'
    params.extend([min_price, max_price])
    query += ' ORDER BY created_at DESC'
    
    cars = db.execute(query, params).fetchall()
    brands = db.execute('SELECT DISTINCT brand FROM cars WHERE status = "available"').fetchall()
    return render_template('catalog.html', cars=cars, brands=brands)

@app.route('/car/<int:car_id>')
def car_detail(car_id):
    db = get_db()
    car = db.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
    if car is None:
        flash('Автомобиль не найден')
        return redirect(url_for('catalog'))
    return render_template('car_detail.html', car=car)

# ===== АДМИН-ПАНЕЛЬ =====

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if user:
            session['admin'] = True
            session['username'] = user['username']
            return redirect(url_for('admin_dashboard'))
        flash('Неверный логин или пароль')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    cars_count = db.execute('SELECT COUNT(*) as count FROM cars').fetchone()['count']
    clients_count = db.execute('SELECT COUNT(*) as count FROM clients').fetchone()['count']
    deals_count = db.execute('SELECT COUNT(*) as count FROM deals').fetchone()['count']
    total_revenue = db.execute('SELECT SUM(deal_price) as total FROM deals').fetchone()
    total_revenue = total_revenue['total'] or 0
    return render_template('admin/dashboard.html', 
                         cars_count=cars_count, 
                         clients_count=clients_count,
                         deals_count=deals_count,
                         total_revenue=total_revenue)

# ===== УПРАВЛЕНИЕ АВТОМОБИЛЯМИ =====

@app.route('/admin/cars')
@admin_required
def admin_cars():
    db = get_db()
    cars = db.execute('SELECT * FROM cars ORDER BY created_at DESC').fetchall()
    return render_template('admin/cars.html', cars=cars)

@app.route('/admin/cars/add', methods=['GET', 'POST'])
@admin_required
def add_car():
    if request.method == 'POST':
        image_file = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_file = filename
        
        db = get_db()
        db.execute('''
            INSERT INTO cars (brand, model, year, price, vin, engine, color, equipment, status, purchase_price, description, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['brand'],
            request.form['model'],
            int(request.form['year']),
            float(request.form['price']),
            request.form.get('vin', ''),
            request.form.get('engine', ''),
            request.form.get('color', ''),
            request.form.get('equipment', ''),
            request.form.get('status', 'available'),
            float(request.form.get('purchase_price', 0)),
            request.form.get('description', ''),
            image_file
        ))
        db.commit()
        flash('Автомобиль добавлен')
        return redirect(url_for('admin_cars'))
    return render_template('admin/car_form.html')

@app.route('/admin/cars/edit/<int:car_id>', methods=['GET', 'POST'])
@admin_required
def edit_car(car_id):
    db = get_db()
    car = db.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()
    
    if request.method == 'POST':
        image_file = car['image']
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_file = filename
        
        db.execute('''
            UPDATE cars SET brand=?, model=?, year=?, price=?, vin=?, engine=?, color=?, 
                          equipment=?, status=?, purchase_price=?, description=?, image=?
            WHERE id=?
        ''', (
            request.form['brand'],
            request.form['model'],
            int(request.form['year']),
            float(request.form['price']),
            request.form.get('vin', ''),
            request.form.get('engine', ''),
            request.form.get('color', ''),
            request.form.get('equipment', ''),
            request.form.get('status', 'available'),
            float(request.form.get('purchase_price', 0)),
            request.form.get('description', ''),
            image_file,
            car_id
        ))
        db.commit()
        flash('Автомобиль обновлён')
        return redirect(url_for('admin_cars'))
    return render_template('admin/car_form.html', car=car)

@app.route('/admin/cars/delete/<int:car_id>')
@admin_required
def delete_car(car_id):
    db = get_db()
    db.execute('DELETE FROM cars WHERE id = ?', (car_id,))
    db.commit()
    flash('Автомобиль удалён')
    return redirect(url_for('admin_cars'))

# ===== УПРАВЛЕНИЕ КЛИЕНТАМИ =====

@app.route('/admin/clients')
@admin_required
def admin_clients():
    db = get_db()
    clients = db.execute('SELECT * FROM clients ORDER BY created_at DESC').fetchall()
    return render_template('admin/clients.html', clients=clients)

@app.route('/admin/clients/add', methods=['GET', 'POST'])
@admin_required
def add_client():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO clients (first_name, last_name, middle_name, phone, email, passport, address, client_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['first_name'],
            request.form['last_name'],
            request.form.get('middle_name', ''),
            request.form['phone'],
            request.form.get('email', ''),
            request.form.get('passport', ''),
            request.form.get('address', ''),
            request.form.get('client_type', 'buyer')
        ))
        db.commit()
        flash('Клиент добавлен')
        return redirect(url_for('admin_clients'))
    return render_template('admin/client_form.html')

@app.route('/admin/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@admin_required
def edit_client(client_id):
    db = get_db()
    client = db.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    
    if request.method == 'POST':
        db.execute('''
            UPDATE clients SET first_name=?, last_name=?, middle_name=?, phone=?, email=?, 
                             passport=?, address=?, client_type=?
            WHERE id=?
        ''', (
            request.form['first_name'],
            request.form['last_name'],
            request.form.get('middle_name', ''),
            request.form['phone'],
            request.form.get('email', ''),
            request.form.get('passport', ''),
            request.form.get('address', ''),
            request.form.get('client_type', 'buyer'),
            client_id
        ))
        db.commit()
        flash('Клиент обновлён')
        return redirect(url_for('admin_clients'))
    return render_template('admin/client_form.html', client=client)

@app.route('/admin/clients/delete/<int:client_id>')
@admin_required
def delete_client(client_id):
    db = get_db()
    db.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    db.commit()
    flash('Клиент удалён')
    return redirect(url_for('admin_clients'))

# ===== УПРАВЛЕНИЕ СДЕЛКАМИ =====

@app.route('/admin/deals')
@admin_required
def admin_deals():
    db = get_db()
    deals = db.execute('''
        SELECT deals.*, cars.brand, cars.model, cars.image,
               clients.first_name, clients.last_name, clients.phone
        FROM deals
        JOIN cars ON deals.car_id = cars.id
        JOIN clients ON deals.client_id = clients.id
        ORDER BY deals.created_at DESC
    ''').fetchall()
    return render_template('admin/deals.html', deals=deals)

@app.route('/admin/deals/add', methods=['GET', 'POST'])
@admin_required
def add_deal():
    db = get_db()
    cars = db.execute('SELECT id, brand, model FROM cars WHERE status = "available"').fetchall()
    clients = db.execute('SELECT id, first_name, last_name FROM clients').fetchall()
    
    if request.method == 'POST':
        car_id = int(request.form['car_id'])
        db.execute('''
            INSERT INTO deals (car_id, client_id, deal_price, payment_method, deal_date, contract_number, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            car_id,
            int(request.form['client_id']),
            float(request.form['deal_price']),
            request.form.get('payment_method', 'cash'),
            request.form['deal_date'],
            request.form.get('contract_number', ''),
            request.form.get('status', 'completed'),
            request.form.get('notes', '')
        ))
        db.execute('UPDATE cars SET status = "sold" WHERE id = ?', (car_id,))
        db.commit()
        flash('Сделка оформлена')
        return redirect(url_for('admin_deals'))
    return render_template('admin/deal_form.html', cars=cars, clients=clients)

@app.route('/admin/deals/edit/<int:deal_id>', methods=['GET', 'POST'])
@admin_required
def edit_deal(deal_id):
    db = get_db()
    deal = db.execute('SELECT * FROM deals WHERE id = ?', (deal_id,)).fetchone()
    cars = db.execute('SELECT id, brand, model FROM cars').fetchall()
    clients = db.execute('SELECT id, first_name, last_name FROM clients').fetchall()
    
    if request.method == 'POST':
        db.execute('''
            UPDATE deals SET car_id=?, client_id=?, deal_price=?, payment_method=?, 
                           deal_date=?, contract_number=?, status=?, notes=?
            WHERE id=?
        ''', (
            int(request.form['car_id']),
            int(request.form['client_id']),
            float(request.form['deal_price']),
            request.form.get('payment_method', 'cash'),
            request.form['deal_date'],
            request.form.get('contract_number', ''),
            request.form.get('status', 'completed'),
            request.form.get('notes', ''),
            deal_id
        ))
        db.commit()
        flash('Сделка обновлена')
        return redirect(url_for('admin_deals'))
    return render_template('admin/deal_form.html', deal=deal, cars=cars, clients=clients)

@app.route('/admin/deals/delete/<int:deal_id>')
@admin_required
def delete_deal(deal_id):
    db = get_db()
    deal = db.execute('SELECT car_id FROM deals WHERE id = ?', (deal_id,)).fetchone()
    db.execute('UPDATE cars SET status = "available" WHERE id = ?', (deal['car_id'],))
    db.execute('DELETE FROM deals WHERE id = ?', (deal_id,))
    db.commit()
    flash('Сделка удалена')
    return redirect(url_for('admin_deals'))

# ===== ОТЧЁТЫ =====

@app.route('/admin/reports')
@admin_required
def reports():
    db = get_db()
    total_revenue = db.execute('SELECT SUM(deal_price) as total FROM deals WHERE status = "completed"').fetchone()['total'] or 0
    deals_count = db.execute('SELECT COUNT(*) as count FROM deals WHERE status = "completed"').fetchone()['count']
    avg_price = db.execute('SELECT AVG(deal_price) as avg FROM deals WHERE status = "completed"').fetchone()['avg'] or 0
    
    popular_cars = db.execute('''
        SELECT cars.brand, cars.model, COUNT(*) as sales_count
        FROM deals
        JOIN cars ON deals.car_id = cars.id
        GROUP BY cars.brand, cars.model
        ORDER BY sales_count DESC
        LIMIT 10
    ''').fetchall()
    
    monthly_sales = db.execute('''
        SELECT strftime('%Y-%m', deal_date) as month, 
               COUNT(*) as deals_count, 
               SUM(deal_price) as revenue
        FROM deals
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''').fetchall()
    
    return render_template('admin/reports.html', 
                         total_revenue=total_revenue,
                         deals_count=deals_count,
                         avg_price=avg_price,
                         popular_cars=popular_cars,
                         monthly_sales=monthly_sales)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # ✅ Исправление для Vercel: сначала ищем в /tmp, потом в исходной папке
    if os.environ.get('VERCEL'):
        tmp_path = os.path.join('/tmp/uploads', filename)
        if os.path.exists(tmp_path):
            return send_from_directory('/tmp/uploads', filename)
    # Если нет в /tmp - отдаём из оригинальной папки uploads
    return send_from_directory('uploads', filename)

@app.route('/static/<path:filename>')
def static_file(filename):
    return send_from_directory('static', filename)

# Инициализация при запуске (для Vercel и других production-сред)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def initialize_app():
    """Инициализация базы данных при старте приложения"""
    try:
        # При первом запуске копируем исходную базу из корня в /tmp
        if os.environ.get('VERCEL') and not os.path.exists(app.config['DATABASE']):
            import shutil
            if os.path.exists('avtosalon.db'):
                shutil.copy('avtosalon.db', app.config['DATABASE'])
                print(f"✅ База данных скопирована в /tmp")
        
        with app.app_context():
            init_db()
    except Exception as e:
        print(f"DB init error: {e}")

# Вызываем инициализацию при импорте модуля (для Vercel)
initialize_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
