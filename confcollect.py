"""Collection of routines to help you collect configuration from
different sources.

There are many different approaches/needs here; I've just added mine,
and I'd be happy to add modifications to support other's.

Can be used with an expando object like
``https://github.com/dsc/bunch`` or ``https://github.com/bcj/AttrDict``.


Syntax inspired by: https://github.com/uniphil/flask-environ.

A simpler, more manual approach:
    https://github.com/seanbrant/environ-maiden/blob/master/environ_maiden.py

Interesting, but potentially overengineered solution, no os.environ loading:
    https://github.com/duckworthd/configurati
"""

import os
import copy as copy_module


__all__ = ('copy', 'from_environ', 'from_object', 'from_module')


# Expose the shallow copy function
copy = copy_module.copy


def from_environ(*specs, **kwargs):
    """Return configuration variables from the OS environment.

    ``specs`` is supposed to work like this:

        from_environ(
            spec('PORT', convert=int)
        )

    You may also do:

        from_environ(by_defaults=existing_dict)

    In this case, it will essentially build a spec based on the existing
    dictionary. It'll see if a respective env key exists, and will do a
    conversion based on the existing value (if the value is an int, it'll
    try to convert the environ value to an int as well).

    TODO: Add support for prefix-based loading.
    """
    if specs:
        raise ValueError('*specs not yet implemented')
    by_defaults = kwargs.pop('by_defaults', None)

    result = {}
    for key, value in by_defaults.items():
        if key.upper() in os.environ:
            converter = {
                bool: convert.bool,
                int: convert.int,
                dict: convert.dict,
                list: convert.list,
                tuple: convert.tuple,
            }.get(type(value), lambda v: v)
            result[key] = converter(os.environ[key.upper()])
    return _postprocess(result, **kwargs)


def from_object(obj, upper_only=True, **kwargs):
    """Return all the properties of the object, by default filtering out
    those which are not uppercase, or which do not start with an
    alphanum char.
    """
    result = {}
    for name in dir(obj):
        if upper_only and not name.isupper():
            continue
        if name.startswith('_'):
            continue
        result[name] = getattr(obj, name)
    return _postprocess(result, **kwargs)


def from_module(module_name, silent=True, **kwargs):
    """Import the given module, return ``False`` if that fails, or
    raise the ImportError if ``sient`` is not set.

    Passes all other arguments to ``from_object``.
    """
    try:
        module = __import__(module_name)
    except ImportError:
        if not silent:
            raise
        else:
            return False
    else:
        return from_object(module, **kwargs)


def _postprocess(d, **kwargs):
    def ppk(k):
        if kwargs.get('key_lower', False):
            return k.lower()
        return k
    def ppv(v):
        return v
    return {ppk(k): ppv(v) for k, v in d.items()}


class convert(object):

    @staticmethod
    def bool(value):
        """
        Returns a boolean if you pass in a truthy or falsy value.

        Valid truth values are::
            1, '1', 'true', 't', 'True' and 'TRUE'

        Valid falsey valus are::
            0, '0', 'false', 'f', 'False' and 'FALSE'

        If the value is not truthy or falsey this will raise a
        value error.
        """
        if value in (True, False):
            return bool(value)

        if value in ('1', 'true', 't', 'True', 'TRUE'):
            return True

        if value in ('0', 'false', 'f', 'False', 'FALSE'):
            return False

        return bool(value)

    @staticmethod
    def int(value):
        """Make sure the value is an integer, or None."""
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def list(value):
        """Support comma-separated lists.
        """
        return value.split(',')

    @staticmethod
    def tuple(value):
        """Same rules as lists.
        """
        return tuple(convert.list(value))

    @staticmethod
    def dict(value):
        """Support dicts, format is::

            var1=foo,var2=bar
        """
        if not value:
            # '' is an empty dict, but ' ' will be {' ': ''}?
            return {}

        def split(a):
            parts = a.split('=', 1)
            if len(parts) == 1:
                return parts[0], ''
            else:
                return parts
        return dict(map(split, value.split(',')))
