import random
import time
import base64

from django.shortcuts import render_to_response, get_object_or_404
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.core.urlresolvers import reverse
from django.utils import simplejson
from django.template import RequestContext, TemplateDoesNotExist
from django.contrib.auth.models import User
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from models import Pastie, Draft, Shell, JSLibrary, JSDependency, \
        ExternalResource, DocType, ShellExternalResource
from forms import ShellForm
from base.views import serve_static as base_serve_static
from base.utils import log_to_file, is_referer_allowed, delay
from mooshell.helpers import expire_page
from person.views import delete_dashboard_keys


CACHE_TIME = settings.CACHE_MIDDLEWARE_SECONDS
# sort choices for the fiddles JS API
SORT_CHOICES = {
    'alphabetical': 'favourite__title',
    'date': 'created_at',
    'framework': 'favourite__js_lib__library_group__name'
}
ORDER_CHOICES = {
    'desc': '-',
    'asc': ''
}


def get_pastie_edit_key(req, slug=None, version=None, revision=None,
                        author=None, skin=None):
    " creating a unique key for pastie_edit "

    key = "%s:pastie_edit" % settings.CACHE_MIDDLEWARE_KEY_PREFIX
    key = "%s:%s" % (key, slug) if slug else '%s:homepage' % key
    if version: key = "%s:%s" % (key, version)
    if revision: key = "%s:%d" % (key, revision)
    if author: key = "%s:%s" % (key, author)
    if skin: key = "%s:%s" % (key, skin)
    return key

