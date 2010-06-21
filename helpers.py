from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.core.urlresolvers import reverse
from django.http import HttpRequest

from base.utils import log_to_file, separate_log

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
	
