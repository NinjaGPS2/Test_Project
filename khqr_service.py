import io
import base64
import qrcode

def calculate_crc16(data: str) -> str:
    """
    Computes CRC16-CCITT checksum for EMVCo standard (polynomial 0x1021, init 0xFFFF).
    """
    crc = 0xFFFF
    for char in data.encode('utf-8'):
        crc ^= (char << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def format_tlv(tag: str, value: str) -> str:
    """Formats Tag-Length-Value according to EMVCo standard."""
    length = f"{len(value):02d}"
    return f"{tag}{length}{value}"

def generate_bakong_khqr_payload(merchant_name: str, account_id: str, amount_khr: float, invoice_number: str) -> str:
    """
    Generates standard NBC Bakong KHQR string compliant with EMVCo QR code specification.
    """
    # 00: Format Indicator
    p_format = format_tlv("00", "01")
    # 01: Dynamic QR Code
    p_initiation = format_tlv("01", "12")

    # Tag 29: Bakong Merchant Account Information
    # Subtag 00: Global Unique Identifier
    sub_guid = format_tlv("00", "bakong@nbc")
    # Subtag 01: Account ID
    sub_acc = format_tlv("01", account_id)
    merchant_info_val = f"{sub_guid}{sub_acc}"
    p_merchant_info = format_tlv("29", merchant_info_val)

    # 52: Merchant Category Code (4900 - Utilities: Electric, Gas, Water)
    p_mcc = format_tlv("52", "4900")
    # 53: Transaction Currency (116 = KHR)
    p_currency = format_tlv("53", "116")
    # 54: Transaction Amount
    p_amount = format_tlv("54", str(int(amount_khr)))
    # 58: Country Code
    p_country = format_tlv("58", "KH")
    # 59: Merchant Name
    p_name = format_tlv("59", merchant_name[:25])
    # 60: Merchant City
    p_city = format_tlv("60", "Phnom Penh")

    # 62: Additional Data Field (Bill Number / Reference)
    sub_bill_ref = format_tlv("01", invoice_number)
    p_add_data = format_tlv("62", sub_bill_ref)

    # Partial raw string ending with Tag 63 Length 04
    raw_payload = f"{p_format}{p_initiation}{p_merchant_info}{p_mcc}{p_currency}{p_amount}{p_country}{p_name}{p_city}{p_add_data}6304"
    crc = calculate_crc16(raw_payload)
    full_khqr = f"{raw_payload}{crc}"
    return full_khqr

def generate_qr_base64(payload_text: str) -> str:
    """
    Generates a high-quality base64 Data URI string for HTML embedding.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(payload_text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#002D62", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_b64}"
