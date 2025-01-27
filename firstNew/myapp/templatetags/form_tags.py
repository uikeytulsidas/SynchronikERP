from django import template

register = template.Library()

@register.filter(name='add_attrs')
def add_attrs(field, attrs):
    attrs = attrs.split(',')
    for attr in attrs:
        key, value = attr.split(':')
        field.field.widget.attrs[key] = value
    return field
