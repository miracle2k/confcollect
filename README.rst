===========
confcollect
===========

The idea is for you to do::

    app = SomeWsgiAppMaybe(__name__)
    app.config.update({
        'SOME_SERVICE_URL': 'http://localhost:4931'
    })

    app.config.update(confcollect.from_module('config'))
    app.config.update(confcollect.from_environ(by_defaults=app.config))

The last two lines are everything that is needed to support configuration via
a uppercase-style 'config.py' module and configuration via the environment
(say, to run on Heroku).

When reading from the environment, it automatically converts to the right
type based on the defaults that you have given. If you need more flexiblity,
``from_environ`` supports something called ``specs``.


Using Django
============

You would do something like this in your ``settings.py`` file::

    import confcollect, sys
    _my = sys.modules[__name__]

    _my.__dict__.update(confcollect.from_module('myproject.config', silent=False))
    _my.__dict__.update(confcollect.from_environ(by_defaults=_my.__dict__))


Complex settings
================

In Django, some settings are nested dicts. Take for example::


    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            'URL': 'http://127.0.0.1:9200/',
            'INDEX_NAME': 'haystack',
        }
    }


How do we read this from the environment?

The native way doesn't work, because ``by_defaults`` does only support simple,
but not nested dicts. Meaning while the following works::

    set USERS="michael=secret,peter=12345"
    >>> confcollect.from_environ(by_defaults={'users': {}})
    {'users': {'michael': 'secret', 'peter': 12345}}

There is no way to set ``USERS`` such that we can generate a nested dict.

One way to fix this is by targeting one of the nested dictionaries directly,
using a custom spec::

    set SEARCH="ENGINE=elastic,URL=http://127.0.0.1:9200/"
    >>> confcollect.from_environ(spec('SEARCH', convert="dict", write_dict='HAYSTACK_CONNECTIONS.default'))
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'elastic',
            'URL': 'http://127.0.0.1:9200/',
        }
    }

Putting multiple such values into a single environment variable can still be
not pretty. Tooption to change the behaviour of ``by_defaults`` to generate
multiple specs for a dict::

    set HAYSTACK_CONNECTIONS_DEFAULT_ENGINE="elastic"
    set HAYSTACK_CONNECTIONS_DEFAULT_URL"elastic"
    >>> confcollect.from_environ(by_defaults=DJANGO, nested_dicts=True)
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'elastic',
            'URL': 'http://127.0.0.1:9200/',
        }
    }


**(not yet supported)** We can write inside a dict::

     spec(read='SEARCH', convert=dict, write_dict='HAYSTACK_CONNECTIONS.default')


**(not yet supported)** We can read multiple values via regex::

    spec(read_prefix='SEARCH_(.*)_(.*)', write_dict='HAYSTACK_CONNECTIONS.{0}.{1}')
    # If there are dots in the names
    spec(read_prefix='SEARCH_(.*)_(.*)', write_dict=('HAYSTACK_CONNECTIONS', '{0}', '{1}'))


**(Support reading nested dicts)** set DB="default=(ENGINE=mysql,HOST=localhost)"


Derivative settings
===================

Imagine that your app has to settings, ``REDIS_HOST`` and ``REDIS_PORT``. But
your deployment setup provides a single ``REDIS_URL`` environment variable.

We can wire this up::

    set REDIS_URL="redis://localhost:4566/0"
    >>> spec('REDIS_URL', 'REDIS_HOST', convert=parse_url('netloc'))
    >>> spec('REDIS_URL', 'REDIS_PORT', parse_url('port'), )

Here we parse a different piece of information out of the url using the
``parse_url``helper.


**(not yet supported)**  Pulling all elements of the URL into variables:

    >>> spec('REDIS_URL', 'REDIS_{}', convert=parse_url)
    >>> spec('REDIS_URL', 'REDIS_INFO', convert=parse_url)  # REDIS_INFO would be dict


The other way around - taking multiple settings and making a url is also
sometimes necessary.


**(not yet supported)** This can be done using a regular format string::

    confcollect.spec('BROKER_[HOST|DB_NAME]', format="redis://{HOST}/{DB_NAME}", write="BROKER_URL")

**(not yet supported)** Or, the build_url() helper will take a dict and
smartly recognize identifiers for host, port etc.::

    spec('BROKER_(.*)', convert=build_url, write='BROKER_URL')
