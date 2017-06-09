.. -*- coding: utf-8 -*-

=============
pyramid_boto3
=============

Adapt ``boto3`` to ``pyramid`` with ``pyramid_services``


Install
=======

from PyPI::

  pip install pyramid_boto3


How to use
==========

In configuration phase, include ``pyramid_boto3`` after ``pyramid_services``::

  from pyramid.config import Configurator

  def main(global_config, **settings):
      config = Configurator(settings=settings)
      config.include('pyramid_services')
      config.include('pyramid_boto3')

      # Your configuration

      return config.make_wsgi_app()


In view or traversing, you can get predefined ``boto3``'s ``Client`` or
``Resource`` instances through ``request.find_service()``::

  @view_config()
  def some_view(request):
      client = request.find_service(name='boto3.client.filepot')
      client.list_buckets()


You need to define servie's name (ex/ ``'boto3.client.filepot'``) and
arguments in your config file::

  [app:main]

  # your-config

  boto3.cache_factory = threading.local
  boto3.sessions = mysession
  boto3.session.mysession.core.config_file = /path/to/aws/config.ini
  boto3.session.mysession.core.credentials_file = /path/to/aws/credentials.ini
  boto3.session.mysession.core.profile = prof1
  boto3.clients = filepot
  boto3.client.filepot.session = mysession
  boto3.client.filepot.service_name = s3


Configuration Keys
==================

+-----------------------------+-----------------------------------------------+
| boto3.                      | namespace prefix                              |
+-----------------------------+-----------------------------------------------+
| boto3.cache_factory         | full qualified callable name.                 |
|                             | default is ``threading.local``.               |
|                             | if you would like to disable, set blank       |
+-----------------------------+-----------------------------------------------+
| boto3.sessions              | list of session's names                       |
+-----------------------------+-----------------------------------------------+
| boto3.session.NAME.*        | See: ``boto3.session.Session``'s docs.        |
|                             | param ``botocore_session`` are created from   |
|                             | blow ``core.`` sub params.                    |
+-----------------------------+-----------------------------------------------+
| boto3.session.NAME.core.    | See: ``botocore.session.Session``'s docs.     |
+-----------------------------+-----------------------------------------------+
| boto3.configs               | list of client config's names                 |
+-----------------------------+-----------------------------------------------+
| boto3.config.NAME.*         | See: ``botocore.config.Config``'s docs.       |
+-----------------------------+-----------------------------------------------+
| boto3.config.NAME.s3.*      | See: ``s3`` parameter in                      |
|                             | ``botocore.config.Config``'s docs.            |
+-----------------------------+-----------------------------------------------+
| boto3.clients               | list of client's names                        |
+-----------------------------+-----------------------------------------------+
| boto3.client.NAME.session   | name of session to create client.             |
+-----------------------------+-----------------------------------------------+
| boto3.client.NAME.config    | (optional) name of config to create client.   |
+-----------------------------+-----------------------------------------------+
| boto3.client.NAME.*         | See: ``boto3.session.Session.client()``'s     |
|                             | docs.                                         |
+-----------------------------+-----------------------------------------------+
| boto3.resources             | list of resource's names.                     |
+-----------------------------+-----------------------------------------------+
| boto3.resource.NAME.session | name of session to create resource.           |
+-----------------------------+-----------------------------------------------+
| boto3.resource.NAME.config  | (optional) name of config to create resource. |
+-----------------------------+-----------------------------------------------+
| boto3.resource.NAME.*       | See: ``boto3.session.Session.resource()``'s   |
|                             | docs.                                         |
+-----------------------------+-----------------------------------------------+
