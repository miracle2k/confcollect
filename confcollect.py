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

__all__ = ('copy', 'from_environ', 'from_object', 'from_module', 'spec')


# Expose the shallow copy function
copy = copy_module.copy

class spec(object):
    """
    Think of a spec conceptionally as a copy & transform operation.
    It reads from a source (environment, primarily) and and then writes
    to the output configuration object.

    read
        Name to read from.
    write (default: read)
        Name to write to.
        If a tuple is given, it generates a nested dict.
    write_dict:
        write(value.split('.'))
    convert:
        Helpful transform function called between read and write.
    """
    def __init__(self, read, write=None, convert=None, write_dict=None):
        self._read = read
        self._write = write
        self._write_dict = write_dict
        self.convert = convert

    def read(self, source):
        if not self._read in source:
            raise IndexError(self._read)
        return source[self._read]

    def write(self, value):
        if self._write_dict:
            key = self._write_dict
            if isinstance(key, basestring):
                key = key.split('.')
        elif self._write:
            key = self._write
        else:
            key = self._read

        if isinstance(key, (tuple, list)):
            # Generate the nested dict.
            result = {key[-1]: value}
            for item in key[-2::-1]:
                result = {item: result}
            return result
        else:
            return {key: value}


def specs_from_dict(template_dict):
    """Given a dictinary, create specs, and return them as a dict.

    The generated specs will read the upper-case values, and write
    the original dict values, automatically choosing a converter
    based on the type.

    By returning a dictionary, it means you can easily take what you
    need and customize other specs. To use the specs, pass them to
    :func:`from_environ` using ``specs_dict.values()``.
    """
    specs = {}
    for key, value in template_dict.items():
        converter = {
            bool: convert.bool,
            int: convert.int,
            dict: convert.dict,
            list: convert.list,
            tuple: convert.tuple,
        }.get(type(value), lambda v: v)
        specs[key] = spec(key.upper(), convert=converter, write=key)
    return specs


def from_environ(*specs, **kwargs):
    """Return configuration variables from the OS environment.

    ``specs`` is supposed to work like this:

        from_environ(
            'port': spec('PORT', convert=int)
        )

    You may also do:

        from_environ(by_defaults=existing_dict)

    In this case, it will essentially build a spec based on the existing
    dictionary. It'll see if a respective env key exists, and will do a
    conversion based on the existing value (if the value is an int, it'll
    try to convert the environ value to an int as well).

    TODO: Add support for prefix-based loading.
    """
    by_defaults = kwargs.pop('by_defaults', None)
    if by_defaults:
        specs = specs_from_dict(by_defaults).values()

    result = {}
    for spec in specs:
        try:
            value = spec.read(os.environ)
        except IndexError:
            continue
        if spec.convert:
            value = spec.convert(value)
        result.update(spec.write(value))
    return _postprocess(result, **kwargs)


def from_object(obj, upper_only=True, **common_opts):
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
    return _postprocess(result, **common_opts)


def from_module(module_name, silent=True, **common_opts):
    """Import the given module, return enpty dict if that fails, or
    raise the ImportError if ``silent`` is not set.

    Passes all other arguments to ``from_object``.
    """
    try:
        module = __import__(module_name)
    except ImportError:
        if not silent:
            raise
        else:
            return {}
    else:
        return from_object(module, **common_opts)


def _postprocess(d, **common_opts):
    """Applies common options.

    key_lower
        Makes all keys in the collected configuration dict lower-case.
    """
    def process_key(k):
        if common_opts.get('key_lower', False):
            return k.lower()
        return k
    def process_value(v):
        return v
    return {process_key(k): process_value(v) for k, v in d.items()}


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
        if not value:
            return []
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
