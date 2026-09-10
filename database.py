import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'electricity_system.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Customers Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_code TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        national_id TEXT,
        customer_type TEXT CHECK(customer_type IN ('Residential', 'Commercial', 'Industrial')) DEFAULT 'Residential',
        address TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Meters Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Meters (
        meter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        meter_number TEXT UNIQUE NOT NULL,
        transformer_pole_id TEXT NOT NULL,
        phase_type TEXT DEFAULT '1-Phase (220V)',
        installation_date DATE NOT NULL,
        status TEXT CHECK(status IN ('Active', 'Suspended', 'Closed')) DEFAULT 'Active',
        FOREIGN KEY (customer_id) REFERENCES Customers(customer_id) ON DELETE CASCADE
    )
    ''')

    # 3. Tariff Tiers Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS TariffTiers (
        tier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_type TEXT NOT NULL,
        tier_name TEXT NOT NULL,
        min_kwh REAL NOT NULL,
        max_kwh REAL, -- NULL means unlimited (> min_kwh)
        rate_khr REAL NOT NULL,
        fixed_maintenance_khr REAL DEFAULT 2000,
        vat_percent REAL DEFAULT 10
    )
    ''')

    # 4. Meter Readings Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MeterReadings (
        reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
        meter_id INTEGER NOT NULL,
        reading_date DATE NOT NULL,
        billing_month TEXT NOT NULL, -- e.g. '2026-08'
        previous_reading REAL NOT NULL,
        current_reading REAL NOT NULL,
        units_consumed REAL NOT NULL,
        reader_name TEXT NOT NULL,
        is_spike_confirmed INTEGER DEFAULT 0,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (meter_id) REFERENCES Meters(meter_id) ON DELETE CASCADE
    )
    ''')

    # 5. Invoices Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        reading_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        billing_month TEXT NOT NULL,
        issue_date DATE NOT NULL,
        due_date DATE NOT NULL,
        units_consumed REAL NOT NULL,
        energy_amount_khr REAL NOT NULL,
        maintenance_fee_khr REAL NOT NULL,
        tax_amount_khr REAL NOT NULL,
        total_amount_khr REAL NOT NULL,
        total_amount_usd REAL NOT NULL,
        payment_status TEXT CHECK(payment_status IN ('Unpaid', 'Paid', 'Overdue')) DEFAULT 'Unpaid',
        khqr_data TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reading_id) REFERENCES MeterReadings(reading_id) ON DELETE CASCADE,
        FOREIGN KEY (customer_id) REFERENCES Customers(customer_id) ON DELETE CASCADE
    )
    ''')

    # 6. Invoice Details (Tier Breakdown)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS InvoiceDetails (
        detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        tier_name TEXT NOT NULL,
        kwh_in_tier REAL NOT NULL,
        rate_khr REAL NOT NULL,
        subtotal_khr REAL NOT NULL,
        FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id) ON DELETE CASCADE
    )
    ''')

    # 7. Payments Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_number TEXT UNIQUE NOT NULL,
        invoice_id INTEGER NOT NULL,
        amount_paid_khr REAL NOT NULL,
        payment_method TEXT CHECK(payment_method IN ('KHQR', 'Cash', 'Bank Transfer')) NOT NULL,
        payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        received_by TEXT NOT NULL,
        reference_no TEXT,
        notes TEXT,
        FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id) ON DELETE CASCADE
    )
    ''')

    # 8. Users Table for Authentication and Approval
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone_number TEXT,
        role TEXT CHECK(role IN ('Admin', 'Staff')) DEFAULT 'Staff',
        status TEXT CHECK(status IN ('Pending', 'Approved', 'Rejected')) DEFAULT 'Pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_at DATETIME,
        approved_by TEXT
    )
    ''')

    # Seed default ADMIN user (ADMIN / 12345@) if not exists
    admin_user = cursor.execute("SELECT * FROM Users WHERE UPPER(username) = 'ADMIN'").fetchone()
    if not admin_user:
        try:
            from werkzeug.security import generate_password_hash
            hashed_pwd = generate_password_hash('12345@')
        except Exception:
            hashed_pwd = '12345@'
        cursor.execute('''
            INSERT INTO Users (username, password_hash, full_name, email, phone_number, role, status, approved_at, approved_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'System')
        ''', (
            'ADMIN',
            hashed_pwd,
            'អភិបាលប្រព័ន្ធ (System Admin)',
            'admin@edc.com.kh',
            '012 999 888',
            'Admin',
            'Approved'
        ))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
