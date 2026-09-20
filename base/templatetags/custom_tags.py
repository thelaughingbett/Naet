# base/templatetags/custom_tags.py
from django.core.serializers.json import DjangoJSONEncoder
import json
from django import template
register = template.Library()


@register.filter
def dict_key(d, key):
    return d.get(key)


@register.filter
def to_json(value):
    return json.dumps(value, cls=DjangoJSONEncoder)
