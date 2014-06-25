from confcollect import from_object

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