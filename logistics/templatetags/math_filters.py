# orders/templatetags/math_filters.py
from decimal import Decimal, InvalidOperation
from django import template
import math
register = template.Library()

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sum_quantity(items):
    """
    Sum item.quantity from a queryset or list
    """
    total = 0
    for item in items:
        qty = getattr(item, "quantity", 0) or 0
        total += qty
    return total



@register.filter
def floor_divide(value, divisor):
    """
    Returns whole number division (floor).
    Example: 3500|floor_divide:1000 => 3
    """
    try:
        value = Decimal(str(value or "0"))
        divisor = Decimal(str(divisor or "1"))

        if divisor == 0:
            return 0

        return int(value // divisor)

    except (InvalidOperation, ValueError, TypeError):
        return 0

@register.filter
def remaining(target, ordered):
    """
    target - ordered
    """
    try:
        return int(target) - int(ordered)
    except (TypeError, ValueError):
        return 0
        
@register.filter
def abs_value(value):
    try:
        return abs(int(value))
    except (TypeError, ValueError):
        return 0

@register.filter
def extra_payment(amount_paid, unit_price):
    """
    Returns extra money paid that doesn't complete a full unit.
    Example: amount_paid=4500, unit_price=1000 => 500
    """
    try:
        amount_paid = float(amount_paid or 0)
        unit_price = float(unit_price or 0)

        if unit_price <= 0:
            return 0

        full_units = int(amount_paid // unit_price)
        remainder = amount_paid - (full_units * unit_price)

        return round(remainder, 2)

    except (ValueError, TypeError):
        return 0
        
@register.filter
def add(value, arg):
    try:
        total = float(value) + float(arg)
        return math.ceil(total)
    except (ValueError, TypeError):
        return 0

