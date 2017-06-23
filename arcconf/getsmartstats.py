#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
from HTMLParser import HTMLParser


class Tag(object):
    INDENT = 2
    def __init__(self, tag, attrs=(), children=[]):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        for _child in children:
            if isinstance(_child, Tag):
                pass
            elif isinstance(_child, (list, tuple)) and \
                    2 <= _child.__len__() <=3:
                _child = Tag(*child)
            self.append(_child)

    def append(self, child):
        assert isinstance(child, Tag)
        self.children.append(child)

    @property
    def tree(self):
        return (
            self.tag,
            self.attrs,
            [_x.tree for _x in self.children]
        )

    @property
    def __dict__(self):
        return {
            'tag': self.tag,
            'attrs': dict(self.attrs),
            'children': [_x.__dict__ for _x in self.children]
        }


class ArcconfGetsmartstatsException(Exception):
    pass


class ArcchonfGetsmartstatsParser(HTMLParser):
    def reset(self):
        # print(ArcchonfGetsmartstatsParser)
        HTMLParser.reset(self)
        self._result = Tag(None)
        self._stack = [self._result]

    def _push_stack(self, tag, attrs):
        _new = Tag(tag, attrs)
        self._stack[-1].append(_new)
        self._stack.append(_new)

    def _pop_stack(self, tag):
        _x = self._stack.pop()
        if _x.tag != tag:
            raise self.ArcconfGetsmartstatsException()

    def handle_starttag(self, tag, attrs):
        return self._push_stack(tag, attrs)

    def handle_endtag(self, tag):
        return self._pop_stack(tag)

    def dict(self):
        return self._result.__dict__['children']

    def tree(self):
        return self._result.tree[2]
