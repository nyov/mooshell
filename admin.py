from django.contrib import admin

from models import JSLibraryGroup, JSLibraryWrap, JSLibrary, JSDependency, Pastie, Shell, ExternalResource, DocType

class JSLibraryGroupAdmin(admin.ModelAdmin):
    pass
admin.site.register(JSLibraryGroup, JSLibraryGroupAdmin)


class JSLibraryWrapAdmin(admin.ModelAdmin):
    pass
admin.site.register(JSLibraryWrap, JSLibraryWrapAdmin)


class JSLibraryAdmin(admin.ModelAdmin):
    list_display = ('library_group', 'version', 'active')
admin.site.register(JSLibrary, JSLibraryAdmin)


class JSDependencyAdmin(admin.ModelAdmin):
    list_display = ('library', 'name', 'active')
admin.site.register(JSDependency, JSDependencyAdmin)


class PastieAdmin(admin.ModelAdmin):
    search_fields = ['slug', 'author__username', 'favourite__js_lib__library_group__name']

    list_display = ('get_title', 'slug', 'author', 'example')
    list_display_links = ('get_title', 'slug')
    fieldsets = (
        (None, {
            'fields': ('slug', 'author', 'example')
        }),
    )
admin.site.register(Pastie, PastieAdmin)


class ShellAdmin(admin.ModelAdmin):
    search_fields = ['pastie__slug', 'author__username', 'description', 'code_css', 'code_html', 'code_js']
    list_display = ('title', 'get_slug', 'version', 'displayed', 'created_at')
    list_display_links = ('title', 'get_slug', 'version')

admin.site.register(Shell, ShellAdmin)


class ExternalResourceAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalResource, ExternalResourceAdmin)

class DocTypeAdmin(admin.ModelAdmin):
    pass
admin.site.register(DocType, DocTypeAdmin)

