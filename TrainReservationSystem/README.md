# Trackline Train Reservation System — Lab Project

## Run on macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo admin
Email: admin@railway.com
Password: Admin123!

The first run creates `railway.db` with sample train services, classes/fare records and refund rules.

## Included
- Passenger registration/login, profile and password change
- Search train by origin, destination and journey date
- Train detail, class-wise fare and availability
- Passenger details and booking for up to 6 people
- Unique PNR, PNR lookup, ticket view and print/save as PDF
- Reservation history and cancellation
- Admin train schedule, class capacity/fares, user and booking management
- Configurable sample refund rules, refund status record and CSV reports

## Lab demo limitations
Payments are simulated, no real funds are processed, and no confirmation emails are sent. Refund percentages are sample lab rules, not official railway policy. PNR statuses are CONFIRMED/CANCELLED; RAC and waiting-list allocation are not implemented. This is not connected to IRCTC or Indian Railways; tickets are not valid for travel. Add CSRF protection, rate limiting, secret management and proper transaction controls before any production use.
