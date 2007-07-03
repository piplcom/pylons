import warnings
from unittest import TestCase

from paste.wsgiwrappers import WSGIRequest
from paste.fixture import TestApp
from paste.registry import RegistryManager

import pylons
from pylons.util import ContextObj
from pylons.controllers import WSGIController, XMLRPCController

from __init__ import TestWSGIController, SetupCacheGlobal, ControllerWrap

class BasicWSGIController(WSGIController):
    def index(self):
        return pylons.Response('hello world')

    def yield_fun(self):
        def its():
            x = 0
            while x < 100:
                yield 'hi'
                x += 1
        return its()
    
    def strme(self):
        return "hi there"
    
    def header_check(self):
        pylons.response.headers['Content-Type'] = 'text/plain'
        return "Hello all!"

class FilteredWSGIController(WSGIController):
    def __init__(self):
        self.before = 0
        self.after = 0

    def __before__(self):
        self.before += 1

    def __after__(self):
        self.after += 1
        action = pylons.request.environ['pylons.routes_dict'].get('action')
        if action in ('after_response', 'after_string_response'):
            self.response.write(' from __after__')

    def index(self):
        return pylons.Response('hi all, before is %s' % self.before)

    def after_response(self):
        return pylons.Response('hi')

    def after_string_response(self):
        return 'hello'

class TestBasicWSGI(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        app = ControllerWrap(BasicWSGIController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron, setup_cache=False)
        app = RegistryManager(app)
        self.app = TestApp(app)
        
    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)

    def test_wsgi_call(self):
        resp = self.get_response()
        assert 'hello world' in resp
    
    def test_yield_wrapper(self):
        resp = self.get_response(action='yield_fun')
        assert 'hi' * 100 in resp

    def test_404(self):
        self.environ['paste.config']['global_conf']['debug'] = False
        self.environ['pylons.routes_dict']['action'] = 'notthere'
        resp = self.app.get('/', status=404)
        assert resp.status == 404
    
    def test_private_func(self):
        self.baseenviron['pylons.routes_dict']['action'] = '_private'
        resp = self.app.get('/', status=404)
        assert resp.status == 404
    
    def test_strme_func(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'strme'
        resp = self.app.get('/')
        assert "hi there" in resp
    
    def test_header_check(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'header_check'
        resp = self.app.get('/')
        assert "Hello all!" in resp
        assert resp.response.headers['Content-Type'] == 'text/plain'
        assert resp.header('Content-Type') == 'text/plain'

class TestFilteredWSGI(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        app = ControllerWrap(FilteredWSGIController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron, setup_cache=False)
        app = RegistryManager(app)
        self.app = TestApp(app)
        
    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)
    
    def test_before(self):
        resp = self.get_response(action='index')
        assert 'hi' in resp
        assert 'before is 1' in resp

    def test_after_response(self):
        resp = self.get_response(action='after_response')
        assert 'hi from __after__' in resp

    def test_after_string_response(self):
        resp = self.get_response(action='after_string_response')
        assert 'hello from __after__' in resp