def pastie_edit(req, slug=None, version=None, revision=None, author=None,
                skin=None):
    """
    display the edit shell page ( main display)
    """

    # build the cache key on the basis of url and user
    try:
        key = get_pastie_edit_key(req, slug, version, revision, author, skin)
    except Exception, err:
        log_to_file("ERROR: pastie_edit: "
                "generating key failed, vars: %s %s" % (
                    str([slug, version, revision, author]), str(err)))
        return HttpResponseNotAllowed("Error in generating the key")

    c = None
    to_log = "%s, slug: %s, version: %s, rev: %s, author: %s, skin: %s" % (
            key, slug, str(version), str(revision), str(author), str(skin))
    if cache.get(key, None):
        c = cache.get(key)

    if not c:
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
        user = None
        if slug:
            if skin:
                # important as {user}/{slug} is indistingushable from
                # {slug}/{skin} "
                try:
                    user = User.objects.get(username=slug)
                except:
                    pass
                else:
                    author = slug
                    slug = skin
                    skin = None

            pastie = get_object_or_404(Pastie, slug=slug)
            if version == None:
                # shell is the base version of the fiddle
                shell = pastie.favourite
                # validate the author exists if provided
                if not user:
                    user = get_object_or_404(User,
                                         username=author) if author else None
            else:
                if not user:
                    user = get_object_or_404(User,
                                         username=author) if author else None
                # if shell has an author, username has to be provided in url
                try:
                    shell = get_object_or_404(Shell, pastie__slug=slug,
                                          version=version, author=user)
                except MultipleObjectsReturned:
                    log_to_file('WARNING: pastie_edit: '
                            "Multiple shells: %s, %s" % (slug, version))
                    shell = list(Shell.objects.filter(pastie__slug=slug,
                                            version=version, author=user))[0]
                except:
                    raise

            external_resources = ShellExternalResource.objects.filter(
                shell__id=shell.id)

            example_url = ''.join([server, shell.get_absolute_url()])
            embedded_url = ''.join([server, shell.get_embedded_url()])
            disqus_url = ''.join([server,
                                  shell.pastie.favourite.get_absolute_url()])
            c['embedded_url'] = embedded_url
            title = shell.title \
                    if shell.title else settings.MOOSHELL_VIEW_TITLE
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
                                    args=["lib_id"]).replace(
                                        'lib_id','{lib_id}'),
            'get_library_versions_url': reverse("_get_library_versions",
                                    args=["group_id"]).replace(
                                        'group_id','{group_id}'),
        })
        try:
            cache.set(key, c)
        except Exception, err:
            log_to_file("WARNING: pastie_edit: "
                    "Saving cache failed, %s %s" % (
                        str(key), str(err)))

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
            try:
                shell.code_js = base64.b64decode(shell.code_js)
            except:
                pass
            try:
                shell.code_html = base64.b64decode(shell.code_html)
            except:
                pass
            try:
                shell.code_css = base64.b64decode(shell.code_css)
            except:
                pass

            " Connect shell with pastie "
            shell.pastie = pastie

            # get javascript dependencies
            dependency_ids = [int(dep[1]) for dep in req.POST.items() \
                              if dep[0].startswith('js_dependency')]
            dependencies = []
            for dep_id in dependency_ids:
                dep = JSDependency.objects.get(id=dep_id)
                dependencies.append(dep)
            dependencies = sorted(
                    dependencies, key=lambda d: d.ord, reverse=True)

            # append external resources
            external_resources = []
            ext_ids = req.POST.get('add_external_resources', '').split(',')
            for ext_id in ext_ids:
                if ext_id:
                    try:
                        external_resources.append(
                            ExternalResource.objects.get(id=int(ext_id)))
                    except Exception, err:
                        log_to_file('WARNING: pastie_save: '
                                'No external resource: %s %s' % (
                            req.POST.get('slug', '-'), ext_id))

            if nosave:
                # get page
                # no need to connect with pastie
                display_page = pastie_display(req, None, shell,
                                        dependencies=dependencies,
                                        resources=external_resources,
                                        skin=skin)
                # save the draft version
                if req.POST.get('username', False):
                    Draft.objects.make(req.POST.get('username'), display_page)

                return display_page

            # add user to shell if anyone logged in
            if req.user.is_authenticated():
                shell.author = req.user

            try:
                shell.save()
            except Exception, err:
                log_to_file("ERROR: pastie_edit: "
                        "saving shell failed %s" % str(err))
                return HttpResponseNotAllowed('Error saving shell')

            # add saved dependencies
            for dep in dependencies:
                shell.js_dependency.add(dep)

            # add saved external resources
            for idx,ext in enumerate(external_resources):
                ShellExternalResource.objects.create(
                    shell=shell,
                    resource=ext,
                    ord=idx)

            " return json with pastie url "
            return HttpResponse(simplejson.dumps({
                    'pastie_url_relative': shell.get_absolute_url()
                    }),mimetype='application/json'
                )
        else:
            error = "Shell form does not validate"
            for s in shellform:
                if hasattr(s, 'errors') and s.errors:
                    error = error + str(s.__dict__)
    else:
        error = 'Please use POST request'

    # Report errors
    return HttpResponse(simplejson.dumps({'error': error}),
                    mimetype='application/json')


@login_required
def pastie_delete(req, slug, confirmation=False):
    " deleting whole pastie "
    pastie = get_object_or_404(Pastie, slug=slug,
                               author__username=req.user.username)
    response = {'shells': pastie.shells.count(),
                'deleted': False,
                'title': pastie.favourite.get_name()
               }
    if confirmation:
        response['delete_url'] = pastie.get_delete_url()
    else:
        # delete shells
        for shell in list(pastie.shells.all()):
            # delete external resources
            for resource in list(shell.external_resources.all()):
                relation = ShellExternalResource.objects.get(
                    shell__pk=shell.pk, resource__pk=resource.pk)
                relation.delete()
            shell.delete()
        # delete pastie
        pastie.delete()
        response['deleted'] = True
        delete_dashboard_keys(req)

    return HttpResponse(simplejson.dumps(response),
                       mimetype='application/json')



@login_required
def display_draft(req):
    " return the draft as saved in user's files "
    try:
        return HttpResponse(req.user.draft.all()[0].html)
    except:
        return HttpResponse("<p>You've got no draft saved</p>"
                "<p>Please hit [Run] after logging in</p>"
                "<p><a href='http://jsfiddle.net/'>Home page</a></p>")


