import os
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db
from tariff_engine import calculate_bill, detect_spike_and_validate, USD_EXCHANGE_RATE
from khqr_service import generate_bakong_khqr_payload, generate_qr_base64

app = Flask(__name__)
app.secret_key = 'electric_billing_cambodia_secure_key_2026'

def verify_password(stored_hash, provided_password):
    if not stored_hash:
        return False
    if stored_hash == provided_password:
        return True
    try:
        return check_password_hash(stored_hash, provided_password)
    except Exception:
        return False

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'Admin':
            flash("ទំព័រនេះសម្រាប់តែអ្នកគ្រប់គ្រង (Admin) ប៉ុណ្ណោះ!", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def require_login():
    # Public endpoints accessible without logging in
    public_endpoints = ['login', 'register', 'static']
    if request.endpoint and request.endpoint not in public_endpoints:
        if 'user_id' not in session:
            flash("សូមចូលប្រើប្រាស់គណនីរបស់អ្នកជាមុនសិន (Please Login)!", "warning")
            return redirect(url_for('login'))

# Custom Jinja filters
@app.template_filter('khr')
def khr_filter(value):
    try:
        return f"{int(round(float(value))):,} ៛"
    except (ValueError, TypeError):
        return f"{value} ៛"

@app.template_filter('usd')
def usd_filter(value):
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return f"${value}"

@app.template_filter('kh_date')
def kh_date_filter(val):
    if not val:
        return ""
    try:
        dt = datetime.strptime(str(val)[:10], '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return str(val)

@app.context_processor
def inject_global_data():
    conn = get_db_connection()
    active_meters = conn.execute('''
        SELECT m.meter_id, m.meter_number, c.customer_code, c.full_name, c.customer_type,
               COALESCE((SELECT current_reading FROM MeterReadings WHERE meter_id = m.meter_id ORDER BY reading_date DESC LIMIT 1), 0.0) as last_reading
        FROM Meters m
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE m.status = 'Active'
        ORDER BY c.full_name ASC
    ''').fetchall()
    
    pending_count = 0
    if session.get('role') == 'Admin':
        try:
            pending_row = conn.execute("SELECT COUNT(*) as c FROM Users WHERE status = 'Pending'").fetchone()
            if pending_row:
                pending_count = pending_row['c']
        except Exception:
            pending_count = 0

    conn.close()
    return {
        'active_meters': active_meters,
        'today': date.today().strftime('%Y-%m-%d'),
        'pending_approvals_count': pending_count
    }

# Helper function to get dashboard analytics
def get_dashboard_metrics():
    conn = get_db_connection()
    
    total_customers = conn.execute("SELECT COUNT(*) as c FROM Customers").fetchone()['c']
    total_meters = conn.execute("SELECT COUNT(*) as c FROM Meters WHERE status = 'Active'").fetchone()['c']
    
    # Month stats
    current_month = datetime.now().strftime('%Y-%m')
    current_month_kwh = conn.execute(
        "SELECT COALESCE(SUM(units_consumed), 0) as total FROM MeterReadings WHERE billing_month = ?",
        (current_month,)
    ).fetchone()['total']
    
    if current_month_kwh == 0:
        # Fallback to August 2026 from seed data if current date is different
        current_month_kwh = conn.execute(
            "SELECT COALESCE(SUM(units_consumed), 0) as total FROM MeterReadings WHERE billing_month = '2026-08'"
        ).fetchone()['total']

    # Financial stats
    total_revenue_khr = conn.execute(
        "SELECT COALESCE(SUM(amount_paid_khr), 0) as total FROM Payments"
    ).fetchone()['total']

    unpaid_stats = conn.execute('''
        SELECT 
            COUNT(*) as unpaid_count,
            COALESCE(SUM(total_amount_khr), 0) as unpaid_total_khr
        FROM Invoices 
        WHERE payment_status IN ('Unpaid', 'Overdue')
    ''').fetchone()

    overdue_count = conn.execute(
        "SELECT COUNT(*) as c FROM Invoices WHERE payment_status = 'Overdue'"
    ).fetchone()['c']

    # Monthly consumption trend (Last 6 months)
    monthly_trend = conn.execute('''
        SELECT billing_month, 
               COALESCE(SUM(units_consumed), 0) as total_kwh,
               COUNT(DISTINCT reading_id) as reading_count
        FROM MeterReadings
        GROUP BY billing_month
        ORDER BY billing_month ASC
        LIMIT 6
    ''').fetchall()

    # Customer breakdown by type
    customer_types = conn.execute('''
        SELECT customer_type, COUNT(*) as count 
        FROM Customers 
        GROUP BY customer_type
    ''').fetchall()

    # Recent Invoices
    recent_invoices = conn.execute('''
        SELECT i.*, c.full_name, c.customer_code, c.customer_type, m.meter_number
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.customer_id
        JOIN MeterReadings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        ORDER BY i.created_at DESC
        LIMIT 6
    ''').fetchall()

    conn.close()

    return {
        'total_customers': total_customers,
        'total_meters': total_meters,
        'current_month_kwh': current_month_kwh,
        'total_revenue_khr': total_revenue_khr,
        'total_revenue_usd': round(total_revenue_khr / USD_EXCHANGE_RATE, 2),
        'unpaid_count': unpaid_stats['unpaid_count'],
        'unpaid_total_khr': unpaid_stats['unpaid_total_khr'],
        'unpaid_total_usd': round(unpaid_stats['unpaid_total_khr'] / USD_EXCHANGE_RATE, 2),
        'overdue_count': overdue_count,
        'monthly_trend': [dict(m) for m in monthly_trend],
        'customer_types': [dict(ct) for ct in customer_types],
        'recent_invoices': recent_invoices
    }

# ----------------- AUTHENTICATION & USER MANAGEMENT ROUTES ----------------- #

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("សូមបញ្ចូលឈ្មោះគណនី និងពាក្យសម្ងាត់!", "danger")
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM Users WHERE UPPER(username) = UPPER(?)", (username,)).fetchone()
        conn.close()

        if not user or not verify_password(user['password_hash'], password):
            flash("ឈ្មោះគណនី ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវឡើយ!", "danger")
            return render_template('login.html')

        # Check Approval Status
        if user['status'] == 'Pending':
            flash("⏳ គណនីរបស់អ្នកកំពុងរង់ចាំការអនុម័ត (Pending Approval) ពី Admin នៅឡើយ! សូមរង់ចាំ Admin ពិនិត្យបើកសិទ្ធិ។", "warning")
            return render_template('login.html')

        if user['status'] == 'Rejected':
            flash("🚫 គណនីរបស់អ្នកត្រូវបានបដិសេធ (Rejected) ដោយ Admin! មិនអាចចូលប្រើប្រាស់បានឡើយ។", "danger")
            return render_template('login.html')

        # Successful Login
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['role'] = user['role']

        flash(f"សូមស្វាគមន៍មកកាន់ប្រព័ន្ធ, {user['full_name']}!", "success")
        return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not username or not full_name or not email or not password:
            flash("សូមបំពេញគ្រប់ព័ត៌មានដែលចាំបាច់ (*)", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("ពាក្យសម្ងាត់ទាំងពីរមិនត្រូវគ្នាឡើយ!", "danger")
            return render_template('register.html')

        conn = get_db_connection()

        # Strict Duplicate Prevention (ហាម User ស្ទួនពីរដាច់ខាត)
        existing_user = conn.execute(
            "SELECT * FROM Users WHERE UPPER(username) = UPPER(?) OR (email != '' AND UPPER(email) = UPPER(?))",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            if existing_user['username'].upper() == username.upper():
                flash("ឈ្មោះគណនី (Username) នេះមានអ្នកប្រើរួចហើយ! សូមជ្រើសរើសឈ្មោះផ្សេង (ហាមស្ទួន)។", "danger")
            else:
                flash("អ៊ីមែល (Email) នេះមានអ្នកប្រើរួចហើយ! សូមជ្រើសរើសអ៊ីមែលផ្សេង (ហាមស្ទួន)។", "danger")
            return render_template('register.html')

        # Hash password and insert as Pending (Requires Admin Approval)
        pwd_hash = generate_password_hash(password)
        try:
            conn.execute('''
                INSERT INTO Users (username, password_hash, full_name, email, phone_number, role, status)
                VALUES (?, ?, ?, ?, ?, 'Staff', 'Pending')
            ''', (username, pwd_hash, full_name, email, phone_number))
            conn.commit()
            conn.close()

            flash("🎉 ការចុះឈ្មោះបានជោគជ័យ! គណនីរបស់អ្នកកំពុងរង់ចាំការអនុម័តពី Admin (Pending Approval)។ សូមរង់ចាំ Admin ពិនិត្យ និងបើកដំណើរការ មុនពេលអាច Login បាន។", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            flash("ឈ្មោះគណនី ឬអ៊ីមែលនេះមានក្នុងប្រព័ន្ធរួចហើយ! មិនអនុញ្ញាតឱ្យចុះឈ្មោះស្ទួនឡើយ។", "danger")
            return render_template('register.html')
        except Exception as e:
            conn.close()
            flash(f"កំហុសក្នុងការចុះឈ្មោះ៖ {str(e)}", "danger")
            return render_template('register.html')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("បានចាកចេញពីប្រព័ន្ធដោយជោគជ័យ!", "info")
    return redirect(url_for('login'))

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    pending_users = conn.execute("SELECT * FROM Users WHERE status = 'Pending' ORDER BY created_at DESC").fetchall()
    all_users = conn.execute("SELECT * FROM Users ORDER BY role ASC, user_id ASC").fetchall()

    total_users_count = len(all_users)
    approved_users_count = sum(1 for u in all_users if u['status'] == 'Approved')
    admin_count = sum(1 for u in all_users if u['role'] == 'Admin')

    conn.close()
    return render_template('admin_users.html', 
                           pending_users=pending_users, 
                           all_users=all_users,
                           total_users_count=total_users_count,
                           approved_users_count=approved_users_count,
                           admin_count=admin_count)

@app.route('/admin/users/approve/<int:user_id>', methods=['POST'])
@admin_required
def admin_approve_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    if user:
        conn.execute('''
            UPDATE Users 
            SET status = 'Approved', approved_at = CURRENT_TIMESTAMP, approved_by = ? 
            WHERE user_id = ?
        ''', (session.get('username', 'Admin'), user_id))
        conn.commit()
        flash(f"បានអនុម័តគណនី {user['username']} ({user['full_name']}) ដោយជោគជ័យ! ឥឡូវគាត់អាច Login ចូលប្រើប្រាស់បានហើយ។", "success")
    else:
        flash("រកមិនឃើញគណនីនេះទេ!", "danger")
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/reject/<int:user_id>', methods=['POST'])
@admin_required
def admin_reject_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    if user:
        conn.execute("UPDATE Users SET status = 'Rejected' WHERE user_id = ?", (user_id,))
        conn.commit()
        flash(f"បានបដិសេធគណនី {user['username']} រួចរាល់!", "warning")
    else:
        flash("រកមិនឃើញគណនីនេះទេ!", "danger")
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/role/<int:user_id>', methods=['POST'])
@admin_required
def admin_toggle_role(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    if user:
        if user['username'].upper() == 'ADMIN':
            flash("មិនអាចប្តូរតួនាទីគណនី Root ADMIN បានឡើយ!", "warning")
        else:
            new_role = 'Staff' if user['role'] == 'Admin' else 'Admin'
            conn.execute("UPDATE Users SET role = ? WHERE user_id = ?", (new_role, user_id))
            conn.commit()
            flash(f"បានប្តូរតួនាទី {user['username']} ទៅជា {new_role} ដោយជោគជ័យ!", "success")
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    if user:
        if user['username'].upper() == 'ADMIN':
            flash("មិនអាចលុបគណនី Root ADMIN ចេញពីប្រព័ន្ធបានឡើយ!", "danger")
        else:
            conn.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
            conn.commit()
            flash(f"បានលុបគណនី {user['username']} ចេញពីប្រព័ន្ធដោយជោគជ័យ!", "info")
    conn.close()
    return redirect(url_for('admin_users'))

# ----------------- OPERATIONAL ROUTES ----------------- #

@app.route('/')
@app.route('/dashboard')
def dashboard():
    metrics = get_dashboard_metrics()
    return render_template('dashboard.html', metrics=metrics)

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    conn = get_db_connection()
    if request.method == 'POST':
        # Add new customer & meter
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        national_id = request.form.get('national_id', '')
        customer_type = request.form.get('customer_type', 'Residential')
        address = request.form.get('address')
        
        # Meter details
        meter_number = request.form.get('meter_number')
        transformer_pole_id = request.form.get('transformer_pole_id', 'P-GENERAL-01')
        phase_type = request.form.get('phase_type', '1-Phase (220V)')
        installation_date = request.form.get('installation_date', date.today().strftime('%Y-%m-%d'))
        
        # Generate customer code
        last_id = conn.execute("SELECT COALESCE(MAX(customer_id), 0) + 1 as next_id FROM Customers").fetchone()['next_id']
        customer_code = f"CUST-{1000 + last_id}"

        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Customers (customer_code, full_name, phone_number, national_id, customer_type, address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_code, full_name, phone_number, national_id, customer_type, address))
            cust_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO Meters (customer_id, meter_number, transformer_pole_id, phase_type, installation_date, status)
                VALUES (?, ?, ?, ?, ?, 'Active')
            ''', (cust_id, meter_number, transformer_pole_id, phase_type, installation_date))

            # Initial zero reading for baseline
            cursor.execute('''
                INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, notes)
                VALUES (?, ?, ?, 0.0, 0.0, 0.0, 'System Initializer', 'លេខកុងទ័រដំបូងកាលពីដំឡើង')
            ''', (cursor.lastrowid, installation_date, installation_date[:7]))

            conn.commit()
            flash(f"បានចុះឈ្មោះអតិថិជន {full_name} ({customer_code}) និងនាឡិកាស្ទង់ដោយជោគជ័យ!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"កំហុសក្នុងការចុះឈ្មោះ: {str(e)}", "danger")
        finally:
            conn.close()
        return redirect(url_for('customers'))

    # GET Filtered customers
    search = request.args.get('search', '').strip()
    type_filter = request.args.get('type', '')

    query = '''
        SELECT c.*, m.meter_id, m.meter_number, m.transformer_pole_id, m.phase_type, m.status as meter_status,
               (SELECT current_reading FROM MeterReadings WHERE meter_id = m.meter_id ORDER BY reading_date DESC LIMIT 1) as last_reading
        FROM Customers c
        LEFT JOIN Meters m ON c.customer_id = m.customer_id
        WHERE 1=1
    '''
    params = []
    if search:
        query += " AND (c.full_name LIKE ? OR c.customer_code LIKE ? OR c.phone_number LIKE ? OR m.meter_number LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])
    if type_filter:
        query += " AND c.customer_type = ?"
        params.append(type_filter)
    
    query += " ORDER BY c.customer_id DESC"
    customer_list = conn.execute(query, params).fetchall()

    # Calculate summary metrics for the customer KPI ribbon
    total_cust = conn.execute("SELECT COUNT(*) as c FROM Customers").fetchone()['c']
    active_meters_count = conn.execute("SELECT COUNT(*) as c FROM Meters WHERE status = 'Active'").fetchone()['c']
    res_count = conn.execute("SELECT COUNT(*) as c FROM Customers WHERE customer_type = 'Residential'").fetchone()['c']
    comm_count = conn.execute("SELECT COUNT(*) as c FROM Customers WHERE customer_type = 'Commercial'").fetchone()['c']
    ind_count = conn.execute("SELECT COUNT(*) as c FROM Customers WHERE customer_type = 'Industrial'").fetchone()['c']

    conn.close()

    return render_template('customers.html', 
                           customers=customer_list, 
                           search=search, 
                           type_filter=type_filter,
                           total_cust=total_cust,
                           active_meters_count=active_meters_count,
                           res_count=res_count,
                           comm_count=comm_count,
                           ind_count=ind_count)

@app.route('/readings', methods=['GET', 'POST'])
def readings():
    conn = get_db_connection()
    if request.method == 'POST':
        meter_id = int(request.form.get('meter_id'))
        reading_date = request.form.get('reading_date', date.today().strftime('%Y-%m-%d'))
        billing_month = request.form.get('billing_month', reading_date[:7])
        current_reading = float(request.form.get('current_reading'))
        previous_reading = float(request.form.get('previous_reading'))
        reader_name = request.form.get('reader_name', 'បុគ្គលិកស្រង់លេខ')
        notes = request.form.get('notes', '')
        is_spike_confirmed = 1 if request.form.get('is_spike_confirmed') == 'on' else 0

        # Validate
        is_valid, is_spike, msg = detect_spike_and_validate(meter_id, current_reading, previous_reading)
        if not is_valid:
            flash(msg, "danger")
            conn.close()
            return redirect(url_for('readings'))

        units_consumed = current_reading - previous_reading

        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes))
            reading_id = cursor.lastrowid

            # Auto-generate Invoice for this reading
            meter_info = conn.execute('''
                SELECT m.meter_number, c.customer_id, c.customer_type, c.full_name
                FROM Meters m
                JOIN Customers c ON m.customer_id = c.customer_id
                WHERE m.meter_id = ?
            ''', (meter_id,)).fetchone()

            bill_data = calculate_bill(meter_info['customer_type'], units_consumed)
            inv_date_str = datetime.now().strftime('%Y%m')
            inv_number = f"INV-{inv_date_str}-{reading_id:04d}"
            
            # Due date 15 days from reading
            due_date = (datetime.strptime(reading_date, '%Y-%m-%d') + timedelta(days=15)).strftime('%Y-%m-%d')

            # Generate KHQR
            khqr_payload = generate_bakong_khqr_payload(
                merchant_name="EDC ELECTRICITY",
                account_id="edc_billing@aclb",
                amount_khr=bill_data['total_amount_khr'],
                invoice_number=inv_number
            )

            cursor.execute('''
                INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date,
                                      units_consumed, energy_amount_khr, maintenance_fee_khr, tax_amount_khr,
                                      total_amount_khr, total_amount_usd, payment_status, khqr_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Unpaid', ?)
            ''', (inv_number, reading_id, meter_info['customer_id'], billing_month, reading_date, due_date,
                  units_consumed, bill_data['energy_amount_khr'], bill_data['maintenance_fee_khr'],
                  bill_data['tax_amount_khr'], bill_data['total_amount_khr'], bill_data['total_amount_usd'], khqr_payload))
            
            new_inv_id = cursor.lastrowid
            
            # Record tier details
            for tier in bill_data['tier_breakdown']:
                cursor.execute('''
                    INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
                    VALUES (?, ?, ?, ?, ?)
                ''', (new_inv_id, tier['tier_name'], tier['kwh'], tier['rate_khr'], tier['amount_khr']))

            conn.commit()
            flash(f"បានកត់ត្រាលេខកុងទ័រ ({units_consumed} kWh) និងបង្កើតវិក្កយបត្រ {inv_number} ដោយជោគជ័យ!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"កំហុសក្នុងការកត់ត្រា៖ {str(e)}", "danger")
        finally:
            conn.close()

        return redirect(url_for('readings'))

    # GET readings list
    readings_list = conn.execute('''
        SELECT r.*, m.meter_number, m.transformer_pole_id, c.full_name, c.customer_code, c.customer_type,
               i.invoice_id, i.invoice_number, i.total_amount_khr, i.payment_status
        FROM MeterReadings r
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        LEFT JOIN Invoices i ON r.reading_id = i.reading_id
        ORDER BY r.reading_id DESC
    ''').fetchall()

    # Active meters for the entry dropdown
    active_meters = conn.execute('''
        SELECT m.meter_id, m.meter_number, c.customer_code, c.full_name, c.customer_type,
               COALESCE((SELECT current_reading FROM MeterReadings WHERE meter_id = m.meter_id ORDER BY reading_date DESC LIMIT 1), 0.0) as last_reading
        FROM Meters m
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE m.status = 'Active'
        ORDER BY c.full_name ASC
    ''').fetchall()

    conn.close()
    return render_template('readings.html', readings=readings_list, active_meters=active_meters, today=date.today().strftime('%Y-%m-%d'))

@app.route('/invoices')
def invoices():
    status_filter = request.args.get('status', '')
    month_filter = request.args.get('month', '')
    search = request.args.get('search', '').strip()

    conn = get_db_connection()
    query = '''
        SELECT i.*, c.full_name, c.customer_code, c.customer_type, c.phone_number, m.meter_number, m.transformer_pole_id
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.customer_id
        JOIN MeterReadings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        WHERE 1=1
    '''
    params = []
    if status_filter:
        query += " AND i.payment_status = ?"
        params.append(status_filter)
    if month_filter:
        query += " AND i.billing_month = ?"
        params.append(month_filter)
    if search:
        query += " AND (i.invoice_number LIKE ? OR c.full_name LIKE ? OR c.customer_code LIKE ? OR m.meter_number LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    query += " ORDER BY i.invoice_id DESC"
    invoice_list = conn.execute(query, params).fetchall()

    # Get available billing months
    months = conn.execute("SELECT DISTINCT billing_month FROM Invoices ORDER BY billing_month DESC").fetchall()
    conn.close()

    return render_template('invoices.html', invoices=invoice_list, status_filter=status_filter, month_filter=month_filter, search=search, months=months)

@app.route('/invoices/<int:invoice_id>')
def invoice_view(invoice_id):
    conn = get_db_connection()
    inv = conn.execute('''
        SELECT i.*, c.full_name, c.customer_code, c.customer_type, c.phone_number, c.address, c.national_id,
               m.meter_number, m.transformer_pole_id, m.phase_type,
               r.previous_reading, r.current_reading, r.reading_date, r.reader_name
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.customer_id
        JOIN MeterReadings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        WHERE i.invoice_id = ?
    ''', (invoice_id,)).fetchone()

    if not inv:
        conn.close()
        flash("រកមិនឃើញវិក្កយបត្រនេះទេ!", "danger")
        return redirect(url_for('invoices'))

    details = conn.execute('''
        SELECT * FROM InvoiceDetails WHERE invoice_id = ? ORDER BY detail_id ASC
    ''', (invoice_id,)).fetchall()

    payment = conn.execute('''
        SELECT * FROM Payments WHERE invoice_id = ? ORDER BY payment_date DESC LIMIT 1
    ''', (invoice_id,)).fetchone()

    conn.close()

    # Generate QR Base64 Image
    qr_image_b64 = generate_qr_base64(inv['khqr_data']) if inv['khqr_data'] else None

    return render_template('invoice_view.html', inv=inv, details=details, payment=payment, qr_image_b64=qr_image_b64)

@app.route('/payments', methods=['GET', 'POST'])
def payments():
    conn = get_db_connection()
    if request.method == 'POST':
        invoice_id = int(request.form.get('invoice_id'))
        amount_paid = float(request.form.get('amount_paid'))
        payment_method = request.form.get('payment_method', 'KHQR')
        received_by = request.form.get('received_by', 'បេឡាការិក')
        reference_no = request.form.get('reference_no', '')
        notes = request.form.get('notes', '')

        receipt_number = f"REC-{datetime.now().strftime('%Y%m')}-{invoice_id:04d}"

        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Payments (receipt_number, invoice_id, amount_paid_khr, payment_method, received_by, reference_no, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (receipt_number, invoice_id, amount_paid, payment_method, received_by, reference_no, notes))

            # Mark invoice as Paid
            cursor.execute("UPDATE Invoices SET payment_status = 'Paid' WHERE invoice_id = ?", (invoice_id,))
            conn.commit()
            flash(f"បានទទួលការទូទាត់ប្រាក់ {amount_paid:,.0f} ៛ (បង្កាន់ដៃ #{receipt_number}) ដោយជោគជ័យ!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"កំហុសក្នុងការទូទាត់៖ {str(e)}", "danger")
        finally:
            conn.close()
        return redirect(url_for('payments'))

    # GET Payments
    payments_list = conn.execute('''
        SELECT p.*, i.invoice_number, i.billing_month, c.full_name, c.customer_code, c.phone_number
        FROM Payments p
        JOIN Invoices i ON p.invoice_id = i.invoice_id
        JOIN Customers c ON i.customer_id = c.customer_id
        ORDER BY p.payment_id DESC
    ''').fetchall()

    # Unpaid invoices for the modal dropdown
    unpaid_invoices = conn.execute('''
        SELECT i.invoice_id, i.invoice_number, i.total_amount_khr, i.billing_month, c.full_name, c.customer_code
        FROM Invoices i
        JOIN Customers c ON i.customer_id = c.customer_id
        WHERE i.payment_status IN ('Unpaid', 'Overdue')
        ORDER BY i.due_date ASC
    ''').fetchall()

    conn.close()
    return render_template('payments.html', payments=payments_list, unpaid_invoices=unpaid_invoices)

@app.route('/payments/receipt/<int:payment_id>')
def payment_receipt(payment_id):
    conn = get_db_connection()
    p = conn.execute('''
        SELECT p.*, i.invoice_number, i.billing_month, i.units_consumed, i.issue_date,
               c.full_name, c.customer_code, c.phone_number, c.address, c.customer_type,
               m.meter_number, m.transformer_pole_id
        FROM Payments p
        JOIN Invoices i ON p.invoice_id = i.invoice_id
        JOIN Customers c ON i.customer_id = c.customer_id
        JOIN MeterReadings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        WHERE p.payment_id = ?
    ''', (payment_id,)).fetchone()
    conn.close()

    if not p:
        flash("រកមិនឃើញបង្កាន់ដៃនេះទេ!", "danger")
        return redirect(url_for('payments'))

    return render_template('receipt_view.html', p=p)

@app.route('/tariffs', methods=['GET', 'POST'])
def tariffs():
    conn = get_db_connection()
    if request.method == 'POST':
        tier_id = int(request.form.get('tier_id'))
        rate_khr = float(request.form.get('rate_khr'))
        fixed_maintenance_khr = float(request.form.get('fixed_maintenance_khr'))
        vat_percent = float(request.form.get('vat_percent'))

        try:
            conn.execute('''
                UPDATE TariffTiers 
                SET rate_khr = ?, fixed_maintenance_khr = ?, vat_percent = ?
                WHERE tier_id = ?
            ''', (rate_khr, fixed_maintenance_khr, vat_percent, tier_id))
            conn.commit()
            flash("បានកែប្រែតម្លៃថ្លៃភ្លើងដោយជោគជ័យ!", "success")
        except Exception as e:
            flash(f"កំហុស៖ {str(e)}", "danger")
        finally:
            conn.close()
        return redirect(url_for('tariffs'))

    all_tariffs = conn.execute("SELECT * FROM TariffTiers ORDER BY customer_type, min_kwh").fetchall()
    conn.close()
    return render_template('tariffs.html', tariffs=all_tariffs)

# ----------------- JSON API ENDPOINTS ----------------- #

@app.route('/api/meters/<int:meter_id>/last-reading')
def api_last_reading(meter_id):
    conn = get_db_connection()
    reading = conn.execute('''
        SELECT current_reading, reading_date, units_consumed 
        FROM MeterReadings 
        WHERE meter_id = ? 
        ORDER BY reading_date DESC, reading_id DESC 
        LIMIT 1
    ''', (meter_id,)).fetchone()
    conn.close()

    if reading:
        return jsonify({
            'success': True,
            'last_reading': reading['current_reading'],
            'reading_date': reading['reading_date'],
            'last_units': reading['units_consumed']
        })
    return jsonify({'success': True, 'last_reading': 0.0, 'reading_date': '', 'last_units': 0.0})

@app.route('/api/readings/validate', methods=['POST'])
def api_validate_reading():
    data = request.get_json() or {}
    meter_id = int(data.get('meter_id', 0))
    current_reading = float(data.get('current_reading', 0))
    previous_reading = float(data.get('previous_reading', 0))

    is_valid, is_spike, msg = detect_spike_and_validate(meter_id, current_reading, previous_reading)
    units = max(0.0, current_reading - previous_reading)
    
    # Estimate preview bill
    conn = get_db_connection()
    cust = conn.execute('''
        SELECT c.customer_type FROM Meters m
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE m.meter_id = ?
    ''', (meter_id,)).fetchone()
    conn.close()

    est_bill = None
    if cust and is_valid:
        est_bill = calculate_bill(cust['customer_type'], units)

    return jsonify({
        'is_valid': is_valid,
        'is_spike': is_spike,
        'message': msg,
        'units_consumed': units,
        'estimated_bill': est_bill
    })

if __name__ == '__main__':
    init_db()
    import sys
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    app.run(host='0.0.0.0', port=5000, debug=False)
