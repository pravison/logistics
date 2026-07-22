# yourapp/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def sort_by_score(participants):
    return sorted(
        participants,
        key=lambda p: getattr(p, 'result', None) and p.result.total_score or 0,
        reverse=True
    )
