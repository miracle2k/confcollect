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
------------

You would do something like this in your ``settings.py`` file::

    import confcollect, sys
    _my = sys.modules[__name__]

    _my.__dict__.update(confcollect.from_module('myproject.config', silent=False))
    _my.__dict__.update(confcollect.from_environ(by_defaults=_my.__dict__))