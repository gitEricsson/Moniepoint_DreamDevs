from decimal import Decimal, ROUND_HALF_UP

def format_monetary(value: Decimal | str | float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def format_percentage(value: Decimal | str | float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
