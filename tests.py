import os
import pytest
from confcollect import from_object, from_environ


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