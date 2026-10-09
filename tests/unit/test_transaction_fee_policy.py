from utils.transaction_fee import calculate_fee


def test_free_transfer_inside_default_allowance():
    assert calculate_fee(0, 5, 50_000) == 0
    assert calculate_fee(4, 5, 50_000) == 0


def test_sixth_transfer_is_charged_below_minimum_balance():
    assert calculate_fee(5, 5, 99_999) == 250


def test_minimum_balance_is_inclusive():
    assert calculate_fee(5, 5, 100_000) == 0
    assert calculate_fee(5, 5, 100_001) == 0


def test_zero_allowance_and_custom_allowance():
    assert calculate_fee(0, 0, 99_999) == 250
    assert calculate_fee(2, 3, 99_999) == 0
    assert calculate_fee(3, 3, 99_999) == 250
