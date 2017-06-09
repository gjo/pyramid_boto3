# -*- coding: utf-8 -*-

import os
import unittest
from boto3.session import Session
from pyramid.config import Configurator
from pyramid.request import Request


class FunctionalTestCase(unittest.TestCase):

    def test_empty(self):
        config = Configurator(settings={})
        config.include('pyramid_services')
        config.include('pyramid_boto3')
        app = config.make_wsgi_app()
        del app

    def test_thin(self):
        config = Configurator(settings={
            'boto3.sessions': 'default',
        })
        config.include('pyramid_services')
        config.include('pyramid_boto3')

        v = {'session': None}

        def aview(request):
            v['session'] = request.find_service(name='boto3.session.default')
            return 'OK'

        config.add_view(aview, route_name='root', renderer='json')
        config.add_route('root', pattern='/')
        app = config.make_wsgi_app()
        request = Request.blank('/')
        response = request.get_response(app)
        self.assertEqual(response.json_body, 'OK')
        self.assertIsInstance(v['session'], Session)
        del app

    def test_fat(self):
        d = os.path.dirname(__file__)
        config = Configurator(settings={
            'boto3.sessions': 'prof1 prof2',
            'boto3.session.prof1.core.config_file':
                os.path.join(d, 'config_1.ini'),
            'boto3.session.prof1.core.credentials_file':
                os.path.join(d, 'credentials_1.ini'),
            'boto3.session.prof1.core.profile': 'prof1',
            'boto3.session.prof2.core.config_file':
                os.path.join(d, 'config_1.ini'),
            'boto3.session.prof2.core.credentials_file':
                os.path.join(d, 'credentials_1.ini'),
            'boto3.session.prof2.core.profile': 'prof2',
            'boto3.session.prof2.core.metadata_service_timeout': '1',
            'boto3.configs': 'conf1',
            'boto3.config.conf1.user_agent': 'myua',
            'boto3.config.conf1.connect_timeout': '3',
            'boto3.config.conf1.parameter_validation': 'no',
            'boto3.config.conf1.s3.addressing_style': 'path',
            'boto3.clients': 'filepot1',
            'boto3.client.filepot1.session': 'prof1',
            'boto3.client.filepot1.service_name': 's3',
            'boto3.resources': 'filepot2',
            'boto3.resource.filepot2.session': 'prof2',
            'boto3.resource.filepot2.service_name': 's3',
            'boto3.resource.filepot2.config': 'conf1',
        })
        config.include('pyramid_services')
        config.include('pyramid_boto3')

        v = {'s3_client': None, 's3_resource': None}

        def aview(request):
            v['s3_client'] = request.find_service(name='boto3.client.filepot1')
            v['s3_resource'] = \
                request.find_service(name='boto3.resource.filepot2')
            return 'OK'

        config.add_view(aview, route_name='root', renderer='json')
        config.add_route('root', pattern='/')
        app = config.make_wsgi_app()
        request = Request.blank('/')
        response = request.get_response(app)
        self.assertEqual(response.json_body, 'OK')
        s3_client = v['s3_client']
        s3_resource = v['s3_resource']
        self.assertEqual(s3_client._request_signer._credentials.access_key,
                         '__PROF1_KEY__')
        self.assertEqual(s3_client._request_signer._credentials.secret_key,
                         '__PROF1_SECRET__')
        self.assertEqual(s3_client.meta.region_name, 'us-west-1')
        self.assertEqual(
            s3_resource.meta.client._request_signer._credentials.access_key,
            '__PROF2_KEY__')
        self.assertEqual(
            s3_resource.meta.client._request_signer._credentials.secret_key,
            '__PROF2_SECRET__')
        self.assertEqual(s3_resource.meta.client.meta.region_name,
                         'ap-northeast-1')
        del app

    def assert_cache_enabled(self, cache_factory):
        settings = {
            'boto3.sessions': 'default',
            'boto3.clients': 's3',
            'boto3.client.s3.session': 'default',
            'boto3.client.s3.service_name': 's3',
            'boto3.resources': 's3',
            'boto3.resource.s3.session': 'default',
            'boto3.resource.s3.service_name': 's3',
            'boto3.cache_factory': cache_factory,
        }
        config = Configurator(settings=settings)
        config.include('pyramid_services')
        config.include('pyramid_boto3')

        def aview(request):
            session = request.find_service(name='boto3.session.default')
            s3cli = request.find_service(name='boto3.client.s3')
            s3res = request.find_service(name='boto3.resource.s3')
            return 'OK'

        config.add_view(aview, route_name='root', renderer='json')
        config.add_route('root', pattern='/')
        app = config.make_wsgi_app()
        request = Request.blank('/')
        response = request.get_response(app)
        self.assertEqual(response.json_body, 'OK')
        del app

    def test_cache_disabled(self):
        self.assert_cache_enabled('')

    def test_cache_threading_local(self):
        self.assert_cache_enabled('threading.local')

    # def test_cache_gevent_local_local(self):
    #     self.assert_cache_enabled('gevent.local.local')
