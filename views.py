import os.path
import random
import time
import base64

from django.shortcuts import render_to_response, get_object_or_404
from django.views import static
from django.conf import settings   
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.template import Template,RequestContext
from django.contrib.auth.models import User
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from models import Pastie, Shell, JSLibraryGroup, JSLibrary, JSLibraryWrap, JSDependency, ExternalResource, DocType, ShellExternalResource
from forms import PastieForm, ShellForm
from base.views import serve_static as base_serve_static
from base.utils import log_to_file, separate_log
from mooshell.helpers import expire_page, expire_view_cache


# consider better caching for that function.

CACHE_TIME = settings.CACHE_MIDDLEWARE_SECONDS

def get_pastie_edit_key(req, slug=None, version=None, revision=None, author=None, skin=None):

	key = "%s:pastie_edit" % settings.CACHE_MIDDLEWARE_KEY_PREFIX 
	key = "%s:%s" % (key, slug) if slug else '%s:homepage' % key
	if version: key = "%s:%s" % (key, version)
	if revision: key = "%s:%d" % (key, revision)
	if author: key = "%s:%s" % (key, author)
	if skin: key = "%s:%s" % (key, skin)

	return key

def pastie_edit(req, slug=None, version=None, revision=None, author=None, skin=None):
	"""
	display the edit shell page ( main display)
	"""
	
	#separate_log('-')
	#log_to_file('pastie_edit')
	# build the cache key on the basis of url and user
	key = get_pastie_edit_key(req, slug, version, revision, author, skin) 
	
	if cache.get(key, None):
		#log_to_file('pastie_edit - cache key found %s' % key)
		c = cache.get(key)
	else:
		#log_to_file('pastie_edit - no cache key found %s - generating from db' % key)
		shell = None
		c = {}
		
		try:
			server = settings.MOOSHELL_FORCE_SERVER
		except:
			server = 'http://%s' % req.META['SERVER_NAME']

		title = settings.MOOSHELL_NEW_TITLE
			
		doctypes = DocType.objects.all()
		external_resources = []
		disqus_url = ''.join([server, '/'])
		if slug:
			if skin:
				" important as {user}/{slug} is indistingushable from {slug}/{skin} "
				try:
					user = User.objects.get(username=slug)
					author = slug
					slug = skin
					skin = None
				except:
					pass
			pastie = get_object_or_404(Pastie, slug=slug)
			if version == None:
				shell = pastie.favourite
			else:
				user = get_object_or_404(User,username=author) if author else None
				shell = get_object_or_404(Shell, pastie__slug=slug, version=version, author=user)
			
			external_resources = ShellExternalResource.objects.filter(shell__id=shell.id)

			example_url = ''.join([server, shell.get_absolute_url()])
			embedded_url = ''.join([server, shell.get_embedded_url()])
			disqus_url = ''.join([server, shell.pastie.favourite.get_absolute_url()])
			c['embedded_url'] = embedded_url
			title = shell.title if shell.title else settings.MOOSHELL_VIEW_TITLE
			for dtd in doctypes:
				if dtd.id == shell.doctype.id:
					dtd.current = True
		else:
			example_url = ''
			#pastieform = PastieForm()
			shellform = ShellForm()
		
		if settings.DEBUG: moo = settings.MOOTOOLS_DEV_CORE
		else: moo = settings.MOOTOOLS_CORE
		
		if not skin: skin = req.GET.get('skin',settings.MOOSHELL_DEFAULT_SKIN)

		examples = Pastie.objects.all_examples_by_groups()


		
		# TODO: join some js files for less requests
		js_libs = [
			reverse('mooshell_js', args=[moo]),
			reverse('mooshell_js', args=[settings.MOOTOOLS_MORE]),
			reverse('codemirror', args=['js/codemirror.js']),
			reverse('codemirror', args=['js/mirrorframe.js']),
			reverse("mooshell_js", args=["Sidebar.js"]),
			reverse('mooshell_js', args=['LayoutCM.js']),
			reverse("mooshell_js", args=["Actions.js"]),
			reverse("mooshell_js", args=["Resources.js"]),
			reverse("mooshell_js", args=["EditorCM.js"]),
			reverse("mooshell_js", args=["Settings.js"]),
		]
		c.update({
			'shell': shell,
			'external_resources': external_resources,
			'css_files': [reverse('mooshell_css', args=["%s.css" % skin])],
			'js_libs': js_libs,
			'examples': examples,
			'doctypes': doctypes,
			'title': title,
			'example_url': example_url,
			'disqus_url': disqus_url,
			'web_server': server,
			'skin': skin,
			'get_dependencies_url': reverse("_get_dependencies", 
									args=["lib_id"]).replace('lib_id','{lib_id}'),
			'get_library_versions_url': reverse("_get_library_versions", 
									args=["group_id"]).replace('group_id','{group_id}'),
		})
		#log_to_file('context generated')
		try:
			cache.set(key, c)
			#log_to_file('context saved in cache')
		except Exception, err:
			log_to_file(err.__str__())
			#log_to_file(c)

	if slug: 
		shellform = ShellForm(instance=c['shell'])
	else:
		shellform = ShellForm()
	c['shellform'] = shellform



	if slug and c['shell']: 
		pastie = c['shell'].pastie
		c['is_author'] = (pastie.author and req.user.is_authenticated() and pastie.author_id == req.user.id)

	return render_to_response('pastie_edit.html',c,
							context_instance=RequestContext(req))
	

