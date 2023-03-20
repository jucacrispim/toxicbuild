# -*- coding: utf-8 -*-

import os
import asyncio
import atexit
import inspect
from unittest.mock import (MagicMock, NonCallableMagicMock, FunctionTypes)
from unittest.mock import (_is_list, _callable, _instance_callable,
                           _set_signature, _check_signature, _is_magic,
                           _SpecState, _must_skip)


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'functional', 'data')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')


def async_test(f):

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(f(*args, **kwargs))

    return wrapper


def close_loop():
    try:
        asyncio.get_event_loop().close()
    except Exception:
        pass


atexit.register(close_loop)


class AsyncMagicMock(MagicMock):

    def __init__(self, *args, **kwargs):
        aiter_items = kwargs.pop('aiter_items', None)
        super().__init__(*args, **kwargs)
        self.aiter_items = aiter_items
        self._c = 0

    def __call__(self, *a, **kw):
        s = super().__call__(*a, **kw)

        async def ret():
            return s

        return ret()

    def __bool__(self):
        return True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, exc_type, exc_tb):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.aiter_items:
            try:
                waste_time = type(self)()
                await waste_time()
                v = self.aiter_items[self._c]
                self._c += 1
            except IndexError:
                self._c = 0
                raise StopAsyncIteration
            return v


def create_autospec(spec, spec_set=False, instance=False, mock_cls=MagicMock,
                    _parent=None, _name=None, **kwargs):
    """Create a mock object using another object as a spec. Attributes on the
    mock will use the corresponding attribute on the `spec` object as their
    spec.

    Functions or methods being mocked will have their arguments checked
    to check that they are called with the correct signature.

    If `spec_set` is True then attempting to set attributes that don't exist
    on the spec object will raise an `AttributeError`.

    `mock_cls` is the class used to create the mock. Defaults to MagicMock

    If a class is used as a spec then the return value of the mock (the
    instance of the class) will have the same spec. You can use a class as the
    spec for an instance object by passing `instance=True`. The returned mock
    will only be callable if instances of the mock are callable.

    `create_autospec` also takes arbitrary keyword arguments that are passed to
    the constructor of the created mock."""

    # copy from the py35 unittest.mock.create_autospec to includ the mock_cls
    # argument.

    if _is_list(spec):
        # can't pass a list instance to the mock constructor as it will be
        # interpreted as a list of strings
        spec = type(spec)

    is_type = isinstance(spec, type)

    _kwargs = {'spec': spec}
    if spec_set:
        _kwargs = {'spec_set': spec}
    elif spec is None:
        # None we mock with a normal mock without a spec
        _kwargs = {}
    if _kwargs and instance:
        _kwargs['_spec_as_instance'] = True

    _kwargs.update(kwargs)

    Klass = mock_cls
    if inspect.isdatadescriptor(spec):
        # descriptors don't have a spec
        # because we don't know what type they return
        _kwargs = {}
    elif not _callable(spec):
        Klass = NonCallableMagicMock
    elif is_type and instance and not _instance_callable(spec):
        Klass = NonCallableMagicMock

    _name = _kwargs.pop('name', _name)

    _new_name = _name
    if _parent is None:
        # for a top level object no _new_name should be set
        _new_name = ''

    mock = Klass(parent=_parent, _new_parent=_parent, _new_name=_new_name,
                 name=_name, **_kwargs)

    if isinstance(spec, FunctionTypes):
        # should only happen at the top level because we don't
        # recurse for functions
        mock = _set_signature(mock, spec)
    else:
        _check_signature(spec, mock, is_type, instance)

    if _parent is not None and not instance:
        _parent._mock_children[_name] = mock

    if is_type and not instance and 'return_value' not in kwargs:
        mock.return_value = create_autospec(spec, spec_set, instance=True,
                                            mock_cls=mock_cls,
                                            _name='()', _parent=mock)

    for entry in dir(spec):
        if _is_magic(entry):
            # MagicMock already does the useful magic methods for us
            continue

        # XXXX do we need a better way of getting attributes without
        # triggering code execution (?) Probably not - we need the actual
        # object to mock it so we would rather trigger a property than mock
        # the property descriptor. Likewise we want to mock out dynamically
        # provided attributes.
        # XXXX what about attributes that raise exceptions other than
        # AttributeError on being fetched?
        # we could be resilient against it, or catch and propagate the
        # exception when the attribute is fetched from the mock
        try:
            original = getattr(spec, entry)
        except AttributeError:
            continue

        kwargs = {'spec': original}
        if spec_set:
            kwargs = {'spec_set': original}

        if not isinstance(original, FunctionTypes):
            new = _SpecState(original, spec_set, mock, entry, instance)
            mock._mock_children[entry] = new
        else:
            parent = mock
            if isinstance(spec, FunctionTypes):
                parent = mock.mock

            skipfirst = _must_skip(spec, entry, is_type)
            kwargs['_eat_self'] = skipfirst
            new = mock_cls(parent=parent, name=entry, _new_name=entry,
                           _new_parent=parent,
                           **kwargs)
            mock._mock_children[entry] = new
            _check_signature(original, new, skipfirst=skipfirst)

        # so functions created with _set_signature become instance attributes,
        # *plus* their underlying mock exists in _mock_children of the parent
        # mock. Adding to _mock_children may be unnecessary where we are also
        # setting as an instance attribute?
        if isinstance(new, FunctionTypes):
            setattr(mock, entry, new)

    return mock
