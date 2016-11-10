# -*- coding: utf-8 -*-

from boto3.session import Session
from boto3.resources.base import ServiceResource
from botocore.client import BaseClient
from botocore.config import Config
from botocore.session import Session as CoreSession
from pyramid.settings import asbool, aslist
from transaction.interfaces import IDataManagerSavepoint, ISavepointDataManager
from zope.interface import Interface, implementer


__version__ = '0.1'


class TransactionError(ValueError):
    pass


class IBoto3CallHook(Interface):

    def after_commit(callable, *args, **kwargs):
        pass

    def before_commit(callable, *args, **kwargs):
        pass

    def on_commit(callable, *args, **kwargs):
        pass


@implementer(IBoto3CallHook, ISavepointDataManager)
class Boto3DataManager(object):

    def __init__(self, tm=None):
        """
        :param tm: transaction.interfaces.ITransactionManager
        """
        if tm is None:
            import transaction
            self.transaction_manager = transaction.manager
        else:
            self.transaction_manager = tm
        self.txn = None
        self.tpc_phase = 0
        self.calls = []

    # IBoto3CallHook implementations

    def after_commit(self, callable_, *args, **kwargs):
        self._verify_call(callable_, *args, **kwargs)
        self._join()
        self.txn.addAfterCommitHook(callable_, args, kwargs)

    def before_commit(self, callable_, *args, **kwargs):
        self._verify_call(callable_, *args, **kwargs)
        self._join()
        self.txn.addBeforeCommitHook(callable_, args, kwargs)

    def on_commit(self, callable_, *args, **kwargs):
        self._verify_call(callable_, *args, **kwargs)
        self.calls.append((callable_, args, kwargs))
        self._join()

    # transaction.interfaces.IDataManager implementations

    def abort(self, txn):
        """
        :type txn: transaction.interfaces.ITransaction
        """
        if self.txn is None:
            raise TransactionError('Does not joined to a transaction')
        if self.txn is not txn:
            raise TransactionError('Called in a different transaction')
        if self.tpc_phase != 0:
            raise TransactionError('TPC is not started')

        self._clear()

    def tpc_begin(self, txn):
        """
        :type txn: transaction.interfaces.ITransaction
        """
        if self.txn is None:
            raise TransactionError('Does not joined to a transaction')
        if self.txn is not txn:
            raise TransactionError('Called in a different transaction')
        if self.tpc_phase != 0:
            raise TransactionError('TPC is already started')

        self.tpc_phase = 1

    def commit(self, txn):
        """
        :type txn: transaction.interfaces.ITransaction
        """
        if self.txn is None:
            raise TransactionError('Does not joined to a transaction')
        if self.txn is not txn:
            raise TransactionError('Called in a different transaction')
        if self.tpc_phase != 1:
            raise TransactionError('TPC is not first phase')

        pass  # exec calls on tpc_finish

    def tpc_vote(self, txn):
        """
        :type txn: transaction.interfaces.ITransaction
        """
        if self.txn is None:
            raise TransactionError('Does not joined to a transaction')
        if self.txn is not txn:
            raise TransactionError('Called in a different transaction')
        if self.tpc_phase != 1:
            raise TransactionError('TPC is not first phase')

        self.tpc_phase = 2

    def tpc_finish(self, txn):
        """
        :type txn: transaction.interfaces.ITransaction
        """
        if self.txn is None:
            raise TransactionError('Does not joined to a transaction')
        if self.txn is not txn:
            raise TransactionError('Called in a different transaction')
        if self.tpc_phase != 2:
            raise TransactionError('TPC is not second phase')

        self._exec_calls()
        self._clear()

    def tpc_abort(self, txn):
        """
        :type txn: transaction.interfaces.ITransaction
        """
        if self.txn is None:
            raise TransactionError('Does not joined to a transaction')
        if self.txn is not txn:
            raise TransactionError('Called in a different transaction')

        self._clear()

    def sortKey(self):
        """
        :rtype: str
        """
        return str(id(self))

    # transaction.interfaces.ISavepointDataManager implementations

    def savepoint(self):
        """
        :rtype: Boto3DataManagerSavepoint
        """
        if self.txn is None:
            raise TransactionError('Does not joined to transaction')
        return Boto3DataManagerSavepoint(self)

    # internal implementations

    def _join(self):
        if self.txn is None:
            self.txn = self.transaction_manager.get()
            self.txn.join(self)

    def _clear(self):
        self.txn = None
        self.tpc_phase = 0

    def _exec_calls(self):
        for callable, args, kwargs in self.calls:
            callable(*args, **kwargs)

    def _verify_call(self, callable_, *args, **kwargs):
        if hasattr(callable_, '__self__'):
            c = callable_.__self__
            if isinstance(c, BaseClient):
                if args:
                    raise ValueError('Invalid positional arguments')
                cm = c.meta
                api_name = cm.method_to_api_mapping[callable_.__name__]
                om = cm.service_model.operation_model(api_name)
                if om.has_streaming_input:
                    pass  # TODO: rewind support
                else:
                    ret = c._serializer.serialize_to_request(kwargs, om)
            elif isinstance(c, ServiceResource):
                pass  # TODO: Resource support