def pastie_save(req, nosave=False, skin=None):
	"""
	retrieve shell from the form, save or display
	Fix dependency
	"""
	if req.method == 'POST':
		slug = req.POST.get('slug', None)
		if slug:
			" UPDATE - get the instance if slug provided "
			pastie = get_object_or_404(Pastie,slug=slug)
			#pastieform = PastieForm(req.POST, instance=pastieinstance)
		else:	
			" CREATE "
			pastie = Pastie()
			if not nosave:
				if req.user.is_authenticated():
					pastie.author = req.user 
				pastie.save()

		shellform = ShellForm(req.POST)
			
		if shellform.is_valid():
			
			" Instantiate shell data from the form "
			shell = shellform.save(commit=False)
			
			" Base64 decode "
			shell.code_js = base64.b64decode(shell.code_js)
			shell.code_html = base64.b64decode(shell.code_html)
			shell.code_css = base64.b64decode(shell.code_css)

			" Connect shell with pastie "
			shell.pastie = pastie
			
			# get javascript dependencies 
			dependency_ids = [int(dep[1]) for dep in req.POST.items() if dep[0].startswith('js_dependency')]
			dependencies = []
			for dep_id in dependency_ids:
				dep = JSDependency.objects.get(id=dep_id)
				dependencies.append(dep)

			# append external resources
			external_resources = []
			ext_ids = req.POST.get('add_external_resources', '').split(',')
			for ext_id in ext_ids:
				try:
					external_resources.append(ExternalResource.objects.get(id=int(ext_id)))
				except:
					pass

			if nosave:
				" return the pastie page only " 
				# no need to connect with pastie
				return pastie_display(req, None, shell, 
										dependencies=dependencies, 
										resources=external_resources, 
										skin=skin)

			" add user to shell if anyone logged in "
			if req.user.is_authenticated():
				shell.author = req.user

			shell.save()

			# add saved dependencies			
			for dep in dependencies:
				shell.js_dependency.add(dep)
		
			# add saved external resources
			for idx,ext in enumerate(external_resources):
				#we use intermediate model now
				#shell.external_resources.add(ext)
				ShellExternalResource.objects.create(
					shell=shell,
					resource=ext,
					ord=idx)

			" return json with pastie url "
			return HttpResponse(simplejson.dumps({
					'pastie_url_relative': shell.get_absolute_url()
					}),mimetype='application/javascript'
				)
		else: 
			error = "Shell form does not validate"
			for s in shellform:
				if hasattr(s, 'errors') and s.errors:
					error = error + str(s.__dict__) 
	else: 
		error = 'Please use POST request'
	
	# Report errors
	return HttpResponse(simplejson.dumps({'error':error}),
					mimetype='application/javascript'
	)


def get_pastie_display_key(req, slug, shell=None, dependencies=[], resources=[], skin=None):

	key = "%s:pastie_display" % settings.CACHE_MIDDLEWARE_KEY_PREFIX 
	key = "%s:%s" % (key, slug)
	if shell: key = "%s:%d" % (key, shell.id)
	if dependencies: 
		dependencies_str = ''
		for d in dependencies: dependencies_str = "%s,%d" % (dependecies_str, d.id)
		key = "%s:%s" % (key, dependencies_str)
	if resources:
		resources_str = ''
		for i in resources: resources_str = "%s:%d" % (resources_str, i.id)
	if skin: key = "%s:%s" % (key, skin)

	return key

