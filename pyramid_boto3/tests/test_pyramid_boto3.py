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
            'pyramid_boto3.sessions': 'default',
        })
        config.include('pyramid_services')
        config.include('pyramid_boto3')
        app = config.make_wsgi_app()
        env = prepare()
        request = env['request']
        session = request.find_service(name='pyramid_boto3.session.default')
        self.assertIsInstance(session, Session)

    def test_fat(self):
        import os
        from pyramid.config import Configurator
        from pyramid.scripting import prepare
        d = os.path.dirname(__file__)
        config = Configurator(settings={
            'pyramid_boto3.sessions': 'prof1 prof2',
            'pyramid_boto3.session.prof1.botocore.config_file':
                os.path.join(d, 'config_1.ini'),
            'pyramid_boto3.session.prof1.botocore.credentials_file':
                os.path.join(d, 'credentials_1.ini'),
            'pyramid_boto3.session.prof1.botocore.profile': 'prof1',
            'pyramid_boto3.session.prof2.botocore.config_file':
                os.path.join(d, 'config_1.ini'),
            'pyramid_boto3.session.prof2.botocore.credentials_file':
                os.path.join(d, 'credentials_1.ini'),
            'pyramid_boto3.session.prof2.botocore.profile': 'prof2',
            'pyramid_boto3.session.prof2.botocore.metadata_service_timeout':
                '1',
            'pyramid_boto3.configs': 'conf1',
            'pyramid_boto3.config.conf1.user_agent': 'myua',
            'pyramid_boto3.config.conf1.connect_timeout': '3',
            'pyramid_boto3.config.conf1.parameter_validation': 'no',
            'pyramid_boto3.config.conf1.s3.addressing_style': 'path',
            'pyramid_boto3.clients': 'filepot1',
            'pyramid_boto3.client.filepot1.session_name': 'prof1',
            'pyramid_boto3.client.filepot1.service_name': 's3',
            'pyramid_boto3.resources': 'filepot2',
            'pyramid_boto3.resource.filepot2.session_name': 'prof2',
            'pyramid_boto3.resource.filepot2.service_name': 's3',
            'pyramid_boto3.resource.filepot2.config_name': 'conf1',
        })
        config.include('pyramid_services')
        config.include('pyramid_boto3')
        app = config.make_wsgi_app()
        env = prepare()
        request = env['request']
        s3_client = request.find_service(name='pyramid_boto3.client.filepot1')
        self.assertEqual(s3_client._request_signer._credentials.access_key,
                         '__PROF1_KEY__')
        self.assertEqual(s3_client._request_signer._credentials.secret_key,
                         '__PROF1_SECRET__')
        self.assertEqual(s3_client.meta.region_name, 'us-west-1')
        s3_resource = request.find_service(
            name='pyramid_boto3.resource.filepot2'
        )
        self.assertEqual(
            s3_resource.meta.client._request_signer._credentials.access_key,
            '__PROF2_KEY__')
        self.assertEqual(
            s3_resource.meta.client._request_signer._credentials.secret_key,
            '__PROF2_SECRET__')
        self.assertEqual(s3_resource.meta.client.meta.region_name,
                         'ap-northeast-1')
