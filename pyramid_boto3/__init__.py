# -*- coding: utf-8 -*-

import boto3_paste
from pyramid.config import aslist


__version__ = '0.1'


def lstrip_settings(settings, prefix):
    prefix_len = len(prefix)
    ret = dict([(k[prefix_len:], v) for k, v in settings.items()
                if k.startswith(prefix) and v])
    return ret


def client_factory(session_name, service_name, settings):
    """
    :type session_name: str
    :type service_name: str
    :type settings: dict
    :rtype: (object, pyramid.request.Request)->
                boto3.resources.base.ResourceBase
    """
    def factory(context, request):
        """
        :type context: object
        :type request: pyramid.request.Request
        :rtype: botocore.client.BaseClient
        """
        session = request.find_service(name=session_name)
        client = session.client(service_name, **settings)
        return client

    return factory


def resource_factory(session_name, service_name, settings):
    """
    :type session_name: str
    :type service_name: str
    :type settings: dict
    :rtype: (object, pyramid.request.Request)->
                boto3.resources.base.ResourceBase
    """
    def factory(context, request):
        """
        :type context: object
        :type request: pyramid.request.Request
        :rtype: boto3.resources.base.ResourceBase
        """
        session = request.find_service(name=session_name)
        resource = session.resource(service_name, **settings)
        return resource

    return factory


def configure(config, prefix='pyramid_boto3.'):
    """
    :type config: pyramid.config.Configurator
    :type prefix: str
    """
    settings = lstrip_settings(config.get_settings(), prefix)

    session_map = {}
    for session_name in aslist(settings.get('sessions', '')):
        session_map[session_name] = fqsn = prefix + 'session.' + session_name
        config.register_service(
            boto3_paste.session_from_config(
                settings,
                'session.{}.'.format(session_name),
            ),
            name=fqsn,
        )

    for domain, domain_plural, factory in (
        ('client', 'clients', client_factory),
        ('resource', 'resources', resource_factory),
    ):
        for name in aslist(settings.get(domain_plural, '')):
            settings_local = lstrip_settings(
                settings,
                '{}.{}.'.format(domain, name),
            )
            session_name = settings_local.pop('session_name')
            session_name = session_map[session_name]
            service_name = settings_local.pop('service_name')
            config.register_service_factory(
                factory(session_name, service_name, settings_local),
                name=prefix + domain + '.' + name,
            )


def includeme(config):
    """
    :type config: pyramid.config.Configurator
    """
    configure(config)