def pastie_display(req, slug, shell=None, dependencies=[], resources=[], skin=None):
	" render the shell only "

	#key = get_pastie_display_key(req, slug, shell, dependencies, resources, skin)
	#if cache.get(key, None):
	#	return cache.get(key)

	#separate_log('-')
	#log_to_file('pastie_display - with shell %s' % shell)
	if not shell:
		#log_to_file('pastie_display - no shell')
		pastie = get_object_or_404(Pastie, slug=slug)
		shell = pastie.favourite
		" prepare dependencies if needed "
		dependencies = shell.js_dependency.all()
		resources = [res.resource for res in ShellExternalResource.objects.filter(shell__id=shell.id)]
		
	wrap = getattr(shell.js_lib, 'wrap_'+shell.js_wrap, None) if shell.js_wrap else None
	if not slug:
		" assign dependencies from request "
	
	if not skin: skin = req.GET.get('skin',settings.MOOSHELL_DEFAULT_SKIN)
	
	page = render_to_response('pastie_show.html', {
									'shell': shell,
									'dependencies': dependencies,
									'resources': resources,
									'resources_length': len(resources),
									'wrap': wrap,
									'skin': skin,
									'skin_css': reverse("mooshell_css", args=['result-%s.css' % skin])
							})
	#cache.set(key, page)
	return page
	

def get_embedded_key(req, slug, version=None, revision=0, author=None, tabs=None, skin=None):

	key = "%s:embedded" % settings.CACHE_MIDDLEWARE_KEY_PREFIX 
	key = "%s:%s" % (key, slug)
	if version: key = "%s:%s" % (key, version)
	if revision: key = "%s:%s" % (key, revision)
	if author: key = "%s:%s" % (key, author)
	#if req.user.is_authenticated(): key = "%s:auth-%s" % (key, req.user.username)

	return key

# consider better caching for that function.

def embedded(req, slug, version=None, revision=0, author=None, tabs=None, skin=None):
	" display embeddable version of the shell "

	#separate_log('-')
	#log_to_file('embedded')
	key = get_embedded_key(req, slug, version, revision, author, tabs, skin)
	if cache.get(key, None):
		 context = cache.get(key)
		 #log_to_file('embedded key %s' % key)
	else:
		pastie = get_object_or_404(Pastie,slug=slug)
		if version == None:
			shell = pastie.favourite
		else:
			user = get_object_or_404(User,username=author) if author else None
			shell = get_object_or_404(Shell, pastie__slug=slug, version=version, author=user)
		
		if not skin: skin = req.GET.get('skin', settings.MOOSHELL_DEFAULT_SKIN)
		if not tabs: tabs = req.GET.get('tabs', 'js,resources,html,css,result')
		
		try:
			server = settings.MOOSHELL_FORCE_SERVER
		except:
			server = 'http://%s' % req.META['SERVER_NAME']

		height = req.GET.get('height', None)
		tabs_order = tabs #req.GET.get('tabs',"js,html,css,result")
		tabs_order = tabs_order.split(',')
		
		if not shell.external_resources.all() and "resources" in tabs_order:
			tabs_order.remove("resources")
			external_resources = []
		else:
			external_resources = [res.resource for res in ShellExternalResource.objects.filter(shell__id=shell.id)]

		tabs = []
		for t in tabs_order:
			tab = {	'type': t,
							'title': settings.MOOSHELL_EMBEDDED_TITLES[t]
						}
			if not t in ["result", "resources"]:
				tab['code'] = getattr(shell,'code_'+t)
			tabs.append(tab)	
																
		context = { 
			'height': height,
			'server': server,
			'shell': shell,
			'external_resources': external_resources,
			'skin': skin,
			'tabs': tabs,
			'code_tabs': ['js', 'css', 'html'],
			'css_files': [
					reverse('mooshell_css', args=["embedded-%s.css" % skin])
					],
			'js_libs': [
					reverse('mooshell_js', args=[settings.MOOTOOLS_CORE]),
					reverse('mooshell_js', args=[settings.MOOTOOLS_MORE]),
					]
		}
		cache.set(key, context)
	page = render_to_response(	'embedded.html', 
								context, 
								context_instance=RequestContext(req))
	return page
		

def get_pastie_show_key(slug, version=None, author=None, obj=None):
	key = "%s:pastie_show" % settings.CACHE_MIDDLEWARE_KEY_PREFIX 
	key = "%s:%s" % (key, slug)
	if version: key = "%s:%s" % (key, version)
	if author: key = "%s:%s" % (key, author)
	if obj: key = "%s:%s" % (key, obj)
	return key

def delete_pastie_show_keys(slug, version=None, author=None):
	for obj in ['shell','resources','dependencies']:
		key = get_pastie_show_key(slug, version, author, obj)
		#log_to_file('checking %s' % key)
		if cache.has_key(key):
			#log_to_file('deleting %s' % key)
			cache.delete(key)
			#log_to_file('%s deleted' % key)

