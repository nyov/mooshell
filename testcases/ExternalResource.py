from django.db import IntegrityError

from mooshell.models import ExternalResource
from mooshell.testcases.base import *

JS_FILENAME = 'some.js'

class ExternalResourceTest(MooshellBaseTestCase):

    def test_get(self):
        resource = ExternalResource.objects.get(url=TEST_EXTERNAL_URL_JS)
        self.failUnless(resource)
        self.assertEqual(resource.url, self.external_js.url)


    def test_unicode(self):
        self.assertEqual(str(self.external_js), JS_FILENAME)


    def test_unique(self):
        res = ExternalResource(url=TEST_EXTERNAL_URL_JS)
        self.assertRaises(IntegrityError, res.save)

    def test_extension(self):
        self.assertEqual(self.external_js.extension, 'js')
        self.assertEqual(self.external_css.extension, 'css')

    def test_adding_to_shell(self):
        self.assertEqual(len(self.shell.external_resources.all()), 0)
        ShellExternalResource.objects.create(shell=self.shell,
                                             resource=self.external_js,
                                             ord=0)
        self.failUnless(self.shell.external_resources.all())
        self.assertEqual(len(self.shell.external_resources.all()), 1)
        ShellExternalResource.objects.create(
                    shell=self.shell,
                    resource=self.external_css,
                    ord=1)
        self.assertEqual(len(self.shell.external_resources.all()), 2)
