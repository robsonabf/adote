from django import template
from ..views import is_member_of_team


register = template.Library()


@register.filter(name='is_member_of_team')
def is_member_of_team_filter(user):
    return is_member_of_team(user)
