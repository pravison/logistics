# your_app/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def to(start, end):
    """
    Usage: {% for i in 1|to:21 %} gives range(1, 21)
    """
    return range(int(start), int(end))
