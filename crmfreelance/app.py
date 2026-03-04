"""
Freelance CRM - A lightweight CRM for freelancers
Built with Flask + SQLite
"""

import os
import re
import csv
import io
import zipfile
import sqlite3
import bcrypt
import secrets
import json
import stripe
from datetime import datetime
from flask import Flask, g, request, render_template, flash, redirect, url_for, abort, make_response, session, jsonify, send_file
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from translations import TRANSLATIONS, get_text

app = Flask(__name__)
app.secret_key = os.environ.get('CRM_SECRET_KEY', 'change-me-please')

# Security-related config (toggle secure cookies via env for dev)
app.config.update({
    'WTF_CSRF_ENABLED': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax'),
    'SESSION_COOKIE_SECURE': os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true',
    'REMEMBER_COOKIE_HTTPONLY': True,
    'REMEMBER_COOKIE_SECURE': os.environ.get('REMEMBER_COOKIE_SECURE', 'False').lower() == 'true',
})

# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    app=app,
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'crm.db')

# Stripe config (set STRIPE_SECRET_KEY in env)
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')


# User Model

class User(UserMixin):
    def __init__(self, id_, name, email, telegram_code=None):
        self.id = id_
        self.name = name
        self.email = email
        self.telegram_code = telegram_code


@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('SELECT id, name, email, telegram_code FROM users WHERE id = ?', (user_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return User(row[0], row[1], row[2], row[3])
    except sqlite3.Error:
        return None
    return None


# Database

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# Billing
def requires_plan(min_plan):
    from functools import wraps
    order = {'free': 0, 'pro': 1, 'team': 2}

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                cur = conn.cursor()
                cur.execute('SELECT plan FROM users WHERE id = ?', (current_user.id,))
                row = cur.fetchone()
                conn.close()
            except Exception:
                row = None

            user_plan = (row[0] if row and row[0] else 'free')
            if order.get(user_plan, 0) < order.get(min_plan, 0):
                return abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('PRAGMA foreign_keys = ON')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            profession TEXT DEFAULT 'freelancer',
            preferred_reminder TEXT DEFAULT 'interface'
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            contact TEXT,
            status TEXT CHECK(status IN ('active','cold','archived')) DEFAULT 'active',
            last_contact DATE,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            client_id INTEGER,
            title TEXT NOT NULL,
            status TEXT CHECK(status IN ('discussion','in_progress','paused','completed')) DEFAULT 'discussion',
            budget REAL,
            deadline DATE,
            description TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE SET NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            project_id INTEGER,
            amount REAL NOT NULL,
            status TEXT CHECK(status IN ('pending','partial','paid')) DEFAULT 'pending',
            due_date DATE,
            comment TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_read BOOLEAN DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS system_alerts (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    c.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('service_status', 'green')")
    c.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('maintenance_mode', 'off')")
    c.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('maintenance_message', '')")

    # Export logs (track admin exports of user data)
    c.execute('''
        CREATE TABLE IF NOT EXISTS export_logs (
            id INTEGER PRIMARY KEY,
            admin_id INTEGER,
            user_id INTEGER,
            email TEXT,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    try:
        c.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'free'")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN telegram_code TEXT UNIQUE")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()


# Internationalization

def get_lang():
    return session.get('lang', 'en')


def t(key, **kwargs):
    return get_text(key, get_lang(), **kwargs)


@app.context_processor
def inject_translations():
    return {'t': t, 'lang': get_lang()}


@app.context_processor
def inject_csrf():
    return {'csrf_token': lambda: generate_csrf()}


@app.route('/lang/<lang_code>')
def set_language(lang_code):
    if lang_code in ('en', 'ru'):
        session['lang'] = lang_code
    return redirect(request.referrer or '/')


# Auth

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        return login()
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        password_confirm = request.form.get('confirm') or ''

        if not name or not email or not password:
            flash(t('fill_required'))
            return render_template('register.html')

        if password != password_confirm:
            flash(t('passwords_mismatch'))
            return render_template('register.html')

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cur.fetchone():
                flash(t('email_exists'))
                return render_template('register.html')

            pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            pw_hash_str = pw_hash.decode('utf-8')

            cur.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)', (name, email, pw_hash_str))
            db.commit()
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('register.html')

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('6 per minute')
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not email or not password:
            flash(t('fill_required'))
            return render_template('login.html')

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute('SELECT id, name, email, password_hash, profession FROM users WHERE email = ?', (email,))
            row = cur.fetchone()
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('login.html')

        if not row:
            flash(t('invalid_credentials'))
            return render_template('login.html')

        user_id, name, email_db, pw_hash_str, profession = row[0], row[1], row[2], row[3], row[4]

        try:
            pw_ok = bcrypt.checkpw(password.encode('utf-8'), pw_hash_str.encode('utf-8'))
        except Exception:
            pw_ok = False

        if not pw_ok:
            flash(t('invalid_credentials'))
            return render_template('login.html')

        user = User(user_id, name, email_db)
        login_user(user)
        
        # Check if profession is not set (first login)
        if not profession or profession == 'freelancer':
            return redirect('/onboarding')
        
        return redirect('/dashboard')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(t('logged_out'))
    return redirect('/')


# Dashboard

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM clients WHERE user_id = ? AND status = 'active'", (current_user.id,))
    active_clients = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE user_id = ? AND status = 'pending'", (current_user.id,))
    pending_amount = cur.fetchone()[0]

    cur.execute('''
        SELECT p.title, c.name as client_name, p.deadline
        FROM projects p
        LEFT JOIN clients c ON p.client_id = c.id
        WHERE p.user_id = ? AND p.deadline >= DATE('now')
        ORDER BY p.deadline
        LIMIT 3
    ''', (current_user.id,))
    upcoming_deadlines = cur.fetchall()

    # Get profession for personalized onboarding message
    cur.execute('SELECT profession FROM users WHERE id = ?', (current_user.id,))
    profession = cur.fetchone()[0] or 'freelancer'

    # Get expected payments (payments due within next 30 days)
    cur.execute('''
        SELECT pay.amount, c.name as client_name, pay.due_date, p.title as project_title
        FROM payments pay
        LEFT JOIN projects p ON pay.project_id = p.id
        LEFT JOIN clients c ON p.client_id = c.id
        WHERE pay.user_id = ? AND pay.status = 'pending' AND pay.due_date BETWEEN DATE('now') AND DATE('now', '+30 days')
        ORDER BY pay.due_date
    ''', (current_user.id,))
    expected_payments = cur.fetchall()

    # Get payment reminders (due within 2 days)
    cur.execute('''
        SELECT pay.amount, c.name as client_name, pay.due_date, p.title as project_title
        FROM payments pay
        LEFT JOIN projects p ON pay.project_id = p.id
        LEFT JOIN clients c ON p.client_id = c.id
        WHERE pay.user_id = ? AND pay.status = 'pending' AND pay.due_date BETWEEN DATE('now') AND DATE('now', '+2 days')
        ORDER BY pay.due_date
    ''', (current_user.id,))
    payment_reminders = cur.fetchall()

    return render_template('dashboard.html', 
                         active_clients=active_clients, 
                         pending_amount=pending_amount, 
                         upcoming_deadlines=upcoming_deadlines,
                         profession=profession,
                         expected_payments=expected_payments,
                         payment_reminders=payment_reminders)


# -----------------------------------------------------------------------------
# Billing endpoints (Stripe)
# -----------------------------------------------------------------------------
@app.route('/billing')
@login_required
def billing_page():
    # For now reuse settings page as billing dashboard
    return render_template('settings.html')


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    data = request.get_json() or {}
    price_id = data.get('price_id')
    if not price_id:
        return jsonify({'error': 'missing price_id'}), 400
    try:
        session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            success_url=url_for('billing_page', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing_page', _external=True),
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stripe-webhook', methods=['POST'])
@csrf.exempt
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            # Fallback: parse payload without signature (useful for local dev only)
            event = json.loads(payload)
    except Exception:
        return '', 400

    # Handle relevant events
    etype = event.get('type') if isinstance(event, dict) else event['type']

    try:
        if etype == 'checkout.session.completed':
            sess = event['data']['object']
            # Obtain email and customer id
            email = (sess.get('customer_details') or {}).get('email') or sess.get('customer_email')
            customer_id = sess.get('customer')
            if email:
                conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                cur = conn.cursor()
                cur.execute('SELECT id FROM users WHERE email = ?', (email,))
                r = cur.fetchone()
                if r:
                    uid = r[0]
                    cur.execute('UPDATE users SET stripe_customer_id = ?, billing_email = ? WHERE id = ?', (customer_id, email, uid))
                    conn.commit()
                conn.close()

        # subscription updates / invoice events
        if etype and (etype.startswith('customer.subscription') or etype.startswith('invoice') or etype.startswith('subscription')):
            obj = event['data']['object']
            # try to get subscription object
            sub = None
            if obj.get('object') == 'subscription':
                sub = obj
            elif obj.get('subscription'):
                try:
                    sub = stripe.Subscription.retrieve(obj.get('subscription'))
                except Exception:
                    sub = None

            if sub:
                customer = sub.get('customer')
                status = sub.get('status')
                cpe = sub.get('current_period_end')
                cpe_iso = datetime.fromtimestamp(cpe).isoformat() if cpe else None
                try:
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    cur = conn.cursor()
                    cur.execute('SELECT id FROM users WHERE stripe_customer_id = ?', (customer,))
                    r = cur.fetchone()
                    if r:
                        uid = r[0]
                        cur.execute('UPDATE users SET stripe_subscription_id = ?, subscription_status = ?, current_period_end = ? WHERE id = ?', (sub.get('id'), status, cpe_iso, uid))
                        conn.commit()
                    conn.close()
                except Exception:
                    pass
    except Exception:
        # swallow to avoid webhook retries in development; log in production
        pass

    return '', 200


# Clients

@app.route('/clients')
@login_required
def clients():
    try:
        db = get_db()
        cur = db.cursor()
        
        # Get clients with project count for loyalty marking
        cur.execute('''
            SELECT c.id, c.user_id, c.name, c.email, c.contact, c.status, c.last_contact, c.notes,
                   (SELECT COUNT(*) FROM projects p WHERE p.client_id = c.id) as project_count
            FROM clients c 
            WHERE c.user_id = ? AND c.status != 'archived'
            ORDER BY 
                CASE WHEN (SELECT COUNT(*) FROM projects p WHERE p.client_id = c.id) > 2 THEN 0 ELSE 1 END,
                c.status,
                c.last_contact DESC
        ''', (current_user.id,))
        rows = cur.fetchall()
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")
        rows = []

    return render_template('clients.html', clients=rows)


@app.route('/clients/import', methods=['POST'])
@login_required
def clients_import():
    if 'csv_file' not in request.files:
        flash(t('file_not_selected'))
        return redirect('/clients')

    file = request.files['csv_file']
    if file.filename == '':
        flash(t('file_not_selected'))
        return redirect('/clients')

    try:
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content), delimiter=',')

        required_cols = {'name', 'email'}
        if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
            flash(t('csv_missing_columns'))
            return redirect('/clients')

        db = get_db()
        cur = db.cursor()

        cur.execute('SELECT email FROM clients WHERE user_id = ?', (current_user.id,))
        existing_emails = {row[0].lower() for row in cur.fetchall() if row[0]}

        imported_count = 0
        skipped_count = 0

        for row in reader:
            name = (row.get('name') or '').strip()
            email = (row.get('email') or '').strip().lower()
            contact = (row.get('contact') or '').strip()
            status = (row.get('status') or 'active').strip()
            notes = (row.get('notes') or '').strip()

            if not name or not email:
                skipped_count += 1
                continue

            if email in existing_emails:
                skipped_count += 1
                continue

            if status not in ('active', 'cold', 'archived'):
                status = 'active'

            cur.execute('''
                INSERT INTO clients (user_id, name, email, contact, status, last_contact, notes)
                VALUES (?, ?, ?, ?, ?, DATE('now'), ?)
            ''', (current_user.id, name, email, contact, status, notes))

            existing_emails.add(email)
            imported_count += 1

        db.commit()

        if imported_count > 0:
            flash(t('imported_clients', count=imported_count))
        if skipped_count > 0:
            flash(t('skipped_rows', count=skipped_count))

    except (UnicodeDecodeError, csv.Error):
        flash(t('invalid_csv'))
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")

    return redirect('/clients')


@app.route('/clients/add', methods=['GET', 'POST'])
@login_required
def clients_add():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        contact = (request.form.get('contact') or '').strip()
        status = (request.form.get('status') or 'active').strip()
        notes = (request.form.get('notes') or '').strip()

        if not name or not email:
            flash(t('name_email_required'))
            return render_template('clients_add.html')

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash(t('invalid_email'))
            return render_template('clients_add.html')

        if status not in ('active', 'cold', 'archived'):
            status = 'active'

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute('''
                INSERT INTO clients (user_id, name, email, contact, status, last_contact, notes)
                VALUES (?, ?, ?, ?, ?, DATE('now'), ?)
            ''', (current_user.id, name, email, contact, status, notes))
            db.commit()
            flash(t('client_added'))
            return redirect('/clients')
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('clients_add.html')

    return render_template('clients_add.html')


@app.route('/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@login_required
def clients_edit(client_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            SELECT id, user_id, name, email, contact, status, last_contact, notes
            FROM clients WHERE id = ? AND user_id = ?
        ''', (client_id, current_user.id))
        client = cur.fetchone()
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")
        client = None

    if not client:
        abort(404)

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        contact = (request.form.get('contact') or '').strip()
        status = (request.form.get('status') or 'active').strip()
        notes = (request.form.get('notes') or '').strip()

        if not name or not email:
            flash(t('name_email_required'))
            return render_template('clients_edit.html', client=client)

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash(t('invalid_email'))
            return render_template('clients_edit.html', client=client)

        if status not in ('active', 'cold', 'archived'):
            status = 'active'

        try:
            cur.execute('''
                UPDATE clients SET name = ?, email = ?, contact = ?, status = ?, last_contact = DATE('now'), notes = ?
                WHERE id = ? AND user_id = ?
            ''', (name, email, contact, status, notes, client_id, current_user.id))
            db.commit()
            flash(t('client_updated'))
            return redirect('/clients')
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('clients_edit.html', client=client)

    return render_template('clients_edit.html', client=client)


@app.route('/clients/delete/<int:client_id>', methods=['POST'])
@login_required
def clients_delete(client_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('DELETE FROM clients WHERE id = ? AND user_id = ?', (client_id, current_user.id))
        db.commit()
        if cur.rowcount == 0:
            flash(t('client_not_found'))
        else:
            flash(t('client_deleted'))
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")

    return redirect('/clients')


# Projects

def get_user_clients():
    db = get_db()
    cur = db.cursor()
    cur.execute('SELECT id, name FROM clients WHERE user_id = ? ORDER BY name', (current_user.id,))
    return cur.fetchall()


@app.route('/projects')
@login_required
def projects():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            SELECT p.id, p.title, p.status, p.budget, p.deadline, p.description, p.client_id, c.name as client_name
            FROM projects p LEFT JOIN clients c ON p.client_id = c.id
            WHERE p.user_id = ? ORDER BY p.deadline DESC
        ''', (current_user.id,))
        rows = cur.fetchall()
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")
        rows = []

    return render_template('projects.html', projects=rows)


@app.route('/projects/add', methods=['GET', 'POST'])
@login_required
def projects_add():
    clients_list = get_user_clients()

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        client_id = request.form.get('client_id')
        status = (request.form.get('status') or 'discussion').strip()
        budget = request.form.get('budget') or None
        deadline = request.form.get('deadline') or None
        description = (request.form.get('description') or '').strip()
        expect_payment = request.form.get('expect_payment') == 'on'
        payment_due_date = request.form.get('payment_due_date') or None
        payment_amount = request.form.get('payment_amount') or None

        if not title:
            flash(t('title_required'))
            return render_template('projects_add.html', clients=clients_list)

        if client_id:
            try:
                db = get_db()
                cur = db.cursor()
                cur.execute('SELECT id FROM clients WHERE id = ? AND user_id = ?', (client_id, current_user.id))
                if not cur.fetchone():
                    flash(t('select_existing_client'))
                    return render_template('projects_add.html', clients=clients_list)
            except sqlite3.Error as e:
                flash(f"{t('db_error')}: {e}")
                return render_template('projects_add.html', clients=clients_list)

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute('''
                INSERT INTO projects (user_id, client_id, title, status, budget, deadline, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (current_user.id, client_id or None, title, status, float(budget) if budget else None, deadline or None, description))
            
            project_id = cur.lastrowid
            
            # If payment expected, create payment record
            if expect_payment and payment_due_date and payment_amount:
                cur.execute('''
                    INSERT INTO payments (user_id, project_id, amount, status, due_date, comment)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (current_user.id, project_id, float(payment_amount), 'pending', payment_due_date, 'Expected payment for project'))
            
            db.commit()
            flash(t('project_added'))
            return redirect('/projects')
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('projects_add.html', clients=clients_list)

    return render_template('projects_add.html', clients=clients_list)


@app.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def projects_edit(project_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            SELECT id, user_id, client_id, title, status, budget, deadline, description
            FROM projects WHERE id = ? AND user_id = ?
        ''', (project_id, current_user.id))
        proj = cur.fetchone()
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")
        proj = None

    if not proj:
        abort(404)

    clients_list = get_user_clients()

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        client_id = request.form.get('client_id')
        status = (request.form.get('status') or 'discussion').strip()
        budget = request.form.get('budget') or None
        deadline = request.form.get('deadline') or None
        description = (request.form.get('description') or '').strip()

        if not title:
            flash(t('title_required'))
            return render_template('projects_edit.html', project=proj, clients=clients_list)

        if client_id:
            try:
                cur.execute('SELECT id FROM clients WHERE id = ? AND user_id = ?', (client_id, current_user.id))
                if not cur.fetchone():
                    flash(t('select_existing_client'))
                    return render_template('projects_edit.html', project=proj, clients=clients_list)
            except sqlite3.Error as e:
                flash(f"{t('db_error')}: {e}")
                return render_template('projects_edit.html', project=proj, clients=clients_list)

        try:
            cur.execute('''
                UPDATE projects SET client_id = ?, title = ?, status = ?, budget = ?, deadline = ?, description = ?
                WHERE id = ? AND user_id = ?
            ''', (client_id or None, title, status, float(budget) if budget else None, deadline or None, description, project_id, current_user.id))
            db.commit()
            flash(t('project_updated'))
            return redirect('/projects')
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('projects_edit.html', project=proj, clients=clients_list)

    return render_template('projects_edit.html', project=proj, clients=clients_list)


@app.route('/projects/delete/<int:project_id>', methods=['POST'])
@login_required
def projects_delete(project_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('DELETE FROM projects WHERE id = ? AND user_id = ?', (project_id, current_user.id))
        db.commit()
        if cur.rowcount == 0:
            flash(t('project_not_found'))
        else:
            flash(t('project_deleted'))
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")

    return redirect('/projects')


@app.route('/projects/complete/<int:project_id>', methods=['POST'])
@login_required
def projects_complete(project_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            UPDATE projects SET status = 'completed'
            WHERE id = ? AND user_id = ?
        ''', (project_id, current_user.id))
        db.commit()
        if cur.rowcount == 0:
            flash(t('project_not_found'))
        else:
            flash(t('project_completed'))
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")

    return redirect('/projects')


# Payments

def get_user_projects_with_clients():
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT p.id, p.title, c.name as client_name
        FROM projects p LEFT JOIN clients c ON p.client_id = c.id
        WHERE p.user_id = ? ORDER BY p.title
    ''', (current_user.id,))
    return cur.fetchall()


@app.route('/payments')
@login_required
def payments():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            SELECT pay.id, pay.amount, pay.status, pay.due_date, pay.comment,
                   p.title as project_title, c.name as client_name
            FROM payments pay
            LEFT JOIN projects p ON pay.project_id = p.id
            LEFT JOIN clients c ON p.client_id = c.id
            WHERE pay.user_id = ? ORDER BY pay.due_date DESC
        ''', (current_user.id,))
        rows = cur.fetchall()
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")
        rows = []

    return render_template('payments.html', payments=rows)


@app.route('/payments/add', methods=['GET', 'POST'])
@login_required
def payments_add():
    projects_list = get_user_projects_with_clients()

    if request.method == 'POST':
        project_id = request.form.get('project_id')
        amount = request.form.get('amount')
        status = (request.form.get('status') or 'pending').strip()
        due_date = request.form.get('due_date') or None
        comment = (request.form.get('comment') or '').strip()

        if not project_id or not amount:
            flash(t('project_amount_required'))
            return render_template('payments_add.html', projects=projects_list)

        try:
            db = get_db()
            cur = db.cursor()
            cur.execute('SELECT id FROM projects WHERE id = ? AND user_id = ?', (project_id, current_user.id))
            if not cur.fetchone():
                flash(t('select_existing_project'))
                return render_template('payments_add.html', projects=projects_list)
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('payments_add.html', projects=projects_list)

        if status not in ('pending', 'partial', 'paid'):
            status = 'pending'

        try:
            cur.execute('''
                INSERT INTO payments (user_id, project_id, amount, status, due_date, comment)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (current_user.id, project_id, float(amount), status, due_date, comment))
            db.commit()
            flash(t('payment_added'))
            return redirect('/payments')
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('payments_add.html', projects=projects_list)

    return render_template('payments_add.html', projects=projects_list)


@app.route('/payments/delete/<int:payment_id>', methods=['POST'])
@login_required
def payments_delete(payment_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('DELETE FROM payments WHERE id = ? AND user_id = ?', (payment_id, current_user.id))
        db.commit()
        if cur.rowcount == 0:
            flash(t('payment_not_found'))
        else:
            flash(t('payment_deleted'))
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")

    return redirect('/payments')


@app.route('/payments/mark_paid/<int:payment_id>', methods=['POST'])
@login_required
def payments_mark_paid(payment_id):
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            UPDATE payments SET status = 'paid'
            WHERE id = ? AND user_id = ?
        ''', (payment_id, current_user.id))
        db.commit()
        if cur.rowcount == 0:
            flash(t('payment_not_found'))
        else:
            flash(t('payment_marked_paid'))
    except sqlite3.Error as e:
        flash(f"{t('db_error')}: {e}")

    return redirect('/payments')


# Export

@app.route('/export')
@login_required
def export_data():
    db = get_db()
    cur = db.cursor()

    UTF8_BOM = '\ufeff'

    def create_csv(headers, rows):
        output = io.StringIO()
        output.write(UTF8_BOM)
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode('utf-8')

    cur.execute('SELECT name, email, contact, status, last_contact, notes FROM clients WHERE user_id = ? ORDER BY name', (current_user.id,))
    clients_rows = cur.fetchall()
    clients_csv = create_csv([t('client_name'), t('email'), t('contact'), t('status'), t('last_contact'), t('notes')], clients_rows)

    cur.execute('''
        SELECT p.title, c.name, p.status, p.budget, p.deadline, p.description
        FROM projects p LEFT JOIN clients c ON p.client_id = c.id
        WHERE p.user_id = ? ORDER BY p.title
    ''', (current_user.id,))
    projects_rows = cur.fetchall()
    projects_csv = create_csv([t('project_name'), t('client'), t('status'), t('budget'), t('deadline'), t('description')], projects_rows)

    cur.execute('''
        SELECT p.title, pay.amount, pay.status, pay.due_date, pay.comment
        FROM payments pay LEFT JOIN projects p ON pay.project_id = p.id
        WHERE pay.user_id = ? ORDER BY pay.due_date DESC
    ''', (current_user.id,))
    payments_rows = cur.fetchall()
    payments_csv = create_csv([t('project'), t('amount'), t('payment_status'), t('due_date'), t('comment')], payments_rows)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('clients.csv', clients_csv)
        zf.writestr('projects.csv', projects_csv)
        zf.writestr('payments.csv', payments_csv)
    zip_buffer.seek(0)

    response = make_response(zip_buffer.read())
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename=crm_export.zip'
    return response


# Feedback

@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    try:
        data = request.get_json()
        name = data.get('name', current_user.name)
        message = data.get('message', '')
        feedback_type = data.get('type', 'feedback')
        
        if not message.strip():
            return jsonify({'error': 'Message is required'}), 400
        
        # In a real app, you'd save this to a database or send an email
        # For now, we'll just log it
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {feedback_type.upper()} from {name} ({current_user.email}): {message}\n"
        
        # Append to a simple log file
        log_file = os.path.join(BASE_DIR, 'feedback.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Settings

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)


def generate_telegram_code():
    """Generate unique Telegram activation code (OP-XXXXXX format)"""
    import secrets
    allowed_chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # exclude 0/O, 1/I to avoid confusion
    code = 'OP-' + ''.join(secrets.choice(allowed_chars) for _ in range(6))
    return code


@app.route('/api/telegram/generate', methods=['POST'])
@login_required
def generate_telegram_code_api():
    try:
        db = get_db()
        cur = db.cursor()
        
        # Check if user already has a code
        cur.execute('SELECT telegram_code FROM users WHERE id = ?', (current_user.id,))
        existing_code = cur.fetchone()
        
        if existing_code and existing_code[0]:
            return jsonify({'success': False, 'error': 'User already has an activation code'})
        
        # Generate unique code
        while True:
            code = generate_telegram_code()
            cur.execute('SELECT id FROM users WHERE telegram_code = ?', (code,))
            if not cur.fetchone():
                break
        
        # Save code to database
        cur.execute('UPDATE users SET telegram_code = ? WHERE id = ?', (code, current_user.id))
        db.commit()
        
        return jsonify({'success': True, 'code': code})
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/telegram/regenerate', methods=['POST'])
@login_required
def regenerate_telegram_code_api():
    try:
        db = get_db()
        cur = db.cursor()
        
        # Generate new unique code
        while True:
            code = generate_telegram_code()
            cur.execute('SELECT id FROM users WHERE telegram_code = ? AND id != ?', (code, current_user.id))
            if not cur.fetchone():
                break
        
        # Update code in database
        cur.execute('UPDATE users SET telegram_code = ? WHERE id = ?', (code, current_user.id))
        db.commit()
        
        return jsonify({'success': True, 'code': code})
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Onboarding

@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    if request.method == 'POST':
        profession = request.form.get('profession', 'freelancer')
        
        try:
            db = get_db()
            cur = db.cursor()
            cur.execute('UPDATE users SET profession = ? WHERE id = ?', (profession, current_user.id))
            db.commit()
            flash(t('profession_saved'))
            return redirect('/dashboard')
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('onboarding.html')

    return render_template('onboarding.html')


# JSON Export

@app.route('/api/export-json')
@login_required
def export_json():
    """Export all user data as JSON"""
    try:
        db = get_db()
        cur = db.cursor()
        
        # Get clients
        cur.execute('SELECT * FROM clients WHERE user_id = ?', (current_user.id,))
        clients = [dict(row) for row in cur.fetchall()]
        
        # Get projects
        cur.execute('SELECT * FROM projects WHERE user_id = ?', (current_user.id,))
        projects = [dict(row) for row in cur.fetchall()]
        
        # Get payments
        cur.execute('SELECT * FROM payments WHERE user_id = ?', (current_user.id,))
        payments = [dict(row) for row in cur.fetchall()]
        
        # Construct JSON response
        data = {
            'export_date': datetime.now().isoformat(),
            'user': {
                'id': current_user.id,
                'name': current_user.name,
                'email': current_user.email
            },
            'clients': clients,
            'projects': projects,
            'payments': payments
        }
        
        response = make_response(jsonify(data))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=opusio_data.json'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Delete Account

@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Permanently delete user account and all data"""
    try:
        data = request.get_json()
        confirmation = data.get('confirmation', '')
        
        if confirmation != 'DELETE':
            return jsonify({'success': False, 'error': 'Invalid confirmation'}), 400
        
        db = get_db()
        cur = db.cursor()
        user_id = current_user.id
        
        # Delete all user data (foreign keys ON DELETE CASCADE should handle this)
        # But let's be explicit for safety
        cur.execute('DELETE FROM payments WHERE user_id = ?', (user_id,))
        cur.execute('DELETE FROM projects WHERE user_id = ?', (user_id,))
        cur.execute('DELETE FROM clients WHERE user_id = ?', (user_id,))
        cur.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        db.commit()
        
        # Log out the user
        logout_user()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Admin

def requires_admin(f):
    """Decorator to require admin role"""
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            cur.execute('SELECT is_admin FROM users WHERE id = ?', (current_user.id,))
            row = cur.fetchone()
            conn.close()
            if not row or not row[0]:
                abort(403)
        except Exception:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def update_user_session():
    """Update or create user session when user is active"""
    if current_user.is_authenticated:
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            cur = conn.cursor()
            ip = request.remote_addr or 'unknown'
            user_agent = request.headers.get('User-Agent', 'unknown')[:255]
            
            cur.execute(
                'INSERT OR REPLACE INTO user_session (user_id, session_id, ip_address, user_agent, last_activity) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
                (current_user.id, session.get('session_id', secrets.token_hex(16)), ip, user_agent)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            pass  # Silently fail


@app.before_request
def before_request():
    """Called before each request - update user session"""
    update_user_session()


@app.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit feedback from user"""
    try:
        data = request.get_json()
        if not data or 'message' not in data or len(data['message'].strip()) < 3:
            return jsonify({'success': False, 'error': 'Message too short'}), 400
        
        message = data['message'][:1000]  # Limit to 1000 chars
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO feedback (user_id, message, status) VALUES (?, ?, ?)',
            (current_user.id, message, 'new')
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Feedback sent successfully'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin', methods=['GET'])
@login_required
@requires_admin
def admin_panel():
    """Admin panel - main page with statistics"""
    try:
        period = request.args.get('period', '30m')  # 30m, 1h, all
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        
        # Get stats
        cur.execute('SELECT COUNT(*) FROM users')
        total_users = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM feedback WHERE status = ?', ('new',))
        new_feedback = cur.fetchone()[0]
        
        # Get recent feedback
        cur.execute('''
            SELECT f.id, f.user_id, u.name, u.email, f.message, f.created_at 
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            ORDER BY f.created_at DESC
            LIMIT 10
        ''')
        recent_feedback = cur.fetchall()
        
        # Get online users based on time period
        if period == '1h':
            time_filter = "datetime('now', '-1 hour')"
        elif period == 'all':
            time_filter = "datetime('now', '-999 days')"  # Essentially all time
        else:  # 30m
            time_filter = "datetime('now', '-30 minutes')"
        
        cur.execute(f'''
            SELECT u.id, u.name, u.email, us.last_activity, us.ip_address
            FROM user_session us
            JOIN users u ON us.user_id = u.id
            WHERE datetime(us.last_activity) > {time_filter}
            ORDER BY us.last_activity DESC
        ''')
        online_users_list = cur.fetchall()
        
        # Additional admin metrics
        try:
            cur.execute('SELECT COUNT(DISTINCT user_id) FROM clients')
            users_with_clients = cur.fetchone()[0] or 0

            cur.execute('SELECT COUNT(*) FROM export_logs')
            exports_count = cur.fetchone()[0] or 0

            cur.execute("SELECT AVG(c) FROM (SELECT COUNT(*) AS c FROM clients GROUP BY user_id)")
            avg_clients = cur.fetchone()[0] or 0

            # Read last 20 lines from error.log (project root)
            logs_preview = []
            log_path = os.path.join(BASE_DIR, 'error.log')
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
                        lines = [l.strip() for l in lf.readlines() if l.strip()]
                    tail = lines[-20:]
                    for ln in tail[::-1]:
                        # Try to extract timestamp and URL naively
                        time_match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ln)
                        url_match = re.search(r"(GET|POST|PUT|DELETE) (\/[^\s\"]+)", ln)
                        ts = time_match.group(0) if time_match else ''
                        url = url_match.group(2) if url_match else '-'
                        msg = (ln[:80] + '...') if len(ln) > 80 else ln
                        logs_preview.append((ts, url, msg))
                except Exception:
                    logs_preview = []
            else:
                logs_preview = []

            # Maintenance flag
            cur.execute("SELECT value FROM system_settings WHERE key = 'maintenance_mode'")
            row = cur.fetchone()
            maintenance_mode = row[0] if row else 'off'
        except Exception:
            users_with_clients = 0
            exports_count = 0
            avg_clients = 0
            logs_preview = []
            maintenance_mode = 'off'

        conn.close()
        
        # Render template with additional admin helpers
        return render_template('admin/dashboard.html',
            total_users=total_users,
            online_users=len(online_users_list),
            new_feedback=new_feedback,
            recent_feedback=recent_feedback,
            online_users_list=online_users_list,
            period=period,
            last_update=datetime.now().strftime('%H:%M:%S'),
            users_with_clients=users_with_clients,
            exports_count=exports_count,
            avg_clients_per_account=round(avg_clients,2) if avg_clients else 0,
            logs_preview=logs_preview,
            maintenance_mode=(maintenance_mode or 'off')
        )
    except Exception as e:
        flash(f'Error loading admin panel: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/api/admin/announcement', methods=['POST'])
@login_required
@requires_admin
def send_announcement():
    """Send announcement to all users"""
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        message = data.get('message', '').strip()
        
        if not title or not message:
            return jsonify({'success': False, 'error': 'Title and message required'}), 400
        
        # Limit lengths
        title = title[:100]
        message = message[:1000]
        
        # Save to database
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO announcements (title, message, admin_id) VALUES (?, ?, ?)',
            (title, message, current_user.id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Announcement sent to all users!'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/replies', methods=['GET'])
@login_required
def get_user_replies():
    """Get new replies to user's feedback"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        
        # Get feedback with admin replies
        cur.execute('''
            SELECT id, message, admin_reply, replied_at
            FROM feedback
            WHERE user_id = ? AND admin_reply IS NOT NULL
            ORDER BY replied_at DESC
            LIMIT 5
        ''', (current_user.id,))
        replies = cur.fetchall()
        conn.close()
        
        return jsonify({'success': True, 'replies': replies}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    """Get active announcements"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        
        # Get announcements that haven't expired (or never expire)
        cur.execute('''
            SELECT id, title, message, created_at
            FROM announcements
            WHERE expires_at IS NULL OR datetime(expires_at) > datetime('now')
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        announcement = cur.fetchone()
        conn.close()
        
        if announcement:
            return jsonify({'success': True, 'announcement': announcement}), 200
        else:
            return jsonify({'success': True, 'announcement': None}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ------------------------
# Admin helper endpoints
# ------------------------

@app.route('/api/admin/logs', methods=['GET'])
@login_required
@requires_admin
def admin_logs():
    """Return last 20 lines from error.log (parsed)"""
    try:
        log_path = os.path.join(BASE_DIR, 'error.log')
        if not os.path.exists(log_path):
            return jsonify({'success': True, 'logs': []}), 200
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
            lines = [l.strip() for l in lf.readlines() if l.strip()]
        tail = lines[-20:][::-1]
        parsed = []
        for ln in tail:
            time_match = re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ln)
            url_match = re.search(r"(GET|POST|PUT|DELETE) (\/[^\s\"]+)", ln)
            ts = time_match.group(0) if time_match else ''
            url = url_match.group(2) if url_match else '-'
            msg = (ln[:80] + '...') if len(ln) > 80 else ln
            parsed.append({'time': ts, 'url': url, 'message': msg})
        return jsonify({'success': True, 'logs': parsed}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/logs/download', methods=['GET'])
@login_required
@requires_admin
def download_logs():
    log_path = os.path.join(BASE_DIR, 'error.log')
    if not os.path.exists(log_path):
        flash('No error log found', 'error')
        return redirect(url_for('admin_panel'))
    return send_file(log_path, as_attachment=True)


@app.route('/api/admin/export_user', methods=['POST'])
@login_required
@requires_admin
def admin_export_user():
    """Export user data (clients, projects, payments, user record)"""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({'success': False, 'error': 'Email required'}), 400
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('SELECT id, name, email, created_at, subscription_status FROM users WHERE lower(email) = ?', (email,))
        user = cur.fetchone()
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        user_id = user[0]
        cur.execute('SELECT id, name, email, contact, status, last_contact, notes FROM clients WHERE user_id = ?', (user_id,))
        clients = [dict(zip(["id","name","email","contact","status","last_contact","notes"], row)) for row in cur.fetchall()]
        cur.execute('SELECT id, client_id, title, status, budget, deadline, description FROM projects WHERE user_id = ?', (user_id,))
        projects = [dict(zip(["id","client_id","title","status","budget","deadline","description"], row)) for row in cur.fetchall()]
        cur.execute('SELECT id, project_id, amount, status, due_date, comment FROM payments WHERE user_id = ?', (user_id,))
        payments = [dict(zip(["id","project_id","amount","status","due_date","comment"], row)) for row in cur.fetchall()]

        payload = {
            'user': {'id': user[0], 'name': user[1], 'email': user[2], 'created_at': user[3], 'subscription_status': user[4]},
            'clients': clients,
            'projects': projects,
            'payments': payments,
            'exported_at': datetime.utcnow().isoformat() + 'Z'
        }

        # Log export
        try:
            cur.execute('INSERT INTO export_logs (admin_id, user_id, email, details) VALUES (?, ?, ?, ?)',
                        (current_user.id, user_id, email, json.dumps({'clients': len(clients), 'projects': len(projects)})))
            conn.commit()
        except Exception:
            pass
        conn.close()

        return jsonify({'success': True, 'data': payload}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/find_user', methods=['GET'])
@login_required
@requires_admin
def admin_find_user():
    email = (request.args.get('email') or '').strip().lower()
    if not email:
        return jsonify({'success': False, 'error': 'Email required'}), 400
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('SELECT id, name, email, created_at, subscription_status FROM users WHERE lower(email) = ?', (email,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found'}), 404
        user_id = row[0]
        cur.execute('SELECT COUNT(*) FROM clients WHERE user_id = ?', (user_id,))
        client_count = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM export_logs WHERE user_id = ?', (user_id,))
        exported = cur.fetchone()[0]
        conn.close()
        return jsonify({'success': True, 'user': {'id': row[0], 'name': row[1], 'email': row[2], 'created_at': row[3], 'subscription_status': row[4], 'client_count': client_count, 'exports': exported}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/impersonate', methods=['POST'])
@login_required
@requires_admin
def admin_impersonate():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'user_id required'}), 400
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('SELECT id, name, email, telegram_code FROM users WHERE id = ?', (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        # remember admin id to allow returning
        session['original_admin_id'] = current_user.id
        user_obj = User(row[0], row[1], row[2], row[3])
        login_user(user_obj)
        return jsonify({'success': True, 'redirect': url_for('dashboard')}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/stop_impersonation', methods=['GET'])
def admin_stop_impersonation():
    orig = session.pop('original_admin_id', None)
    if not orig:
        flash('No impersonation active', 'error')
        return redirect(url_for('dashboard'))
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('SELECT id, name, email, telegram_code FROM users WHERE id = ?', (orig,))
        row = cur.fetchone()
        conn.close()
        if row:
            admin_user = User(row[0], row[1], row[2], row[3])
            login_user(admin_user)
            flash('Returned to admin account', 'success')
            return redirect(url_for('admin_panel'))
    except Exception:
        pass
    flash('Could not return to admin account', 'error')
    return redirect(url_for('login'))


@app.route('/api/admin/maintenance', methods=['POST'])
@login_required
@requires_admin
def admin_set_maintenance():
    try:
        data = request.get_json() or {}
        enabled = bool(data.get('enabled'))
        message = (data.get('message') or '').strip()
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('maintenance_mode', ?)", ('on' if enabled else 'off',))
        cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('maintenance_message', ?)", (message,))
        cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('service_status', ?)", ('maintenance' if enabled else 'green',))
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system_status', methods=['GET'])
def api_system_status():
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_settings WHERE key = 'maintenance_mode'")
        row = cur.fetchone()
        maintenance_mode = row[0] if row else 'off'
        cur.execute("SELECT value FROM system_settings WHERE key = 'maintenance_message'")
        row2 = cur.fetchone()
        maintenance_message = row2[0] if row2 else ''
        cur.execute("SELECT value FROM system_settings WHERE key = 'service_status'")
        row3 = cur.fetchone()
        service_status = row3[0] if row3 else 'green'
        conn.close()
        return jsonify({'success': True, 'maintenance_mode': maintenance_mode, 'maintenance_message': maintenance_message, 'service_status': service_status}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/feedback', methods=['GET'])
@login_required
@requires_admin
def admin_feedback_list():
    """View all feedback with status filtering"""
    try:
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        per_page = 20
        offset = (page - 1) * per_page
        
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        
        # Get counts for all statuses
        cur.execute('SELECT COUNT(*) FROM feedback')
        total_feedback = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM feedback WHERE status = ?', ('new',))
        new_feedback = cur.fetchone()[0]
        
        cur.execute('SELECT COUNT(*) FROM feedback WHERE status = ?', ('replied',))
        replied_feedback = cur.fetchone()[0]
        
        # Get feedback list with pagination
        if status == 'all':
            cur.execute('''
                SELECT f.id, f.user_id, u.name, u.email, f.message, f.status, f.created_at
                FROM feedback f
                JOIN users u ON f.user_id = u.id
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            cur.execute('SELECT COUNT(*) FROM feedback')
        else:
            cur.execute('''
                SELECT f.id, f.user_id, u.name, u.email, f.message, f.status, f.created_at
                FROM feedback f
                JOIN users u ON f.user_id = u.id
                WHERE f.status = ?
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
            ''', (status, per_page, offset))
            cur.execute('SELECT COUNT(*) FROM feedback WHERE status = ?', (status,))
        
        feedback_list = cur.fetchall()
        total = cur.fetchone()[0]
        conn.close()
        
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('admin/feedback_list.html',
            feedback_list=feedback_list,
            status=status,
            page=page,
            total_pages=total_pages,
            total_feedback=total_feedback,
            new_feedback=new_feedback,
            replied_feedback=replied_feedback
        )
    except Exception as e:
        flash(f'Error loading feedback: {str(e)}', 'error')
        return redirect(url_for('admin'))


@app.route('/admin/feedback/<int:feedback_id>', methods=['GET', 'POST'])
@login_required
@requires_admin
def admin_feedback_detail(feedback_id):
    """View feedback detail and send reply"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        
        if request.method == 'POST':
            reply = request.form.get('reply', '').strip()
            if not reply or len(reply) < 2:
                flash('Reply must be at least 2 characters', 'error')
                return redirect(url_for('admin_feedback_detail', feedback_id=feedback_id))
            
            reply = reply[:5000]  # Limit to 5000 chars
            cur.execute(
                'UPDATE feedback SET admin_reply = ?, status = ?, replied_at = CURRENT_TIMESTAMP WHERE id = ?',
                (reply, 'replied', feedback_id)
            )
            conn.commit()
            flash('Reply sent successfully!', 'success')
            return redirect(url_for('admin_feedback_detail', feedback_id=feedback_id))
        
        # GET - show feedback detail
        cur.execute('''
            SELECT f.id, f.user_id, u.name, u.email, f.message, f.status, f.created_at, f.admin_reply, f.replied_at
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            WHERE f.id = ?
        ''', (feedback_id,))
        
        feedback = cur.fetchone()
        conn.close()
        
        if not feedback:
            abort(404)
        
        return render_template('admin/feedback_detail.html',
            feedback_id=feedback[0],
            user_id=feedback[1],
            user_name=feedback[2],
            user_email=feedback[3],
            message=feedback[4],
            status=feedback[5],
            created_at=feedback[6],
            admin_reply=feedback[7],
            replied_at=feedback[8]
        )
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin_feedback_list'))


# Main

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
