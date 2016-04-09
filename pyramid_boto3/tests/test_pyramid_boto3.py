# -*- coding: utf-8 -*-

import unittest


class FunctionalTestCase(unittest.TestCase):

    def test_empty(self):
        from pyramid.config import Configurator
        from pyramid.scripting import prepare
        config = Configurator(settings={})
        config.include('pyramid_services')
        config.include('pyramid_boto3')
        app = config.make_wsgi_app()
        env = prepare()

    def test_session(self):
        from boto3.session import Session
        from pyramid.config import Configurator
        from pyramid.scripting import prepare
        config = Configurator(settings={
            'boto3.sessions': 'default',
        })
        config.include('pyramid_services')
        config.include('pyramid_boto3')
        app = config.make_wsgi_app()
        env = prepare()
        request = env['request']
        session = request.find_service(name='boto3.session.default')
        self.assertIsInstance(session, Session)

    def test_fat(self):
        import os
        from pyramid.config import Configurator
        from pyramid.scripting import prepare
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
        app = config.make_wsgi_app()
        env = prepare()
        request = env['request']
        s3_client = request.find_service(name='boto3.client.filepot1')
        self.assertEqual(s3_client._request_signer._credentials.access_key,
                         '__PROF1_KEY__')
        self.assertEqual(s3_client._request_signer._credentials.secret_key,
                         '__PROF1_SECRET__')
        self.assertEqual(s3_client.meta.region_name, 'us-west-1')
        s3_resource = request.find_service(name='boto3.resource.filepot2')
        self.assertEqual(
            s3_resource.meta.client._request_signer._credentials.access_key,
            '__PROF2_KEY__')
        self.assertEqual(
            s3_resource.meta.client._request_signer._credentials.secret_key,
            '__PROF2_SECRET__')
        self.assertEqual(s3_resource.meta.client.meta.region_name,
                         'ap-northeast-1')