def pastie_display(req, slug, shell=None, dependencies=[], resources=[],
                   skin=None):
    " render the shell only "
    if not shell:
        pastie = get_object_or_404(Pastie, slug=slug)
        shell = pastie.favourite
        " prepare dependencies if needed "
        dependencies = shell.js_dependency.all()
        resources = [res.resource \
                     for res in ShellExternalResource.objects.filter(
                         shell__id=shell.id)]

    wrap = getattr(shell.js_lib, 'wrap_'+shell.js_wrap, None) \
            if shell.js_wrap else None

    if not skin:
        skin = req.GET.get('skin',settings.MOOSHELL_DEFAULT_SKIN)

    page = render_to_response('pastie_show.html', {
        'shell': shell,
        'dependencies': dependencies,
        'resources': resources,
        'resources_length': len(resources),
        'wrap': wrap,
        'skin': skin,
        'skin_css': reverse("mooshell_css", args=['result-%s.css' % skin])
    })
    return page


def get_embedded_key(req, slug, version=None, revision=0, author=None,
                     tabs=None, skin=None):

    key = "%s:embedded" % settings.CACHE_MIDDLEWARE_KEY_PREFIX
    key = "%s:%s" % (key, slug)
    if version: key = "%s:%s" % (key, version)
    if revision: key = "%s:%s" % (key, revision)
    if author: key = "%s:%s" % (key, author)
    if tabs: key = "%s:%s" % (key, tabs)
    if skin: key = "%s:%s" % (key, skin)

    return key

# consider better caching for that function.

