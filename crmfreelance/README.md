# Freelance CRM

A lightweight CRM system for freelancers built with Flask and SQLite.

## Features

- **Client Management** — Add, edit, delete clients with status tracking
- **Project Management** — Track projects with budgets and deadlines
- **Payment Tracking** — Monitor payment status (pending/partial/paid)
- **Dashboard** — Overview of active clients, pending payments, upcoming deadlines
- **CSV Import** — Bulk import clients from CSV files
- **Data Export** — Export all data as ZIP archive with CSV files
- **Multi-language** — English and Russian interface (switchable)

## Tech Stack

- Python 3.x
- Flask + Flask-Login
- SQLite
- bcrypt (password hashing)
- Jinja2 templates

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Open http://127.0.0.1:5000/ in your browser.

## Routes

| Route | Description |
|-------|-------------|
| `/register` | User registration |
| `/login` | User login |
| `/dashboard` | Main dashboard |
| `/clients` | Client list |
| `/clients/add` | Add new client |
| `/clients/edit/<id>` | Edit client |
| `/clients/import` | Import clients from CSV |
| `/projects` | Project list |
| `/projects/add` | Add new project |
| `/projects/edit/<id>` | Edit project |
| `/payments` | Payment list |
| `/payments/add` | Add new payment |
| `/export` | Download data as ZIP |
| `/lang/en` | Switch to English |
| `/lang/ru` | Switch to Russian |

## Project Structure

```
├── app.py              # Main application
├── translations.py     # i18n translations (EN/RU)
├── requirements.txt    # Python dependencies
├── render.yaml         # Render.com deployment config
├── crm.db             # SQLite database (auto-created)
└── templates/
    ├── base.html       # Base template with navigation
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── clients.html
    ├── clients_add.html
    ├── clients_edit.html
    ├── projects.html
    ├── projects_add.html
    ├── projects_edit.html
    ├── payments.html
    └── payments_add.html
```

## Database Schema

```sql
-- Users
users (id, name, email, password_hash)

-- Clients  
clients (id, user_id, name, email, contact, status, last_contact, notes)

-- Projects
projects (id, user_id, client_id, title, status, budget, deadline, description)

-- Payments
payments (id, user_id, project_id, amount, status, due_date, comment)
```

## CSV Import Format

```csv
name,email,contact,status,notes
John Doe,john@example.com,+1234567890,active,Important client
Jane Smith,jane@example.com,,cold,
```

## Deployment

### Render.com

1. Push to GitHub
2. Connect repository on [Render.com](https://render.com)
3. Render will auto-detect `render.yaml`
4. Deploy

**Note:** SQLite uses ephemeral storage on Render. For production, consider PostgreSQL.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CRM_SECRET_KEY` | Flask secret key | `change-me-please` |
| `PORT` | Server port | `5000` |

## License

MIT
