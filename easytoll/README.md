# EasyToll — Digital Toll Operations

A polished Flask + SQLite web application for the web-development practical. This version includes a responsive dashboard, dedicated HTML templates, a project-specific visual theme, record creation/editing/deletion, search and status filtering, CSV export, validation, flash messages, and a demo sign-in screen.

## Run it

**macOS / Linux:** open Terminal in this folder and run `bash run_mac_linux.sh`.

**Windows:** double-click `run_windows.bat`.

Or run manually:
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo credentials
- Username: `admin`
- Password: `admin123`

Set `DEMO_USERNAME`, `DEMO_PASSWORD`, and `SECRET_KEY` environment variables to override the demo credentials and session key.

## Project structure
- `app.py` — Flask routes, validation, database access, CSV export
- `config.json` — app-specific fields, choices, theme, and sample data
- `templates/base.html` — shared layout and navigation
- `templates/dashboard.html` — overview and recent activity
- `templates/records.html` — searchable/filterable record table
- `templates/form.html` — create/edit form
- `templates/login.html` — sign-in screen
- `static/style.css` — responsive styles and this project's unique theme
- `static/app.js` — small usability enhancements
- `workspace.db` — created automatically on first run

## Notes
This is a classroom/demo application, not a production system. It does not integrate real payment gateways, SMS/OTP, healthcare systems, identity verification, mapping, or legally valid elections. Do not enter sensitive real-world data. Before deployment, add CSRF protection, stronger authentication/password hashing, role-based access, secure secret management, backups, and production hosting settings. The database file is local to this folder.