def embedded(req, slug, version=None, revision=0, author=None, tabs=None,
             skin=None):
    " display embeddable version of the shell "

    allowed_tabs = ('js', 'html', 'css', 'result', 'resources')
    key = get_embedded_key(req, slug, version, revision, author, tabs, skin)

    context = None
    try:
        context = cache.get(key, None)
    except Exception:
        log_to_file('ERROR: embedded: Getting cache key failed: %s' % key)
        return HttpResponseNotAllowed('Error in cache')

    if not context:
        pastie = get_object_or_404(Pastie,slug=slug)
        if version == None:
            shell = pastie.favourite
        else:
            user = get_object_or_404(User,username=author) if author else None
            try:
                shell = Shell.objects.get(pastie__slug=slug, version=version,
                                      author=user)
            except MultipleObjectsReturned:
                # MySQL created some duplicate Shells
                shell = Shell.objects.filter(pastie__slug=slug,
                        version=version, author=user)[0]
            except ObjectDoesNotExist:
                raise Http404

        if not skin: skin = req.GET.get('skin', settings.MOOSHELL_DEFAULT_SKIN)
        if not tabs: tabs = req.GET.get('tabs', 'js,resources,html,css,result')

        server = settings.MOOSHELL_FORCE_SERVER \
                if hasattr(settings, 'MOOSHELL_FORCE_SERVER') \
                else 'http://%s' % req.META['SERVER_NAME']

        height = req.GET.get('height', None)
        tabs_order = tabs #req.GET.get('tabs',"js,html,css,result")
        tabs_order = tabs_order.split(',')

        if not shell.external_resources.all() and "resources" in tabs_order:
            tabs_order.remove("resources")
            external_resources = []
        else:
            resources = ShellExternalResource.objects.filter(
                shell__id=shell.id)
            external_resources = [res.resource for res in resources]

        if [x for x in tabs_order if x not in allowed_tabs]:
            return HttpResponseNotAllowed('Tab name not allowed')
        tabs = []
        for t in tabs_order:
            tab = { 'type': t,
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
    page = render_to_response('embedded.html',
                              context, context_instance=RequestContext(req))
    return page


def get_pastie_show_key(slug, version=None, author=None, obj=None):
    " returns key for the pastie show cache "
    key = "%s:pastie_show" % settings.CACHE_MIDDLEWARE_KEY_PREFIX
    key = "%s:%s" % (key, slug)
    if version: key = "%s:%s" % (key, version)
    if author: key = "%s:%s" % (key, author)
    if obj: key = "%s:%s" % (key, obj)
    return key


def delete_pastie_show_keys(slug, version=None, author=None):
    " deletes cache for the pastie show "
    keys = [get_pastie_show_key(slug, version, author, obj)
            for obj in ['shell','resources','dependencies']]
    keys_deleted = []
    for key in keys:
        if cache.has_key(key):
            keys_deleted.append(key)
            cache.delete(key)
    return keys_deleted

def pastie_show(req, slug, version=None, author=None, skin=None):
    " render the shell only "

    key = get_pastie_show_key(slug, version, author, 'shell')
    if cache.has_key(key):
        shell = cache.get(key)
    else:
        pastie = get_object_or_404(Pastie, slug=slug)
        if version == None:
            shell = pastie.favourite
        else:
            user = get_object_or_404(User,username=author) if author else None
            try:
                shell = get_object_or_404(Shell, pastie__slug=slug,
                                      version=version, author=user)
            except MultipleObjectsReturned:
                log_to_file('WARNING: pastie_show: '
                        'Multiple shells in pastie_show: %s, %s'
                            % (slug, version))
                shell = list(Shell.objects.filter(pastie__slug=slug,
                                        version=version, author=user))[0]
        cache.set(key, shell)

    if not skin: skin = req.GET.get('skin', settings.MOOSHELL_DEFAULT_SKIN)

    key = get_pastie_show_key(slug, version, author, 'resources')
    if cache.has_key(key):
        resources = cache.get(key)
    else:
        resources = [res.resource for res in \
                     ShellExternalResource.objects.filter(shell__id=shell.id)]
        cache.set(key, resources)

    key = get_pastie_show_key(slug, version, author, 'dependencies')
    if cache.has_key(key):
        dependencies = cache.get(key)
    else:
        dependencies = shell.js_dependency.all()
        cache.set(key, dependencies)

    return pastie_display(req, slug, shell,
                        dependencies=dependencies,
                        resources=resources, skin=skin)


@cache_page(CACHE_TIME)
def show_part(req, slug, part, version=None, author=None):
    " show only html css or js "
    pastie = get_object_or_404(Pastie,slug=slug)
    if pastie.favourite and version == None:
        shell = pastie.favourite
    else:
        if version == None:
            version=0
        user = get_object_or_404(User,username=author) if author else None
        shell = get_object_or_404(Shell, pastie__slug=slug, version=version,
                                  author=user)
    return render_to_response('show_part.html',
                                {'content': getattr(shell, 'code_'+part)})

def ajax_json_echo(req, delay=True):
    " OLD: echo GET and POST via JSON "
    if delay:
        time.sleep(random.uniform(1,3))
    c = {'get_response':{},'post_response':{}}
    for key, value in req.GET.items():
        c['get_response'].update({key: value})
    for key, value in req.POST.items():
        c['post_response'].update({key: value})
    return HttpResponse(simplejson.dumps(c),mimetype='application/json')


def ajax_html_echo(req, delay=True):
    " OLD: echo POST['html'] "
    if delay:
        time.sleep(random.uniform(1,3))
    t = req.POST.get('html','')
    return HttpResponse(t)


def ajax_xml_echo(req, delay=True):
    " OLD: echo POST['xml'] "
    if delay:
        time.sleep(random.uniform(1,3))
    t = req.POST.get('xml','')
    return HttpResponse(t, mimetype='application/xml')


def ajax_json_response(req):
    " OLD: standard JSON response "
    response_string = req.POST.get('response_string','This is a sample string')
    return HttpResponse(simplejson.dumps(
        {
            'string': response_string,
            'array': ['This','is',['an','array'],1,2,3],
            'object': {'key': 'value'}
        }),
        mimetype='application/json'
    )


def ajax_html_javascript_response(req):
    return HttpResponse("""<p>A sample paragraph</p>
<script type='text/javascript'>alert('sample alert');</script>""")


@cache_page(CACHE_TIME)
def serve_static(request, path, media='media', mimetype=None):
    " static pages are cached "
    return base_serve_static(request, path, media, mimetype)


@cache_page(CACHE_TIME)
def get_library_versions(request, group_id):
    " get library versions for current framework "
    try:
        group_id = int(group_id)
    except:
        log_to_file("ERROR: get_library_versions called with group_id:"
                " %s" % group_id)
        raise Http404
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
    return HttpResponse(simplejson.dumps(c),mimetype='application/json')


@cache_page(CACHE_TIME)
def get_dependencies(request, lib_id):
    " get dependencies for current library version "
    try:
        lib_id = int(lib_id)
    except:
        log_to_file("ERROR: get_dependencies called with lib_id: %s" % lib_id)
        raise Http404
    return HttpResponse(simplejson.dumps(get_dependencies_dict(lib_id)),
                        mimetype='application/json')

def get_dependencies_dict(lib_id):
    " returns a dict of dependencies for given library version "
    dependencies = JSDependency.objects.filter(active=True,library__id=lib_id)
    return [{'id': d.id,
             'name': d.name,
             'selected': d.selected} for d in dependencies]

#def expire_path(r, path):
#    " make the path expire - used with base version (I think) "
#    path = '%s' % path
#    expire_page(path)
#    return HttpResponse(simplejson.dumps(
#        {'message':'path expired', 'path':path}
#    ), mimetype="application/json")


def make_favourite(req):
    " set the base version "
    shell_id = req.POST.get('shell_id', None)
    if not shell_id:
        log_to_file('ERROR: make_favourite: no shell_id')
        return HttpResponse(
                simplejson.dumps({
                    'error': "<p>No shell id - if you think it is an error."
                    "please <a href='support@jsfiddle.net'>email us</a>.</p>"
                    "<p>The error has been logged</p>"}))

    try:
        shell = Shell.objects.get(id=shell_id)
    except ObjectDoesNotExist, err:
        log_to_file("ERROR: make_favourite: Shell doesn't exist "
                "%s" % str(shell_id))
        raise Http404

    if not req.user.is_authenticated() \
            or req.user.id != shell.pastie.author.id:
        log_to_file("ERROR: make_favourite: "
                    "User %s is not the author of the pastie %s" % (
                            str(req.user), shell.pastie.slug))
        return HttpResponseNotAllowed("You're not the author!")

    shell.pastie.favourite = shell
    shell.pastie.save()

    delete_pastie_show_keys(shell.pastie.slug, author=shell.author)
    keys = [get_pastie_edit_key(req, shell.author, author=shell.pastie.slug),
            get_pastie_edit_key(req, shell.author, skin=shell.pastie.slug),
            get_pastie_edit_key(req, shell.pastie.slug, author=shell.author,
                                version=shell.version),
            get_pastie_edit_key(req, shell.pastie.slug, author=shell.author),
            get_embedded_key(req, shell.pastie.slug, author=shell.author)]
    keys_deleted = []
    for key in keys:
        if cache.has_key(key):
            cache.delete(key)
            keys_deleted.append(key)

    return HttpResponse(simplejson.dumps({
            'message': 'saved as favourite',
            'url': shell.pastie.get_absolute_url()
        }), mimetype="application/json")


@cache_page(CACHE_TIME)
def api_get_users_pasties(req, author, method='json'):
    " JS API returns user's fiddles "

    # receiving query parameters
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

    # jsoncallback is historical
    callback = req.GET.get('jsoncallback', None)
    # callback is a industry standard
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

    try:
        return render_to_response('api/pasties.%s' % method, {
                'pasties': pasties,
                'server': server,
                'callback': callback,
                'overallResultSetCount': overall_result_set_count
            },
            context_instance=RequestContext(req),
            mimetype="application/javascript")
    except TemplateDoesNotExist:
        log_to_file('WARNING: api_get_users_pasties: no such type: '
                '%s' % method)
        raise Http404()


def add_external_resource(req):
    " add external url "
    url = req.POST.get('url')
    if not url:
        return HttpResponseNotAllowed('Please provide url')
    try:
        # check if url already in models
        resource = ExternalResource.objects.get(url=url)
        #log_to_file('resource %s chosen' % resource.filename)
    except:
        # else create resource
        resource = ExternalResource(url=url)
        resource.save()
        #log_to_file('resource %s created' % resource.filename)

    return HttpResponse(simplejson.dumps({
            'id': resource.id,
            'url': resource.url,
            'filename': resource.filename,
            'extension': resource.extension
        }), mimetype="application/json")