def pastie_show(req, slug, version=None, author=None, skin=None):
	" render the shell only "

	#separate_log('-')
	#log_to_file('pastie_show')
	key = get_pastie_show_key(slug, version, author, 'shell')
	#log_to_file(key)
	if cache.has_key(key):
		shell = cache.get(key)
		#log_to_file('shell read from cache %s' % key)
	else:
		pastie = get_object_or_404(Pastie, slug=slug)
		if version == None:
			shell = pastie.favourite
		else:
			user = get_object_or_404(User,username=author) if author else None
			shell = get_object_or_404(Shell, pastie__slug=slug, version=version, author=user)
		cache.set(key, shell)
		#log_to_file('pastie_show, shell saved in cache %s' % key)

	if not skin: skin = req.GET.get('skin', settings.MOOSHELL_DEFAULT_SKIN)

	key = get_pastie_show_key(slug, version, author, 'resources')
	if cache.has_key(key):
		resources = cache.get(key)
		#log_to_file('resources read from cache %s' % key)
	else:
		resources = [res.resource for res in ShellExternalResource.objects.filter(shell__id=shell.id)]
		cache.set(key, resources)
		#log_to_file('pastie_show, resources saved in cache %s' % key)

	key = get_pastie_show_key(slug, version, author, 'dependencies')
	if cache.has_key(key):
		dependencies = cache.get(key)
		#log_to_file('dependencies read from cache %s' % key)
	else:
		dependencies = shell.js_dependency.all()
		cache.set(key, dependencies)
		#log_to_file('pastie_show, dependencies saved in cache %s' % key )

	return pastie_display(req, slug, shell, 
						dependencies=dependencies, 
						resources=resources, skin=skin)


#TODO: remove if not used
@cache_page(CACHE_TIME)
def author_show_part(req, author, slug, part, version=0):
	return render_to_response('show_part.html', 
								{'content': getattr(shell, 'code_'+part)})


@cache_page(CACHE_TIME)
def show_part(req, slug, part, version=None, author=None):
	pastie = get_object_or_404(Pastie,slug=slug)
	if pastie.favourite and version == None:
		shell = pastie.favourite
	else:
		if version == None: 
			version=0
		user = get_object_or_404(User,username=author) if author else None
		shell = get_object_or_404(Shell, pastie__slug=slug, version=version, author=user)
	return render_to_response('show_part.html', 
								{'content': getattr(shell, 'code_'+part)})

def ajax_json_echo(req, delay=True):
	" echo GET and POST "
	if delay:
		time.sleep(random.uniform(1,3))
	c = {'get_response':{},'post_response':{}}
	for key, value in req.GET.items():
		c['get_response'].update({key: value})
	for key, value in req.POST.items():
		c['post_response'].update({key: value})
	return HttpResponse(simplejson.dumps(c),mimetype='application/javascript')


def ajax_html_echo(req, delay=True):
	if delay:
		time.sleep(random.uniform(1,3))
	t = req.POST.get('html','')
	return HttpResponse(t)


def ajax_xml_echo(req, delay=True):
	if delay:
		time.sleep(random.uniform(1,3))
	t = req.POST.get('xml','')
	return HttpResponse(t, mimetype='application/xml')


def ajax_json_response(req):
	response_string = req.POST.get('response_string','This is a sample string')	
	return HttpResponse(simplejson.dumps(
		{
			'string': response_string,
			'array': ['This','is',['an','array'],1,2,3],
			'object': {'key': 'value'}
		}),
		mimetype='application/javascript'
	)


def ajax_html_javascript_response(req):
	return HttpResponse("""<p>A sample paragraph</p>
<script type='text/javascript'>alert('sample alert');</script>""")


@cache_page(CACHE_TIME)
def serve_static(request, path, media='media', type=None):
	if path == 'favicon':
		path = 'favicon.ico'
	return base_serve_static(request, path, media, type)


@cache_page(CACHE_TIME)
def get_library_versions(request, group_id): 
	libraries = JSLibrary.objects.filter(library_group__id=group_id)
	c = {'libraries': [
			{
				'id': l.id, 
				'version': l.version, 
				'selected': l.selected, 
				'group_name': l.library_group.name,
				'active': l.active
			} for l in libraries 
		]
	}
	selected = [l for l in libraries if l.selected]
	if selected:
		selected = selected[0]
		c['dependencies'] = get_dependencies_dict(selected.id)
	return HttpResponse(simplejson.dumps(c),mimetype='application/javascript')


