from django.core.cache import cache
#from django.utils.cache import get_cache_key
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.utils.hashcompat import md5_constructor
from django.conf import settings
from django.utils.encoding import smart_str, iri_to_uri
from django.utils.translation import get_language

from base.utils import log_to_file, separate_log

def _i18n_cache_key_suffix(request, cache_key):
    """If enabled, returns the cache key ending with a locale."""
    if settings.USE_I18N:
        # first check if LocaleMiddleware or another middleware added
        # LANGUAGE_CODE to request, then fall back to the active language
        # which in turn can also fall back to settings.LANGUAGE_CODE
        cache_key += '.%s' % getattr(request, 'LANGUAGE_CODE', get_language())
    return cache_key

def _generate_cache_header_key(key_prefix, request):
    """Returns a cache key for the header cache."""
    path = md5_constructor(iri_to_uri(request.path))
    cache_key = 'views.decorators.cache.cache_header.%s.%s' % (
        key_prefix, path.hexdigest())
    return _i18n_cache_key_suffix(request, cache_key)

def get_cache_key(request, key_prefix=None):
    if key_prefix is None:
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
    cache_key = _generate_cache_header_key(key_prefix, request)
    headerlist = cache.get(cache_key, None)
    if headerlist is not None:
        return cache_key
    else:
        return None


def expire_page(path):
	request = HttpRequest()
	request.path = path
	key = get_cache_key(request)
	log_to_file('deleting cache: %s, path: %s' % (key, request.path))
	if cache.has_key(key):   
		cache.delete(key)
		log_to_file('cache deleted %s, path: %s' % (key, request.path))
	else:
		log_to_file('no such key %s' % key)


def expire_view_cache(view_name, args=[], namespace=None, key_prefix=None):
	"""
	This function allows you to invalidate any view-level cache. 
		view_name: view function you wish to invalidate or it's named url pattern
		args: any arguments passed to the view function
		namepace: optioal, if an application namespace is needed
		key prefix: for the @cache_page decorator for the function (if any)
	"""
	# create a fake request object
	request = HttpRequest()
	# Loookup the request path:
	if namespace:
		view_name = namespace + ":" + view_name
	request.path = reverse(view_name, args=args)
	# get cache key, expire if the cached item exists:
	key = get_cache_key(request, key_prefix=key_prefix)
	
	log_to_file('deleting view cache: %s, view: %s' % (key, view_name))
	if key:
		#if cache.get(key):
		#	cache.set(key, None, 0)
		#return True
		if cache.has_key(key):
			cache.delete(key)
			log_to_file('cache deleted %s, view: %s' % (key, view_name))
		return True
	return False
	
