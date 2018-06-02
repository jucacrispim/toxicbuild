# from motor_extensions.py

import inspect
from sphinx import addnodes
from sphinx.addnodes import (desc, desc_signature)
from sphinx.util.inspect import safe_getattr


# This is a place to store info while parsing, to be used before generating.
_parse_info = {}


def find_by_path(root, classes):
    if not classes:
        return [root]

    _class = classes[0]
    rv = []
    for child in root.children:
        if isinstance(child, _class):
            rv.extend(find_by_path(child, classes[1:]))

    return rv


def process_nodes(app, doctree):
    # looks for async methods and annotates it.

    for objnode in doctree.traverse(desc):
        if objnode['objtype'] in ('method', 'classmethod'):
            signature_node = find_by_path(objnode, [desc_signature])[0]
            name = '.'.join([
                signature_node['module'], signature_node['fullname']])

            obj__parse_info = _parse_info.get(name)
            if obj__parse_info:
                if obj__parse_info.get('is_async_method'):
                    coro_annotation = addnodes.desc_annotation(
                        'coroutine ', 'coroutine ',
                        classes=['coro-annotation'])
                    signature_node.insert(0, coro_annotation)


def get_coro_attr(cls, name, *defargs):
    """
    """

    attr = safe_getattr(cls, name)

    # Store some info for process_nodes()
    full_name = '%s.%s.%s' % (
        cls.__module__, cls.__name__, name)

    has_coroutine_annotation = getattr(attr, 'coroutine_annotation', False)
    is_async_method = inspect.iscoroutinefunction(attr)

    # attr.doc is set by statement like 'error = AsyncRead(doc="OBSOLETE")'.

    _parse_info[full_name] = {
        'is_async_method': is_async_method or has_coroutine_annotation,
    }

    return attr


def setup(app):
    app.add_autodoc_attrgetter(type, get_coro_attr)
    app.connect("doctree-read", process_nodes)
