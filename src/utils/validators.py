from src.core.constants import VALID_PRODUCTS, VALID_STATUSES, VALID_CHANNELS

def validate_status_value(status: str) -> str:
    cleaned = status.strip().upper()
    if cleaned not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")
    return cleaned

def validate_product_value(product: str) -> str:
    cleaned = product.strip().upper()
    if cleaned not in VALID_PRODUCTS:
        raise ValueError(f"Invalid product: {product!r}")
    return cleaned

def validate_channel_value(channel: str | None) -> str | None:
    if not channel or not channel.strip():
        return None
    cleaned = channel.strip().upper()
    return cleaned if cleaned in VALID_CHANNELS else None
