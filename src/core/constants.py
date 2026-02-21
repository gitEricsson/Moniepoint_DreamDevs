from typing import Final

HEADER_PROCESS_TIME: Final[str] = "X-Process-Time"

ISO_8601_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S"
YYYY_MM_FORMAT: Final[str] = "%Y-%m"

VALID_PRODUCTS: Final[set[str]] = {"POS", "AIRTIME", "BILLS", "CARD_PAYMENT", "SAVINGS", "MONIEBOOK", "KYC"}
VALID_STATUSES: Final[set[str]] = {"SUCCESS", "FAILED", "PENDING"}
VALID_CHANNELS: Final[set[str]] = {"POS", "APP", "USSD", "WEB", "OFFLINE"}
