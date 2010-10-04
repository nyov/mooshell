"""
Default MooShell Context Templates
"""
from django.conf import settings


def _get_if_hasattr(setting, default=""):
    " return setting only if exists, defaults to \"\" "
    return getattr(settings, setting) if hasattr(settings, setting) else default


def load_settings(request):
    " inject keys as variables into the template context"
    return {
        'project_name': _get_if_hasattr('MOOSHELL_PROJECT_NAME'),
        'project_status': _get_if_hasattr('MOOSHELL_PROJECT_STATUS'),
        'seo_title_pre': _get_if_hasattr('MOOSHELL_SEO_TITLE_HEAD'),
        'seo_title_tail': _get_if_hasattr('MOOSHELL_SEO_TITLE_TAIL'),
        'title_separator': _get_if_hasattr('MOOSHELL_TITLE_SEPARATOR'),
        'SEO_DESCRIPTION': _get_if_hasattr('MOOSHELL_SEO_DESCRIPTION'),
        'SEO_KEYWORDS': _get_if_hasattr('MOOSHELL_SEO_KEYWORDS'),
        'DEBUG': _get_if_hasattr('DEBUG'),
        'WEB_SERVER': request.META['SERVER_NAME'],
        'default_library_group': _get_if_hasattr('MOOSHELL_LIBRARY_GROUP'),
        'GOOGLE_ANALYTICS_ID': _get_if_hasattr('GOOGLE_ANALYTICS_ID'),
        'GOOGLE_VERIFICATION_META_TAG': _get_if_hasattr(
            'GOOGLE_VERIFICATION_META_TAG'),
        'SHOW_LIB_OPTION': _get_if_hasattr('MOOSHELL_SHOW_LIB_OPTION'),
        'FORCE_SHOW_SERVER': _get_if_hasattr('MOOSHELL_FORCE_SHOW_SERVER'),
        'SPECIAL_HEAD_CODE': _get_if_hasattr('MOOSHELL_SPECIAL_HEAD_CODE')
        }
