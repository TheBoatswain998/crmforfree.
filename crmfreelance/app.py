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
from datetime import datetime
from flask import Flask, g, request, render_template, flash, redirect, url_for, abort, make_response, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from translations import TRANSLATIONS, get_text

app = Flask(__name__)
app.secret_key = os.environ.get('CRM_SECRET_KEY', 'change-me-please')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'crm.db')


# =============================================================================
# User Model
# =============================================================================

class User(UserMixin):
    def __init__(self, id_, name, email):
        self.id = id_
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('SELECT id, name, email FROM users WHERE id = ?', (user_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            return User(row[0], row[1], row[2])
    except sqlite3.Error:
        return None
    return None


# =============================================================================
# Database
# =============================================================================

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


def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('PRAGMA foreign_keys = ON')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
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

    try:
        c.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'free'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()


# =============================================================================
# Internationalization
# =============================================================================

def get_lang():
    return session.get('lang', 'en')


def t(key, **kwargs):
    return get_text(key, get_lang(), **kwargs)


@app.context_processor
def inject_translations():
    return {'t': t, 'lang': get_lang()}


@app.route('/lang/<lang_code>')
def set_language(lang_code):
    if lang_code in ('en', 'ru'):
        session['lang'] = lang_code
    return redirect(request.referrer or '/')


# =============================================================================
# Authentication Routes
# =============================================================================

@app.route('/')
def index():
    return t('crm_ready')


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
            cur.execute('SELECT id, name, email, password_hash FROM users WHERE email = ?', (email,))
            row = cur.fetchone()
        except sqlite3.Error as e:
            flash(f"{t('db_error')}: {e}")
            return render_template('login.html')

        if not row:
            flash(t('invalid_credentials'))
            return render_template('login.html')

        user_id, name, email_db, pw_hash_str = row[0], row[1], row[2], row[3]

        try:
            pw_ok = bcrypt.checkpw(password.encode('utf-8'), pw_hash_str.encode('utf-8'))
        except Exception:
            pw_ok = False

        if not pw_ok:
            flash(t('invalid_credentials'))
            return render_template('login.html')

        user = User(user_id, name, email_db)
        login_user(user)
        return redirect('/dashboard')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash(t('logged_out'))
    return redirect('/')


# =============================================================================
# Dashboard
# =============================================================================

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

    return render_template('dashboard.html', active_clients=active_clients, pending_amount=pending_amount, upcoming_deadlines=upcoming_deadlines)


# =============================================================================
# Clients
# =============================================================================

@app.route('/clients')
@login_required
def clients():
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute('''
            SELECT id, user_id, name, email, contact, status, last_contact, notes
            FROM clients WHERE user_id = ? ORDER BY last_contact DESC
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


# =============================================================================
# Projects
# =============================================================================

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


# =============================================================================
# Payments
# =============================================================================

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


# =============================================================================
# Export
# =============================================================================

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


# =============================================================================
# Feedback / Support
# =============================================================================

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


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
