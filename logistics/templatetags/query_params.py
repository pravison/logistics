from django import template
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

register = template.Library()

@register.simple_tag
def add_referral_param(url, key, value):
    """
    Add or update a query parameter in the URL.
    Usage: {% add_referral_param url 'key' value as new_url %}
    """
    url_parts = urlparse(url)
    query = dict(parse_qsl(url_parts.query))
    query[key] = value
    new_query = urlencode(query, doseq=True)
    return urlunparse(url_parts._replace(query=new_query))
