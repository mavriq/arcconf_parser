#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
from HTMLParser import HTMLParser
from logging import warning


__all__ = ['ArcchonfGetsmartstats']


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


class ArcchonfGetsmartstats(object):
    CMDLINE = 'arcconf getsmartstats %s'

    class ArcconfException(Exception):
        pass

    def __init__(self, filename=None, raw=None, id=None):
        if id is None:
            self.id = 1
        else:
            self.id = id
        if filename is None and raw is None and id is None:
            if os.isatty(sys.stdin.fileno()):
                self.id = '1'
                self.content = self._get_output(self.id)
            else:
                self.content = sys.stdin.read()
        elif filename:
            if filename == '-':
                self.content = sys.stdin.read()
            else:
                self.content = open(filename, 'rt').read()
        else:
            self.id = id
            self.content = self._get_output(self.id)
        #
        self._result = ArcchonfGetsmartstatsParser()
        self._result.feed(self.content)

    def _get_output(self, id):
        from subprocess import Popen, PIPE
        try:
            from subprocess import DEVNULL
        except ImportError:
            DEVNULL = open('/dev/null', 'w')
        _cmdline = self.CMDLINE % id
        _env = os.environ.copy()
        _env.update(LC_ALL='C', LANG='C', PATH=':'.join((
            os.environ.get('PATH', ':'),
            '/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin',
        )))
        _cmd = Popen(
            _cmdline,
            stdin=DEVNULL,
            stdout=PIPE,
            stderr=PIPE,
            shell=True,
            env=_env,
        )
        _x = _cmd.communicate()
        if _cmd.returncode != 0:
            raise self.ArcconfException(
                "Error on executing command %s" % {
                    'command': _cmdline,
                    'returncode': _cmd.returncode,
                    'stdout': _x[0],
                    'stderr': _x[1],
                })
        else:
            return _x[0].decode()

    def out(self, jsn, typ):
        if jsn is False:
            from pprint import pprint as out
        elif typ not in ('xml', None):
            try:
                try:
                    from simplejson import dumps
                except ImportError:
                    from json import dumps
            except ImportError:
                raise self.ArcconfException(
                    "Can't show like a JSON. Uou can use `--print` argument.")
            def out(x):
                print(dumps(x, indent=2))
        if typ in ('xml', None):
            if jsn:
                raise self.ArcconfException('format can not be xml and json')
            def out(x):
                print(x)
            _result = self._result._result
        elif typ == 'smart':
            _result = self._result.smart()
        elif typ == 'dict':
            _result = self._result.dict()
        elif typ == 'tree':
            _result = self._result.tree()
        out(_result)


def main(argv):
    import optparse
    parser = optparse.OptionParser(
        usage='%prog: [id]|--input=FILE'
        ' --print|--json'
        ' --type=[xml|smart|dict|tree]'
    )
    parser.add_option(
        '-i', '--input', dest='filename', metavar='FILE',
        help='Read arcconf message from file',
    )
    parser.add_option(
        '--print', action='store_false', dest='json',
        help='print result as python internal structure',
    )
    parser.add_option(
        '--json', action='store_true', dest='json',
        help='print resula as json',
    )
    parser.add_option(
        '--type', dest='type', metavar='TYPE', type='choice',
        choices=['xml', 'smart', 'dict', 'tree'],
        help='select a output type',
    )
    #
    (options, args) = parser.parse_args(argv)
    #
    _result = []
    try:
        if options.filename is not None:
            if args:
                parser.error('Mutially expusive options <id> and <--input=FILE>')
            else:
                _result.append(ArcchonfGetsmartstats(filename=options.filename))
        elif not args:
            _result.append(ArcchonfGetsmartstats())
        else:
            for i in args:
                _result.append(ArcchonfGetsmartstats(id=i))
        #
        for i in _result:
            i.out(jsn=options.json, typ=options.type)
    except ArcchonfGetsmartstats.ArcconfException:
        parser.error(sys.exc_info()[:2][1])


if __name__ == '__main__':
    main(sys.argv[1:])
