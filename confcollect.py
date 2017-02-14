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
try:
    from urllib import parse as urlparse
except ImportError:
    import urlparse


__all__ = ('copy', 'from_environ', 'from_object', 'from_module', 'spec')



class Skip(Exception):
    """If this is raised by a converter, it is as if the setting does
    not exist in the first place.
    """
    pass


# Expose the shallow copy function
copy = copy_module.copy


def get_convert_func_for_type(type):
    return {
        bool: convert.bool,
        int: convert.int,
        dict: convert.dict,
        list: convert.list,
        tuple: convert.tuple,
    }.get(type)


class spec(object):
    """Think of a spec conceptionally as a copy & transform operation.
    It reads from a source (usually the OS environment) and and then
    writes to the output configuration object.

    `spec('DEBUG', 'sys:debug')`
        Reads DEBUG from the source, writes it to a key `sys:debug`.

    `spec('DEBUG', ('runtime', 'debug'))`
        Reads DEBUG from the source, adds a key to the result dict
        like this: `{'runtime': {'debug': value}}`

    Args:
        read (str): Name to read from.
        write (str, tuple): Output key to write to. If not given, the
            same string as `read` is used. If a tuple is given, a
            nested dict is generated in the output.
        split_by (str): The value read is
        convert (callable): Function to convert the value read; takes
            a single argument, the value.
        type (type): Give a expected output type. The string-value
            read will be converted to this type. This is an alternative
            to providing a custom `convert` function.

    Returns:
        dict: All the keys found and converted.
    """
    def __init__(self, read, write=None, convert=None, type=None):
        self._read = read
        self._write = write
        if convert:
            self.convert = convert
        elif type:
            self.convert = get_convert_func_for_type(type)
        else:
            self.convert = None

    def read(self, source):
        if not self._read in source:
            raise IndexError(self._read)
        value = source[self._read]
        if self.convert:
            value = self.convert(value)
        return value

    def write(self, value):
        if self._write:
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

    def __repr__(self):
        return repr(self.__dict__)


def specs_from_dict(template_dict, nested_dicts=False, prefix=""):
    """Given a dictinary, create specs, and return them as a dict.

    The generated specs will read the upper-case values, and write
    the original dict values, automatically choosing a converter
    based on the type.

    By returning a dictionary, it means you can easily take what you
    need and customize other specs. To use the specs, pass them to
    :func:`from_environ` using ``specs_dict.values()``.

    Args:
        nested_dicts (bool): If any of the values is a dict that
            contains further dicts, multiple specs are generated for
            this key. For example, given the template
            ``{db: {host: 'localhost', port: 80}}``, two specs are
            generated: DB_HOST, and DB_PORT.

    Returns:
        dict: A dict of {key: spec()}. The key is the `read` value.
            A dict, rather than a list, is provided so you can more
            easily customize the auto-generated specs.
    """
    specs = {}
    for key, value in template_dict.items():
        if key.startswith('_'):
            # Igore those by default. The dict might be locals()!
            continue

        if nested_dicts and isinstance(value, dict):
            # Generate specs from this nested dict. For this nested
            # call, modify the prefix by adding the parent key to it.
            nested_specs = specs_from_dict(
                value,
                prefix="%s%s_" % (prefix, key.upper()),
                nested_dicts=True
            )
            # Modify the nested specs to write inside the nested key;
            # the _write target from the nested spec might either be
            # a simple string, or a tuple, if there was any further
            # recursive nesting.
            for s in nested_specs.values():
                if isinstance(s._write, tuple):
                    s._write = (key,) + s._write
                else:
                    s._write = (key, s._write)

            specs.update(nested_specs)
            continue

        env_key = "%s%s" % (prefix, key.upper())
        specs[env_key] = spec(env_key, write=key, type=type(value))
    return specs


def merge_dict(d1, d2):
    """Modifies d1 in-place to contain values from d2.  If any value
    in d1 is a dictionary (or dict-like), *and* the corresponding
    value in d2 is also a dictionary, then merge them in-place.
    """
    for k,v2 in d2.items():
        v1 = d1.get(k) # returns None if v1 has no value for this key
        if (isinstance(v1, dict) and
             isinstance(v2, dict)):
            merge_dict(v1, v2)
        else:
            d1[k] = v2


def from_environ(*speclist, **kwargs):
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
    nested_dicts = kwargs.pop('nested_dicts', None)
    specs = kwargs.pop('specs', [])
    if by_defaults:
        specs = specs_from_dict(
            by_defaults, nested_dicts=nested_dicts).values()

    result = {}
    for spec in (speclist or specs or []):
        try:
            value = spec.read(os.environ)
        except IndexError:
            continue
        except Skip:
            continue
        merge_dict(result, spec.write(value))
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
        # http://stackoverflow.com/a/6957437/15677
        import importlib
        module = importlib.import_module(module_name)
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


def parse_url(which):
    def converter(value):
        parsed = urlparse.urlparse(value)._asdict()
        if not parsed['netloc'] and parsed['path']:
            # urlparse assume path by default rather than url
            parsed.update({
                'netloc': parsed['path'],
                'path': ''
            })
        # urlparse does not separate the port
        if ':' in parsed['netloc']:
            host, port = parsed['netloc'].rsplit(':', 1)
            parsed.update({'host': host, 'port': port})
        else:
            parsed['port'] = None
            parsed['host'] = parsed['netloc']

        value = parsed[which]
        if value == None:
            # None values are like "not existant"
            raise Skip()
        return value
    return converter
