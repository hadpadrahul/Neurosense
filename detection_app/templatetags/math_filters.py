from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """
    Multiply two numbers in templates: {{ value|mul:arg }}.
    Example: prob (0.82) * 100 -> 82.0
    """
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0
