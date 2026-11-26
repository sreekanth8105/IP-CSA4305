# Buy a Cake — Online Cake Ordering System

A responsive, end-to-end coursework web app built with **Python Flask, SQLite, HTML, and CSS**. Customers can browse and filter cakes, register/login, customize size and cake messages, manage a cart, place an order with delivery details, select a demo payment method, and track order status. Admins can manage cake visibility, add cakes, view orders, and update fulfilment status.

## Features

- Responsive storefront with cake photos, descriptions, category/flavor/occasion filters, search, and price filter.
- Customer registration and login with hashed passwords.
- Cake detail page with size, quantity, and personal message options.
- Shopping cart with size-aware price calculations and item removal.
- Checkout form with delivery address, phone, postal code, delivery date, and payment choice.
- Order confirmation page and customer order history/status tracking.
- Admin dashboard with sales/order counts, cake catalogue management, and order status controls.
- SQLite database is created and seeded automatically on first run.

## Run on macOS / Linux

1. Install Python 3.10 or later.
2. Unzip the project and open Terminal in the `buy_a_cake` folder.
3. Run:
   ```bash
   chmod +x run_mac_linux.sh
   ./run_mac_linux.sh
   ```
4. Open **http://127.0.0.1:5000**.

Manual alternative:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Run on Windows

Double-click `run_windows.bat`, or open Command Prompt in this folder and run it. Then visit **http://127.0.0.1:5000**.

## Admin demo login

- Email: `admin@buyacake.com`
- Password: `Admin123!`

Register a regular customer account from the website to test the customer flow. The admin account is seeded automatically when the database is first initialized.

## Important demo limitations

- The online payment option is **simulated**. No card details are collected and no real payment is processed. A real deployment needs a payment provider such as Razorpay/Stripe and verified server-side payment callbacks.
- Email confirmation is represented by the order confirmation screen. To send real emails, configure an SMTP/email service.
- Cake images use remote image URLs, so those images require an internet connection. You can replace image URLs from the admin catalogue form.
- Before deployment, set a strong `SECRET_KEY`, disable Flask debug mode, use HTTPS, add CSRF protection and rate limiting, validate delivery areas, and configure production database/email/payment services.
- This is an educational project, not a production-ready commerce platform.

## Project structure

```text
buy_a_cake/
├── app.py
├── requirements.txt
├── README.md
├── run_mac_linux.sh
├── run_windows.bat
├── cake_store.db       # created automatically on first run
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── home.html
    ├── cake_detail.html
    ├── auth.html
    ├── cart.html
    ├── checkout.html
    ├── order_confirmation.html
    ├── my_orders.html
    ├── admin.html
    ├── admin_cakes.html
    ├── admin_orders.html
    └── error.html
```