@implementer(IDataManagerSavepoint)
class Boto3DataManagerSavepoint(object):
    """
    Dummy savepoint
    """

    def __init__(self, dm):
        """
        :type dm: Boto3DataManager
        """
        self.data_manager = dm

    def rollback(self):
        pass


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


def client_factory(session_name, settings):
    """
    :type session_name: str
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
        client = session.client(**settings)
        return client

    return factory


def resource_factory(session_name, settings):
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
        resource = session.resource(**settings)
        return resource

    return factory


def session_factory(settings):
    """
    :type settings: dict
    :rtype: boto3.Session
    """
    core_settings = lstrip_settings(settings, 'core.')
    if core_settings:
        settings = dict([(k, v) for k, v in settings.items()
                         if not k.startswith('core.')])
        core_session = CoreSession()
        for k, v in CoreSession.SESSION_VARIABLES.items():
            if k in core_settings:
                var = core_settings[k]
                (ini_key, env_key, default, converter) = v
                if converter:
                    var = converter(var)
                core_session.set_config_variable(k, var)
        settings['botocore_session'] = core_session
    session = Session(**settings)
    return session


def configure(config, prefix='boto3.'):
    """
    :type config: pyramid.config.Configurator
    :type prefix: str
    """
    settings = lstrip_settings(config.get_settings(), prefix)

    session_map = {}
    for session_name in aslist(settings.get('sessions', '')):
        qsn = 'session.{}'.format(session_name)
        session_map[session_name] = fqsn = prefix + qsn
        settings_local = lstrip_settings(settings, qsn + '.')
        config.register_service(session_factory(settings_local), name=fqsn)

    config_map = {}
    for config_name in aslist(settings.get('configs', '')):
        settings_local = lstrip_settings(settings,
                                         'config.{}.'.format(config_name))
        config_map[config_name] = config_factory(settings_local)

    for domain, domain_plural, factory in (
        ('client', 'clients', client_factory),
        ('resource', 'resources', resource_factory),
    ):
        for name in aslist(settings.get(domain_plural, '')):
            settings_local = lstrip_settings(
                settings,
                '{}.{}.'.format(domain, name),
            )
            session_name = settings_local.pop('session')
            session_name = session_map[session_name]
            config_name = settings_local.pop('config', None)
            if config_name:
                settings_local['config'] = config_map[config_name]
            config.register_service_factory(
                factory(session_name, settings_local),
                name=prefix + domain + '.' + name,
            )

    config.register_service_factory(
        lambda context, request: Boto3DataManager(tm=request.tm),
        IBoto3CallHook,
    )


def includeme(config):
    """
    :type config: pyramid.config.Configurator
    """
    configure(config)
