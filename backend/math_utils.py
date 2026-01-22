"""
Math Utilities

JavaScript-compatible rounding functions to ensure consistency between
backend (Python) and frontend (JavaScript).
"""

def js_round(value, decimals=0):
    """
    Round using "round half up" strategy (matches JavaScript Math.round).

    Python's built-in round() uses "round half to even" (banker's rounding):
        round(0.5) = 0 (even)
        round(1.5) = 2 (even)

    JavaScript Math.round() uses "round half up":
        Math.round(0.5) = 1 (always up)
        Math.round(1.5) = 2 (always up)

    This function mimics JavaScript behavior for cross-platform consistency.

    Args:
        value: Number to round
        decimals: Number of decimal places (0 = integer, default)

    Returns:
        Rounded number (float if decimals > 0, int if decimals = 0)

    Examples:
        js_round(0.5) = 1 (not 0)
        js_round(1.5) = 2
        js_round(2.5) = 3 (not 2)
        js_round(1.234, 2) = 1.23
        js_round(1.235, 2) = 1.24 (not 1.23)
    """
    multiplier = 10 ** decimals
    return int(value * multiplier + 0.5) / multiplier if decimals > 0 else int(value + 0.5)
