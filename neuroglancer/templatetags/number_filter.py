from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

def currency(input):
    return "$%s%s" % (intcomma(int(input)), ("%0.2f" % input)[-3:])

register.filter('intcomma', intcomma)