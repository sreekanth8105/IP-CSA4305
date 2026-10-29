# AeroVista — Flight Reservation System

A Flask + SQLite college-lab project with a custom aviation-inspired navy, cyan and amber interface (not the previous airline template).

## Features
- Customer registration, login, profile and demo password reset
- Search sample flights by origin, destination and date
- Economy, Premium Economy, Business and First Class fares and seat inventory
- Passenger details, demo payment selection, booking confirmation and unique booking code
- Booking status lookup, booking history, cancellation/refund estimate and printable ticket
- Customer feedback form
- Admin dashboard for flights, cabin inventory, fares, users, bookings, refund rules and CSV reports
- Responsive layout for desktop and mobile

## Run on macOS
```bash
cd FlightReservationSystem
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

Demo admin: `admin@aerovista.demo` / `Admin123!`

## Important demo limitations
This is a student prototype. Flights, seat inventory and fares are sample data; availability is only real-time within this local database, not a live airline/GDS connection. Payment is simulated, password reset does not send email, and tickets are not valid for travel. Change the secret key and admin credentials before any deployment.
