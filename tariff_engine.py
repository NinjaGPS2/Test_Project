from database import get_db_connection

USD_EXCHANGE_RATE = 4100.0  # 1 USD = 4,100 KHR

def get_tariff_tiers(customer_type):
    conn = get_db_connection()
    tiers = conn.execute(
        'SELECT * FROM TariffTiers WHERE customer_type = ? ORDER BY min_kwh ASC',
        (customer_type,)
    ).fetchall()
    conn.close()
    return tiers

def calculate_bill(customer_type, units_consumed):
    """
    Calculates electricity bill based on stepped / tiered rates according to customer_type.
    Returns:
        {
            'units_consumed': float,
            'tier_breakdown': list of {'tier_name', 'kwh', 'rate_khr', 'amount_khr'},
            'energy_amount_khr': float,
            'maintenance_fee_khr': float,
            'vat_percent': float,
            'tax_amount_khr': float,
            'total_amount_khr': float,
            'total_amount_usd': float
        }
    """
    tiers = get_tariff_tiers(customer_type)
    if not tiers:
        # Default fallback if no tiers configured in DB
        rates = {
            'Residential': [(50, 380), (200, 610), (float('inf'), 740)],
            'Commercial': [(200, 790), (float('inf'), 820)],
            'Industrial': [(float('inf'), 740)]
        }
        fallback_rate = 650.0
        return {
            'units_consumed': units_consumed,
            'tier_breakdown': [{'tier_name': 'អត្រាទូទៅ', 'kwh': units_consumed, 'rate_khr': fallback_rate, 'amount_khr': units_consumed * fallback_rate}],
            'energy_amount_khr': round(units_consumed * fallback_rate, 2),
            'maintenance_fee_khr': 2000,
            'vat_percent': 10,
            'tax_amount_khr': round((units_consumed * fallback_rate + 2000) * 0.1, 2),
            'total_amount_khr': round((units_consumed * fallback_rate + 2000) * 1.1, 0),
            'total_amount_usd': round(((units_consumed * fallback_rate + 2000) * 1.1) / USD_EXCHANGE_RATE, 2)
        }

    remaining_units = units_consumed
    tier_breakdown = []
    total_energy_khr = 0.0
    maintenance_fee = tiers[0]['fixed_maintenance_khr'] if tiers else 2000.0
    vat_percent = tiers[0]['vat_percent'] if tiers else 10.0

    for tier in tiers:
        min_k = tier['min_kwh']
        max_k = tier['max_kwh']
        rate = tier['rate_khr']
        tier_name = tier['tier_name']

        if remaining_units <= 0:
            break

        if max_k is not None:
            capacity = max_k - (min_k - 1) if min_k > 0 else max_k
            kwh_in_this_tier = min(remaining_units, capacity)
        else:
            kwh_in_this_tier = remaining_units

        tier_amount = kwh_in_this_tier * rate
        total_energy_khr += tier_amount
        remaining_units -= kwh_in_this_tier

        tier_breakdown.append({
            'tier_name': tier_name,
            'kwh': round(kwh_in_this_tier, 2),
            'rate_khr': rate,
            'amount_khr': round(tier_amount, 2)
        })

    # Low residential consumption exemption or reduced VAT
    if customer_type == 'Residential' and units_consumed <= 50:
        vat_percent = 0.0  # Exempt for low usage residential

    tax_amount_khr = round((total_energy_khr + maintenance_fee) * (vat_percent / 100.0), 2)
    total_amount_khr = round(total_energy_khr + maintenance_fee + tax_amount_khr, 0)
    total_amount_usd = round(total_amount_khr / USD_EXCHANGE_RATE, 2)

    return {
        'units_consumed': round(units_consumed, 2),
        'tier_breakdown': tier_breakdown,
        'energy_amount_khr': round(total_energy_khr, 2),
        'maintenance_fee_khr': round(maintenance_fee, 2),
        'vat_percent': vat_percent,
        'tax_amount_khr': tax_amount_khr,
        'total_amount_khr': total_amount_khr,
        'total_amount_usd': total_amount_usd
    }

def detect_spike_and_validate(meter_id, current_reading, previous_reading):
    """
    Validates meter reading and tests for abnormal surge (Spike alert).
    Returns (is_valid, is_spike, message)
    """
    if current_reading < previous_reading:
        return False, False, f"កំហុស៖ លេខថ្មី ({current_reading}) មិនអាចតូចជាងលេខចាស់ ({previous_reading}) បានទេ!"

    units = current_reading - previous_reading
    conn = get_db_connection()
    past_readings = conn.execute(
        '''SELECT units_consumed FROM MeterReadings 
           WHERE meter_id = ? ORDER BY reading_date DESC LIMIT 3''',
        (meter_id,)
    ).fetchall()
    conn.close()

    if past_readings:
        past_units = [r['units_consumed'] for r in past_readings]
        avg_units = sum(past_units) / len(past_units)
        # Spike threshold: consumption is more than 50% above average or 50% above last month
        if avg_units > 15 and units > avg_units * 1.5:
            percent_increase = round(((units - avg_units) / avg_units) * 100)
            msg = (f"ការព្រមានពីការកើនឡើងខុសប្រក្រតី (Spike Alert)! "
                   f"ការប្រើប្រាស់ {units} kWh កើនឡើង {percent_increase}% "
                   f"ធៀបនឹងមធ្យមភាគ {round(avg_units, 1)} kWh នៃខែមុន។ "
                   f"សូមផ្ទៀងផ្ទាត់លេខកុងទ័រឡើងវិញ ឬបញ្ជាក់ការទទួលស្គាល់។")
            return True, True, msg

    return True, False, "ទិន្នន័យត្រឹមត្រូវ"
