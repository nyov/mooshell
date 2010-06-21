from django.core.cache import cache
from django.http import HttpRequest
from django.utils.cache import get_cache_key
from base.utils import log_to_file, separate_log

def expire_page(path):
	request = HttpRequest()
	request.path = path
	key = get_cache_key(request)
	if cache.has_key(key):   
		cache.delete(key)
		log_to_file('cache deleted %s, path: %s' % (key, request.path))
