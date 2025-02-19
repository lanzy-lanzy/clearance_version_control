from django import template

register = template.Library()

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtracts the arg from the value"""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value

@register.filter(name='has_attr')
def has_attr(obj, attr_name):
    """Checks if an object has the specified attribute"""
    return hasattr(obj, attr_name)

@register.filter(name='rejectattr')
def rejectattr(value, attr_value_pair):
    """
    Filter a list of objects based on an attribute not equal to a value
    Usage: {{ students|rejectattr:"is_approved,True" }}
    """
    try:
        attr, val = attr_value_pair.split(',')
        val = val.strip().lower() == 'true'  # Convert string to boolean
        return [item for item in value if not getattr(item, attr, None) == val]
    except (ValueError, AttributeError):
        return value
