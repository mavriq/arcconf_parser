#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
from HTMLParser import HTMLParser
from logging import warning


class Tag(object):
    INDENT = 2

    def __init__(self, tag, attrs=None, children=None):
        self.tag = tag
        if attrs is None:
            self.attrs = []
        else:
            self.attrs = attrs
        self.children = []
        if children is not None:
            for _child in children:
                if isinstance(_child, Tag):
                    pass
                elif isinstance(_child, (list, tuple)) and \
                        2 <= _child.__len__() <= 3:
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

    def __str__(self, offset=0):
        _args = ' '.join(['%s=%s' % (k, repr(v)) for k, v in self.attrs])
        _args = _args.replace('"', r'\"').replace("'", '"')
        _child_list = [
            c.__str__(offset=(offset + self.INDENT))
            for c in self.children]
        if not _child_list:
            _children = '/>'
        else:
            _children = ('>%(linesep)s%(children)s%(linesep)s%(offset)s'
                    '</%(tag)s>') % {
                'linesep': os.linesep,
                'children': os.linesep.join(_child_list),
                'offset': ' ' * offset,
                'tag': self.tag
            }
        #
        return '%(offset)s<%(tag)s %(args)s%(children)s' % {
            'offset': ' ' * offset,
            'tag': self.tag,
            'args': _args,
            'children': _children,
        }


class ArcconfGetsmartstatsException(Exception):
    pass


class ArcchonfGetsmartstatsParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._result = Tag('SMART')
        self._stack = [self._result]

    def handle_starttag(self, tag, attrs):
        _new = Tag(tag, attrs)
        self._stack[-1].append(_new)
        self._stack.append(_new)

    def handle_endtag(self, tag):
        _x = self._stack.pop()
        if _x.tag != tag:
            raise self.ArcconfGetsmartstatsException()

    def dict(self):
        return self._result.__dict__['children']

    def tree(self):
        return self._result.tree[2]

    def smart(self):
        _SMART = {}
        smartstats = [
            x for x in self._result.children if x.tag == 'smartstats'][0]
        _cntrlr = '%(devicevendor)s: %(devicename)s #%(serialnumber)s' % dict(
            smartstats.attrs)
        _SMART[_cntrlr] = {}
        for disk in smartstats.children:
            if disk.tag != 'physicaldrivesmartstats':
                warning('element is not "physicaldrivesmartstats": %s' % (
                    disk))
                continue
            _ID = '%(channel)s:%(id)s' % dict(disk.attrs)
            _SMART[_cntrlr][_ID] = dict(disk.attrs)
            for attr in disk.children:
                if attr.tag != 'attribute':
                    warning("element is not attribute: %s" % (attr))
                _d_attr = dict(attr.attrs)
                _d_attr_name = _d_attr.pop('name', None)
                if _d_attr_name is None:
                    warning("can not load name from %s" % (_d_attr))
                    continue
                _SMART[_cntrlr][_ID][_d_attr_name] = _d_attr
        return _SMART
