confcollect
-----------

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
