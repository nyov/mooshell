from django.db import models
from django.contrib.auth.models import User


class JSDependencyManager(models.Manager):
	def get_active(self, **kwargs):
		return self.get_query_set().filter(active=True,**kwargs)

class JSLibraryManager(models.Manager):
	def get_active(self, **kwargs):
		return self.get_query_set().filter(active=True,**kwargs)

class PastieManager(models.Manager):
	def all_examples(self):
		return self.get_query_set().filter(example=True)

	def all_examples_by_groups(self):
		examples = self.all_examples()
		libs = {}
		for ex in examples:
			group_name = ex.favourite.js_lib.library_group.name
			if not libs.has_key(group_name):
				libs[group_name] = []
			libs[group_name].append(ex)
		return libs
	
	def get_all_owned(self, user=None):
		return self.get_query_set().filter(author__id=user.id).order_by('-created_at')

	def get_public_owned(self, user=None):
		return self.get_query_set().exclude(favourite__title='').filter(favourite__private=False).filter(author__id=user.id).order_by('-created_at')


class DraftManager(models.Manager):
	def make(self, username, html):
		try:
			user = User.objects.get(username=username)
		except:
			return
		html = html._container[0]
		try:
			draft = self.get(author__username=user.username)
			draft.html = html
			draft.save()
		except:
			draft = self.create(author=user, html=html)

		return draft


class ShellManager(models.Manager):
	def all(self):
		public = self.get_query_set().filter(private=False)
		return public

	def all_available(self, user=None):
		public = self.get_query_set().filter(private=False)
		if user and user.is_authenticated():
			owned = self.get_query_set().filter(private=True, author__id=user.id)
			return public | owned
		return public

	def all_owned(self, user=None):
		return self.get_query_set().filter(private=True, author__id=user.id).order_by('-revision')

	def all_with_private(self):
		return super(ShellManager, self).all()
 
	def get_public_or_owned(self, **kwargs):
		try:
			return self.get_public(**kwargs)
		except:
			return self.get_owned(user, **kwargs)

	def get_public(self, **kwargs):
		return self.get_query_set().get(private=False, **kwargs)

	def get_owned(self, user, **kwargs):
		return self.get_query_set().get(private=True, author__id=user.id, **kwargs)

