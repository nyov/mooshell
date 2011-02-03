from django import template
from django.utils import simplejson
from django.utils.safestring import mark_safe

from base.utils import log_to_file

register = template.Library()


@register.filter
def jsonify_pasties(pasties, server):
    """
        returns json version of pasties.
    """
    def build_dict(pastie):
        shell = pastie.favourite
        if not shell.author:
            log_to_file(
                    'WARNING: Shell has no author %s' % shell.get_absolute_url())
        return {
            "title": shell.title,
            "author": shell.author.username if shell.author else 'no author',
            "description": shell.description,
            "url": "%s%s" % (server, shell.get_absolute_url()),
            "version": shell.version,
            "created": shell.created_at.strftime("%Y-%m-%d %H:%I:%S"),
            "framework": shell.js_lib.library_group.name,
            "latest_version": pastie.get_latest().version
        }

    return mark_safe(simplejson.dumps([build_dict(pastie) for pastie in pasties]))
