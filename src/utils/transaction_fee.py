TRANSACTION_FEE_CENTS = 250
MINIMUM_BALANCE_FOR_FEE_EXEMPTION_CENTS = 100000
DEFAULT_MONTHLY_FREE_TRANSFERS_LIMIT = 5


def calculate_fee(monthly_transfers_count: int, monthly_free_transfers_limit: int, source_balance: int) -> int:
    """Returns the fee in cents using the count before the current transfer."""
    if monthly_transfers_count < monthly_free_transfers_limit:
        return 0
    if source_balance >= MINIMUM_BALANCE_FOR_FEE_EXEMPTION_CENTS:
        return 0
    return TRANSACTION_FEE_CENTS
