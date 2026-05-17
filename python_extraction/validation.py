from datetime import datetime, timedelta

def validate_invoice(data):
    flags = []

    # GST Mismatch Validation
    subtotal = float(data.get("subtotal") or 0)
    tax = float(data.get("tax") or 0)
    total = float(data.get("total_amount") or 0)
    expected_total = subtotal + tax
    if abs(expected_total - total) > 2:
        flags.append({
            "code": "GST_MISMATCH",
            "message": "Subtotal + tax does not match total amount"
        })

    # Missing GSTIN/PAN
    if tax > 0:
        if not data.get("gstin"):
            flags.append({
                "code": "MISSING_GSTIN",
                "message": "GSTIN missing while tax is charged"
            })

        if not data.get("pan"):
            flags.append({
                "code": "MISSING_PAN",
                "message": "PAN missing while tax is charged"
            })

    # Future Date
    invoice_date = data.get("invoice_date")
    if invoice_date:
        try:
            parsed_date = datetime.strptime(
                invoice_date,
                "%d-%m-%Y"
            )

            today = datetime.now()

            if parsed_date > today:
                flags.append({
                    "code": "FUTURE_DATED_INVOICE",
                    "message": "Invoice date is in the future"
                })

            # Old Invoice Validation (older than 1 year)
            if parsed_date < today - timedelta(days=365):
                flags.append({
                    "code": "OLD_INVOICE",
                    "message": "Invoice is older than 1 year"
                })

        except:
            flags.append({
                "code": "INVALID_DATE_FORMAT",
                "message": "Unable to parse invoice date"
            })

    return flags