import os
import pytest
from confcollect import from_object, from_environ, spec, specs_from_dict


class TestFromObject:

    def test(self):
        class Module(object):
            pass
        m = Module()
        m.FOO = 1
        m.foo = 2
        m._FOO = 3
        m._foo = 4
        assert from_object(m) == {'FOO': 1}


@pytest.fixture
def environ(request):
    fake_env = {}
    real_env = os.environ
    os.environ = fake_env
    def reset():
        os.environ = real_env
    request.addfinalizer(reset)
    return fake_env



class TestFromEnviron:

    def test_empty_list(self, environ):
        """Values of type 'list' return an empty list if the
        environment variable is empty.
        """
        environ['FOO'] = ""
        assert from_environ(by_defaults={'foo': []}) == {'foo': []}

    def test_nested_dicts(self, environ):
        environ['DB_HOST'] = 'localhost'
        environ['DB_PORT'] = '333'
        assert from_environ(by_defaults={'db': {'host': '', 'port': 80}},
            nested_dicts=True) == {'db': {'host': 'localhost', 'port': 333}}


class TestSpecsFromDict:

    def test_nested_dict(self):
        assert set(specs_from_dict({
            'db': {
                'host': 'test',
                'port': 111
            }
        }, nested_dicts=True).keys()) == set(['DB_HOST', 'DB_PORT'])


class TestSpecs:

    def test_read_with_type(self):
        assert spec('foo', type=int).read({'foo': '42'}) == 42

    def test_read_with_custom_convert(self):
        assert spec('foo', convert=lambda s: int(s) + 1).read({'foo': '42'}) == 43

    def test_write_dict(self):
        assert spec('foo', write=('a', 'b', 'c')).write('42') == {'a': {'b': {'c': '42'}}}