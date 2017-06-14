# -*- coding: utf-8 -*-

from boto3.session import Session
from botocore.config import Config
from botocore.session import Session as CoreSession
from pyramid.settings import asbool, aslist


__version__ = '0.2.1'


default_settings = {
    # 'cache_factory': '',
    # 'cache_factory': 'gevent.local.local',
    'cache_factory': 'threading.local',
}


def lstrip_settings(settings, prefix):
    prefix_len = len(prefix)
    ret = dict([(k[prefix_len:], v) for k, v in settings.items()
                if k.startswith(prefix) and v])
    return ret


def config_factory(settings):
    """
    :type settings: dict
    :rtype: botocore.config.Config
    """
    params = {}
    for k in ('region_name', 'signature_version', 'user_agent',
              'user_agent_extra'):
        if settings.get(k):
            params[k] = settings[k]
    for k in ('connect_timeout', 'read_timeout'):
        if settings.get(k):
            params[k] = int(settings[k])
    for k in ('parameter_validation',):
        if settings.get(k):
            params[k] = asbool(settings[k])
    s3 = {}
    for k in ('addressing_style',):
        lk = 's3.{}'.format(k)
        if settings.get(lk):
            s3[k] = settings[lk]
    if s3:
        params['s3'] = s3
    config = Config(**params)
    return config


def client_factory(session_name, client_name, settings, cache=None):
    """
    :type session_name: str
    :type client_name: str
    :type settings: dict
    :type cache: threading.local, gevent.local.local
    :rtype: (object, pyramid.request.Request)->
                boto3.resources.base.ResourceBase
    """
    def factory(context, request):
        """
        :type context: object
        :type request: pyramid.request.Request
        :rtype: botocore.client.BaseClient
        """
        client = None
        if cache is not None:
            client = getattr(cache, client_name, None)
        if client is None:
            session = request.find_service(name=session_name)
            client = session.client(**settings)
            if cache is not None:
                setattr(cache, client_name, client)
        return client

    return factory


def resource_factory(session_name, resource_name, settings, cache=None):
    """
    :type session_name: str
    :type resource_name: str
    :type settings: dict
    :type cache: threading.local, gevent.local.local
    :rtype: (object, pyramid.request.Request)->
                boto3.resources.base.ResourceBase
    """
    def factory(context, request):
        """
        :type context: object
        :type request: pyramid.request.Request
        :rtype: boto3.resources.base.ResourceBase
        """
        resource = None
        if cache is not None:
            resource = getattr(cache, resource_name, None)
        if resource is None:
            session = request.find_service(name=session_name)
            resource = session.resource(**settings)
            if cache is not None:
                setattr(cache, resource_name, resource)
        return resource

    return factory


def session_factory(session_name, settings, cache=None):
    """
    :type session_name: str
    :type settings: dict
    :type cache: threading.local, gevent.local.local
    :rtype: (object, pyramid.request.Request)-> boto3.Session
    """
    core_settings = lstrip_settings(settings, 'core.')
    if core_settings:
        settings = dict([(k, v) for k, v in settings.items()
                         if not k.startswith('core.')])

    def factory(context, request):
        """
        :type context: object
        :type request: pyramid.request.Request
        :rtype: boto3.Session
        """
        session = None
        if cache is not None:
            session = getattr(cache, session_name, None)
        if session is None:
            core_session = None
            if core_settings:
                core_session = CoreSession()
                for k, v in CoreSession.SESSION_VARIABLES.items():
                    if k in core_settings:
                        var = core_settings[k]
                        (ini_key, env_key, default, converter) = v
                        if converter:
                            var = converter(var)
                        core_session.set_config_variable(k, var)
            session = Session(botocore_session=core_session, **settings)
            if cache is not None:
                setattr(cache, session_name, session)
        return session

    return factory


def configure(config, prefix='boto3.'):
    """
    :type config: pyramid.config.Configurator
    :type prefix: str
    """
    settings = default_settings.copy()
    settings.update(lstrip_settings(config.get_settings(), prefix))

    cache = None
    cache_factory = config.maybe_dotted(settings.get('cache_factory'))
    if cache_factory:
        cache = cache_factory()

    session_map = {}
    for session_name in aslist(settings.get('sessions', '')):
        qsn = 'session.{}'.format(session_name)
        session_map[session_name] = fqsn = prefix + qsn
        settings_local = lstrip_settings(settings, qsn + '.')
        config.register_service_factory(
            session_factory(fqsn, settings_local, cache),
            name=fqsn,
        )

    config_map = {}
    for config_name in aslist(settings.get('configs', '')):
        qsn = 'config.{}'.format(config_name)
        settings_local = lstrip_settings(settings, qsn + '.')
        config_map[config_name] = config_factory(settings_local)

    for domain, domain_plural, factory in (
        ('client', 'clients', client_factory),
        ('resource', 'resources', resource_factory),
    ):
        for name in aslist(settings.get(domain_plural, '')):
            qsn = '{}.{}'.format(domain, name)
            fqsn = prefix + qsn
            settings_local = lstrip_settings(settings, qsn + '.')
            session_name = settings_local.pop('session')
            session_name = session_map[session_name]
            config_name = settings_local.pop('config', None)
            if config_name:
                settings_local['config'] = config_map[config_name]
            config.register_service_factory(
                factory(session_name, fqsn, settings_local, cache),
                name=fqsn,
            )


def includeme(config):
    """
    :type config: pyramid.config.Configurator
    """
    configure(config)