@cache_page(CACHE_TIME)
def get_dependencies(request, lib_id): 
	return HttpResponse(simplejson.dumps(get_dependencies_dict(lib_id)),mimetype='application/javascript')

@cache_page(CACHE_TIME)
def get_dependencies_dict(lib_id):
	dependencies = JSDependency.objects.filter(active=True,library__id=lib_id)
	return [{'id': d.id, 'name': d.name, 'selected': d.selected} for d in dependencies ]

def expire_path(r, path):
	path = '%s' % path
	expire_page(path)
	return HttpResponse(simplejson.dumps({'message':'path expired', 'path':path}),
						mimetype="application/javascript")
	
def make_favourite(req):
	shell_id = req.POST.get('shell_id')
	shell = Shell.objects.get(id=shell_id)

	if not req.user.is_authenticated() or req.user.id != shell.pastie.author.id:
		raise Http404

	shell.pastie.favourite = shell
	shell.pastie.save()
	
	#if settings.FORCE_SHOW_SERVER:
	#	from urllib2 import urlopen
	#	response = urlopen('%s%s' % (settings.FORCE_SHOW_SERVER, reverse('expire', args=[shell.pastie.get_absolute_url()])))

	separate_log('-')
	log_to_file('make favourite - deleting caches')
	delete_pastie_show_keys(shell.pastie.slug, author=shell.author)
	keys = [get_pastie_edit_key(req, shell.author, author=shell.pastie.slug),
			get_pastie_edit_key(req, shell.pastie.slug, author=shell.author, version=shell.version),
			get_embedded_key(req, shell.pastie.slug, author=shell.author)
			]
	for key in keys:
		log_to_file('checking %s' % key)
		if cache.has_key(key):
			log_to_file('deleting')
			cache.delete(key)
	#expire_page(shell.get_absolute_url())
	#expire_page(shell.get_show_url())
	#expire_page(shell.get_embedded_url())

	return HttpResponse(simplejson.dumps({'message':'saved as favourite', 'url':shell.pastie.get_absolute_url()}),
						mimetype="application/javascript")


SORT_CHOICES = {
	'alphabetical': 'favourite__title',
	'date': 'created_at',
	'framework': 'favourite__js_lib__library_group__name'
}
ORDER_CHOICES = {
	'desc': '-',
	'asc': ''
}

@cache_page(CACHE_TIME)
def api_get_users_pasties(req, author, method='json'):
	separate_log()
	start = int(req.GET.get('start',0))
	limit = start + int(req.GET.get('limit',10))
	framework = req.GET.get('framework', '')
	sort = None
	if SORT_CHOICES.has_key(req.GET.get('sort', False)):
		sort= SORT_CHOICES[req.GET['sort']]
		if ORDER_CHOICES.has_key(req.GET.get('order', False)):
			order = ORDER_CHOICES[req.GET['order']]
		else:
			order = ''
		order_by = '%s%s' % (order, sort)
	else:
		order_by = False
	
	callback = req.GET.get('jsoncallback', None)
	if not callback:
		callback = req.GET.get('callback', None)
	user = get_object_or_404(User, username=author)
	pasties_filter = Pastie.objects\
					.filter(author__username=author)
	if framework != '':
		pasties_filter = pasties_filter\
					.filter(favourite__js_lib__library_group__name=framework)
	pasties_objects = pasties_filter\
					.exclude(favourite__title__isnull=True)\
					.exclude(favourite__title="")\
					.order_by('-created_at')
	if order_by:
		pasties_ordered = pasties_objects\
					.order_by(order_by)
	else:
		pasties_ordered = pasties_objects

	overall_result_set_count = len(pasties_objects)
	
	
	pasties = pasties_ordered[start:limit]
	
	try:
		server = settings.MOOSHELL_FORCE_SERVER
	except:
		server = 'http://%s' % req.META['SERVER_NAME']

	return render_to_response('api/pasties.%s' % method, 
								{
									'pasties': pasties, 
									'server': server, 
									'callback': callback,
									'overallResultSetCount': overall_result_set_count
								},
								context_instance=RequestContext(req),
								mimetype="application/javascript"
							)

def add_external_resource(req):
	url = req.POST.get('url')
	try:
		# check if url already in models
		resource = ExternalResource.objects.get(url=url)
		log_to_file('resource %s chosen' % resource.filename)
	except:
		# else create resource
		resource = ExternalResource(url=url)
		resource.save()
		log_to_file('resource %s created' % resource.filename)
	return HttpResponse(simplejson.dumps({
			'id': resource.id,
			'url': resource.url,
			'filename': resource.filename,
			'extension': resource.extension
		}),	mimetype="application/javascript")
