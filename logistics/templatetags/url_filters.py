# your_app/templatetags/custom_filters.py

from django import template
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

register = template.Library()

@register.simple_tag
def add_query_param(url, key, value):
    """
    Add or replace a query parameter in the URL.
    Usage: {% add_query_param request.build_absolute_uri 'moq' 5 %}
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    query_params[str(key)] = [str(value)]  # set or replace the param
    new_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed_url._replace(query=new_query))


