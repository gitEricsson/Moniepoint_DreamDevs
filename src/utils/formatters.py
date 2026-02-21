"""
utils/formatters.py
──────────────────────────────────────────────────────────────────────────────
Shared formatting utilities (monetary, percentage).
"""
from decimal import Decimal, ROUND_HALF_UP

def format_monetary(value: Decimal | str | float) -> float:
    """Formats a decimal value strictly to 2 decimal places."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def format_percentage(value: Decimal | str | float) -> float:
    """Formats a decimal percentage to 1 decimal place."""
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
