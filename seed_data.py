from database import init_db, get_db_connection
from tariff_engine import calculate_bill
from khqr_service import generate_bakong_khqr_payload
from datetime import datetime, timedelta

def seed():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM Payments")
    cursor.execute("DELETE FROM InvoiceDetails")
    cursor.execute("DELETE FROM Invoices")
    cursor.execute("DELETE FROM MeterReadings")
    cursor.execute("DELETE FROM TariffTiers")
    cursor.execute("DELETE FROM Meters")
    cursor.execute("DELETE FROM Customers")

    print("Populating Tariff Tiers...")
    tariffs = [
        # Residential
        ('Residential', 'កម្រិត ១ (1 - 50 kWh)', 1, 50, 380, 2000, 10),
        ('Residential', 'កម្រិត ២ (51 - 200 kWh)', 51, 200, 610, 2000, 10),
        ('Residential', 'កម្រិត ៣ (លើសពី 200 kWh)', 201, None, 740, 2000, 10),
        
        # Commercial
        ('Commercial', 'កម្រិត ១ (1 - 200 kWh)', 1, 200, 790, 5000, 10),
        ('Commercial', 'កម្រិត ២ (លើសពី 200 kWh)', 201, None, 820, 5000, 10),
        
        # Industrial
        ('Industrial', 'អត្រាថេរឧស្សាហកម្ម (> 0 kWh)', 1, None, 740, 25000, 10),
    ]

    cursor.executemany('''
    INSERT INTO TariffTiers (customer_type, tier_name, min_kwh, max_kwh, rate_khr, fixed_maintenance_khr, vat_percent)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', tariffs)

    print("Populating Customers...")
    customers_data = [
        ('CUST-1001', 'សុខ ចិន្តា (Sok Chenda)', '012 888 991', '010203040', 'Residential', 'ផ្ទះលេខ #14, ផ្លូវ 289, សង្កាត់បឹងកក់២, ខណ្ឌទួលគោក, ភ្នំពេញ'),
        ('CUST-1002', 'ហេង វិសាល (Heng Visal)', '098 776 554', '010405060', 'Residential', 'ផ្ទះលេខ #88, ផ្លូវ 598, សង្កាត់ភ្នំពេញថ្មី, ខណ្ឌសែនសុខ, ភ្នំពេញ'),
        ('CUST-1003', 'ចាន់ មករា (ហាងកាហ្វេ Cafe Amazon)', '017 334 556', '010809101', 'Commercial', 'ផ្ទះលេខ #210, មហាវិថីព្រះមុនីវង្ស, សង្កាត់វត្តភ្នំ, ខណ្ឌដូនពេញ, ភ្នំពេញ'),
        ('CUST-1004', 'លីម សេរីរ័ត្ន (ម៉ាត Lucky Express)', '077 221 445', '010992211', 'Commercial', 'ផ្ទះលេខ #52, ផ្លូវ 2004, សង្កាត់កាកាប, ខណ្ឌពោធិ៍សែនជ័យ, ភ្នំពេញ'),
        ('CUST-1005', 'រោងចក្រកាត់ដេរខ្មែរ រុងរឿង (Khmer Garment)', '023 881 223', '010555332', 'Industrial', 'ផ្លូវជាតិលេខ 4, សង្កាត់ចោមចៅ, ខណ្ឌពោធិ៍សែនជ័យ, ភ្នំពេញ'),
        ('CUST-1006', 'កែវ ពិសិដ្ឋ (Keo Piseth)', '089 556 677', '010114422', 'Residential', 'ផ្ទះលេខ #45, ផ្លូវ 315, សង្កាត់បឹងកក់១, ខណ្ឌទួលគោក, ភ្នំពេញ')
    ]

    for c in customers_data:
        cursor.execute('''
        INSERT INTO Customers (customer_code, full_name, phone_number, national_id, customer_type, address)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', c)

    conn.commit()

    print("Populating Meters...")
    meters_data = [
        (1, 'MTR-TK-008123', 'P-TK-104', '1-Phase (220V)', '2024-01-15', 'Active'),
        (2, 'MTR-SS-009451', 'P-SS-088', '1-Phase (220V)', '2024-03-10', 'Active'),
        (3, 'MTR-DP-011244', 'P-DP-022', '3-Phase (380V)', '2023-11-20', 'Active'),
        (4, 'MTR-PS-014589', 'P-PS-071', '3-Phase (380V)', '2024-02-05', 'Active'),
        (5, 'MTR-IND-99120', 'TR-CP-009', '3-Phase High Voltage (22kV)', '2022-08-12', 'Active'),
        (6, 'MTR-TK-008127', 'P-TK-105', '1-Phase (220V)', '2024-04-18', 'Active'),
    ]

    for m in meters_data:
        cursor.execute('''
        INSERT INTO Meters (customer_id, meter_number, transformer_pole_id, phase_type, installation_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', m)

    conn.commit()

    print("Populating Meter Readings and Invoices...")
    # Customer 1: Sok Chenda (Residential)
    # Month 1 (July 2026)
    r1_data = (1, '2026-07-25', '2026-07', 1240.0, 1380.0, 140.0, 'កែវ វិបុល (Reader-01)', 0, 'ធម្មតា')
    cursor.execute('''
    INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', r1_data)
    r1_id = cursor.lastrowid
    
    # Bill for Month 1 (Paid)
    bill1 = calculate_bill('Residential', 140.0)
    inv1_num = 'INV-202607-001'
    khqr1 = generate_bakong_khqr_payload('EDC ELECTRICITY', 'edc_billing@aclb', bill1['total_amount_khr'], inv1_num)
    cursor.execute('''
    INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date, units_consumed,
                          energy_amount_khr, maintenance_fee_khr, tax_amount_khr, total_amount_khr, total_amount_usd, payment_status, khqr_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (inv1_num, r1_id, 1, '2026-07', '2026-07-26', '2026-08-10', 140.0,
          bill1['energy_amount_khr'], bill1['maintenance_fee_khr'], bill1['tax_amount_khr'], bill1['total_amount_khr'], bill1['total_amount_usd'], 'Paid', khqr1))
    inv1_id = cursor.lastrowid

    for d in bill1['tier_breakdown']:
        cursor.execute('''
        INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
        VALUES (?, ?, ?, ?, ?)
        ''', (inv1_id, d['tier_name'], d['kwh'], d['rate_khr'], d['amount_khr']))

    # Payment for Inv 1
    cursor.execute('''
    INSERT INTO Payments (receipt_number, invoice_id, amount_paid_khr, payment_method, received_by, reference_no, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('REC-202607-001', inv1_id, bill1['total_amount_khr'], 'KHQR', 'Bakong Payment Gateway', 'BK-99238411', 'បង់តាមរយៈ Bakong KHQR'))

    # Month 2 (August 2026) for Customer 1 (Unpaid, Current)
    r1_aug = (1, '2026-08-25', '2026-08', 1380.0, 1545.0, 165.0, 'កែវ វិបុល (Reader-01)', 0, 'ធម្មតា')
    cursor.execute('''
    INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', r1_aug)
    r1_aug_id = cursor.lastrowid
    
    bill1_aug = calculate_bill('Residential', 165.0)
    inv1_aug_num = 'INV-202608-001'
    khqr1_aug = generate_bakong_khqr_payload('EDC ELECTRICITY', 'edc_billing@aclb', bill1_aug['total_amount_khr'], inv1_aug_num)
    cursor.execute('''
    INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date, units_consumed,
                          energy_amount_khr, maintenance_fee_khr, tax_amount_khr, total_amount_khr, total_amount_usd, payment_status, khqr_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (inv1_aug_num, r1_aug_id, 1, '2026-08', '2026-08-26', '2026-09-12', 165.0,
          bill1_aug['energy_amount_khr'], bill1_aug['maintenance_fee_khr'], bill1_aug['tax_amount_khr'], bill1_aug['total_amount_khr'], bill1_aug['total_amount_usd'], 'Unpaid', khqr1_aug))
    inv1_aug_id = cursor.lastrowid

    for d in bill1_aug['tier_breakdown']:
        cursor.execute('''
        INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
        VALUES (?, ?, ?, ?, ?)
        ''', (inv1_aug_id, d['tier_name'], d['kwh'], d['rate_khr'], d['amount_khr']))

    # Customer 2: Heng Visal (Residential - Low Usage: 45 kWh, exempt VAT)
    r2_data = (2, '2026-08-25', '2026-08', 510.0, 555.0, 45.0, 'ស៊ុន ដារ៉ា (Reader-02)', 0, 'ការប្រើប្រាស់ទាប')
    cursor.execute('''
    INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', r2_data)
    r2_id = cursor.lastrowid

    bill2 = calculate_bill('Residential', 45.0)
    inv2_num = 'INV-202608-002'
    khqr2 = generate_bakong_khqr_payload('EDC ELECTRICITY', 'edc_billing@aclb', bill2['total_amount_khr'], inv2_num)
    cursor.execute('''
    INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date, units_consumed,
                          energy_amount_khr, maintenance_fee_khr, tax_amount_khr, total_amount_khr, total_amount_usd, payment_status, khqr_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (inv2_num, r2_id, 2, '2026-08', '2026-08-26', '2026-09-12', 45.0,
          bill2['energy_amount_khr'], bill2['maintenance_fee_khr'], bill2['tax_amount_khr'], bill2['total_amount_khr'], bill2['total_amount_usd'], 'Paid', khqr2))
    inv2_id = cursor.lastrowid
    for d in bill2['tier_breakdown']:
        cursor.execute('''
        INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
        VALUES (?, ?, ?, ?, ?)
        ''', (inv2_id, d['tier_name'], d['kwh'], d['rate_khr'], d['amount_khr']))
    cursor.execute('''
    INSERT INTO Payments (receipt_number, invoice_id, amount_paid_khr, payment_method, received_by, reference_no, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('REC-202608-002', inv2_id, bill2['total_amount_khr'], 'Cash', 'បេឡាការិក កែវ រតនា', 'CASH-9912', 'បង់ប្រាក់ផ្ទាល់នៅការិយាល័យ EDC'))

    # Customer 3: Cafe Amazon (Commercial - 850 kWh, Overdue bill from July)
    r3_jul = (3, '2026-07-24', '2026-07', 4200.0, 5050.0, 850.0, 'កែវ វិបុល (Reader-01)', 0, 'អាជីវកម្មម៉ោងពេញ')
    cursor.execute('''
    INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', r3_jul)
    r3_jul_id = cursor.lastrowid

    bill3_jul = calculate_bill('Commercial', 850.0)
    inv3_jul_num = 'INV-202607-003'
    khqr3_jul = generate_bakong_khqr_payload('EDC ELECTRICITY', 'edc_billing@aclb', bill3_jul['total_amount_khr'], inv3_jul_num)
    cursor.execute('''
    INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date, units_consumed,
                          energy_amount_khr, maintenance_fee_khr, tax_amount_khr, total_amount_khr, total_amount_usd, payment_status, khqr_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (inv3_jul_num, r3_jul_id, 3, '2026-07', '2026-07-25', '2026-08-08', 850.0,
          bill3_jul['energy_amount_khr'], bill3_jul['maintenance_fee_khr'], bill3_jul['tax_amount_khr'], bill3_jul['total_amount_khr'], bill3_jul['total_amount_usd'], 'Overdue', khqr3_jul))
    inv3_jul_id = cursor.lastrowid
    for d in bill3_jul['tier_breakdown']:
        cursor.execute('''
        INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
        VALUES (?, ?, ?, ?, ?)
        ''', (inv3_jul_id, d['tier_name'], d['kwh'], d['rate_khr'], d['amount_khr']))

    # Customer 4: Lucky Express (Commercial - August 2026, 1200 kWh, Unpaid)
    r4_aug = (4, '2026-08-26', '2026-08', 7800.0, 9000.0, 1200.0, 'ស៊ុន ដារ៉ា (Reader-02)', 0, 'ដំណើរការម៉ាស៊ីនត្រជាក់ 24/7')
    cursor.execute('''
    INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', r4_aug)
    r4_aug_id = cursor.lastrowid
    bill4_aug = calculate_bill('Commercial', 1200.0)
    inv4_aug_num = 'INV-202608-004'
    khqr4 = generate_bakong_khqr_payload('EDC ELECTRICITY', 'edc_billing@aclb', bill4_aug['total_amount_khr'], inv4_aug_num)
    cursor.execute('''
    INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date, units_consumed,
                          energy_amount_khr, maintenance_fee_khr, tax_amount_khr, total_amount_khr, total_amount_usd, payment_status, khqr_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (inv4_aug_num, r4_aug_id, 4, '2026-08', '2026-08-27', '2026-09-15', 1200.0,
          bill4_aug['energy_amount_khr'], bill4_aug['maintenance_fee_khr'], bill4_aug['tax_amount_khr'], bill4_aug['total_amount_khr'], bill4_aug['total_amount_usd'], 'Unpaid', khqr4))
    inv4_aug_id = cursor.lastrowid
    for d in bill4_aug['tier_breakdown']:
        cursor.execute('''
        INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
        VALUES (?, ?, ?, ?, ?)
        ''', (inv4_aug_id, d['tier_name'], d['kwh'], d['rate_khr'], d['amount_khr']))

    # Customer 5: Khmer Garment Factory (Industrial - 18,500 kWh, Paid via Bank Transfer)
    r5_aug = (5, '2026-08-26', '2026-08', 85000.0, 103500.0, 18500.0, 'ម៉េង ហុង (Industrial Reader)', 0, 'បន្ទុកធម្មតា')
    cursor.execute('''
    INSERT INTO MeterReadings (meter_id, reading_date, billing_month, previous_reading, current_reading, units_consumed, reader_name, is_spike_confirmed, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', r5_aug)
    r5_aug_id = cursor.lastrowid
    bill5_aug = calculate_bill('Industrial', 18500.0)
    inv5_aug_num = 'INV-202608-005'
    khqr5 = generate_bakong_khqr_payload('EDC ELECTRICITY', 'edc_billing@aclb', bill5_aug['total_amount_khr'], inv5_aug_num)
    cursor.execute('''
    INSERT INTO Invoices (invoice_number, reading_id, customer_id, billing_month, issue_date, due_date, units_consumed,
                          energy_amount_khr, maintenance_fee_khr, tax_amount_khr, total_amount_khr, total_amount_usd, payment_status, khqr_data)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (inv5_aug_num, r5_aug_id, 5, '2026-08', '2026-08-27', '2026-09-15', 18500.0,
          bill5_aug['energy_amount_khr'], bill5_aug['maintenance_fee_khr'], bill5_aug['tax_amount_khr'], bill5_aug['total_amount_khr'], bill5_aug['total_amount_usd'], 'Paid', khqr5))
    inv5_aug_id = cursor.lastrowid
    for d in bill5_aug['tier_breakdown']:
        cursor.execute('''
        INSERT INTO InvoiceDetails (invoice_id, tier_name, kwh_in_tier, rate_khr, subtotal_khr)
        VALUES (?, ?, ?, ?, ?)
        ''', (inv5_aug_id, d['tier_name'], d['kwh'], d['rate_khr'], d['amount_khr']))
    cursor.execute('''
    INSERT INTO Payments (receipt_number, invoice_id, amount_paid_khr, payment_method, received_by, reference_no, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('REC-202608-005', inv5_aug_id, bill5_aug['total_amount_khr'], 'Bank Transfer', 'ធនាគារវឌ្ឍនៈ (Vattanac Bank)', 'FT-202608-9842', 'ផ្ទេរប្រាក់តាមធនាគារសាជីវកម្ម'))

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic Cambodian electricity billing data!")

if __name__ == '__main__':
    seed()
