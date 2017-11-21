# -*- coding: utf-8 -*-

from docutils import nodes, utils
from sphinx.util.nodes import split_explicit_title

SOURCE_URI = 'https://github.com/jucacrispim/toxicbuild/blob/master/%s'


def source_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    has_t, title, target = split_explicit_title(text)
    title = utils.unescape(title)
    target = utils.unescape(target)
    refnode = nodes.reference(title, title, refuri=SOURCE_URI % target)
    return [refnode], []


def setup(app):
    """Install the plugin.

    :param app: Sphinx application context.
    """
    app.add_role('source', source_role)
    return
