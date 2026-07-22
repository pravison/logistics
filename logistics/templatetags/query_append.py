from django import template
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

register = template.Library()

@register.filter
def add_query_param(url, param_string):
    """
    Append or update a query parameter to the given URL.
    Usage: {{ request.build_absolute_uri|add_query_param:"sort=name_az" }}
    """
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    key, value = param_string.split('=')
    query[key] = value
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)
