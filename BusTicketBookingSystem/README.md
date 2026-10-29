# BusWay — Online Bus Ticket Booking System

## Run on macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo admin
Email: `admin@bus.com`
Password: `Admin123!`

The app creates `bus.db` and demo buses on first startup. Demo trips are dated for the day the database is first created; use the admin panel to add buses for other dates.

## Implemented lab modules
- Customer registration/login, password change and profile
- Bus search by source, destination and date
- Volvo, Sleeper, Coach and AC Seater categories
- Seat selection and passenger details
- Booking confirmation, history and cancellation
- Bus comments and admin comment moderation
- Admin bus/category/user/news management
- Booking/revenue reports with CSV export

## Important
- Payment is simulated; no real payments are processed.
- No real confirmation emails are sent by default.
- This is a student demo, not a production ticketing service. Before deployment add CSRF protection, rate limiting, email reset/verification, secure secret configuration, database backups and real payment/email integrations.
