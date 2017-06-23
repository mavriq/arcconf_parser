#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re

__all__ = ['ArcconfParser', 'ArcconfGetconfig', ]


def _list2dict(lst):
    if isinstance(lst, list):
        name = lst[0]
        _tree = lst[1:]
    else:
        name = None
        _tree = lst
    # name = isinstance(lst, list) and lst[0] or None
    dct = {}
    for kv in _tree:
        if isinstance(kv, tuple):
            dct[kv[0]] = kv[1]
        else:
            _n, _d = _list2dict(kv)
            dct[_n] = _d
    return name, dct


class ArcconfParser(object):
    def __init__(self):
        self.__result = []
        self._last_spaces = -1
        self._stack = [{
            'spaces': self._last_spaces,
            'branch': self.__result,
        }]
        # _stack - стек элементов, в которые добавляются новые записи
        self._wasdash = False

    @staticmethod
    def is_multidash(line):
        return re.compile('^ *-').match(line)

    @staticmethod
    def lspace_count(line):
        '''return the number of spaces at begining of the line'''
        return re.compile('^( *)[^ ].*$').match(line).groups()[0].__len__()

    @staticmethod
    def get_k_v(line):
        _x = line.split(': ', 1)
        if _x.__len__() < 2:
            return
        return tuple([s.strip() for s in _x])

    def _crop_stack(self, i, leave_first=False):
        _new_stack = []
        for _x in self._stack:
            if _x['spaces'] < i:
                _new_stack.append(_x)
            elif _x['spaces'] == i and leave_first:
                _new_stack.append(_x)
                break
            else:
                break
        self._stack = _new_stack

    def _append_branch(self, spaces, branch):
        self._stack[-1]['branch'].append(branch)
        self._stack.append({
            'spaces': spaces,
            'branch': branch,
        })

    def _append_leaf(self, kv):
        self._stack[-1]['branch'].append(kv)

    def append(self, line):
        if not line:
            return
        _spaces = self.lspace_count(line)
        if self.is_multidash(line):
            self._wasdash = not self._wasdash
            self._last_spaces = _spaces
            return
        kv = self.get_k_v(line)
        if self._wasdash:
            # начинается заголовок нового списка элементов
            self._crop_stack(_spaces)
            self._append_branch(_spaces, [line.strip()])
            self._last_spaces = _spaces
            return
        if kv is None and _spaces == 0:
            # text like a ...
            # Logical device number \d
            self._crop_stack(_spaces, leave_first=(True))
            self._append_branch(_spaces, [line.strip()])
            self._last_spaces = _spaces
            return
        if kv is None:
            if _spaces < self._last_spaces:
                self._crop_stack(_spaces)
                self._append_branch(_spaces, [line.strip()])
                self._last_spaces = _spaces
            else:
                self._append_leaf((line.strip(), True))
                self._last_spaces = _spaces
        else:
            self._append_leaf(kv)
        return

    def get_result(self):
        return self.__result

    def get_as_dict(self):
        return _list2dict(['plug'] + self.__result)[1]


class ArcconfGetconfig(object):
    u'''
    Parses the output of the command
    arcconf getconfig <ID>
    '''

    CMDLINE = 'arcconf getconfig %s'

    class ArcconfException(Exception):
        pass

    def __init__(self, filename=None, raw=None, id=None):
        if id is None:
            self.id = 1
        else:
            self.id = id
        if filename is None and id is None:
            if os.isatty(sys.stdin.fileno()):
                self.id = '1'
                self.content = self._get_output(self.id)
            else:
                self.content = sys.stdin.read()
            pass
        elif filename:
            if filename == '-':
                self.content = sys.stdin.read()
            else:
                self.content = open(filename, 'rt').read()
        else:
            self.id = id
            self.content = self._get_output(self.id)
        #
        self._result = self.parse_config(self.content)

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

    @staticmethod
    def is_multidash(line):
        return re.compile('^ *-').match(line)

    @staticmethod
    def lspace_count(line):
        return re.compile('^( *)[^ ].*$').match(line).groups()[0].__len__()

    @staticmethod
    def get_k_v(line):
        _m = re.compile('^ *([^ :][^:]+[^ :]) +: +([^ :][^:]+[^ :]) *$')
        _x = _m.match(line)
        if _x:
            return _x.groups()
        else:
            return None

    @staticmethod
    def parse_config(content):
        _result = ArcconfParser()
        for line in content.splitlines():
            _result.append(line)
        return _result

    def out(self, jsn, dct):
        if dct is False:
            _result = self._result.get_result()
        else:
            _result = self._result.get_as_dict()
        if jsn is False:
            from pprint import pprint as out
        else:
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
        out(_result)


def main(argv):
    import optparse
    parser = optparse.OptionParser(
        usage='%prog: [id]|--input=FILE'
        ' --dict|--raw'
        ' --print|--json'
    )
    parser.add_option(
        '-i', '--input', dest='filename', metavar='FILE',
        help='Read arcconf message from file',
    )
    parser.add_option(
        '--dict', action='store_true', dest='dict',
        help='get result as dictionary',
    )
    parser.add_option(
        '--raw', action='store_false', dest='dict',
        help='get result raw',
    )
    parser.add_option(
        '--print', action='store_false', dest='json',
        help='print result as python internal structure',
    )
    parser.add_option(
        '--json', action='store_true', dest='json',
        help='print resula as json',
    )

    (options, args) = parser.parse_args(argv)
    _result = []
    try:
        if options.filename is not None:
            if args:
                parser.error('Mutially expusive options <id> and <--input=FILE>')
            else:
                _result.append(ArcconfGetconfig(filename=options.filename))
        elif not args:
            _result.append(ArcconfGetconfig())
        else:
            for i in args:
                _result.append(ArcconfGetconfig(id=i))

        for i in _result:
            i.out(jsn=options.json, dct=options.dict)
    except ArcconfGetconfig.ArcconfException:
        parser.error(sys.exc_info()[:2][1])


if __name__ == '__main__':
    main(sys.argv[1:])
