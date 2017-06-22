#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import re


__version__ = '0.1'


try:
    next.__doc__
except NameError:
    def next(iterator):
        '''for python2.4 or earlyer'''
        return iterator.next()


def _list2dict(lst):
    name = lst[0] if isinstance(lst, list) else None
    dct = {}
    for kv in (lst[1:] if name is not None else lst):
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
        return tuple([ s.strip() for s in  _x ])
        # _m = re.compile('^ *([^ :][^:]+[^ :]) +: +([^ :][^:]+[^ :]) *$')
        # _x = _m.match(line)
        # return _x.groups() if _x else None

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

    def __init__(self, filename=None, raw=None, id=None):
        self.id = 1 if id is None else id
        if filename is None and id is None:
            if os.isatty(sys.stdin.fileno()):
                self.id = '1'
                self.content = self._get_output()
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
            self.content = self._get_output()
        #
        self.__result = self.parse_config(self.content)

    @staticmethod
    def _get_output(id):
        from subprocess import Popen, PIPE
        try:
            from subprocess import DEVNULL
        except ImportError:
            DEVNULL = open('/dev/null', 'w')
        _cmdline = 'arcconf getconfig %s' % id
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
            raise OSError({
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
        return _x.groups() if _x else None

    @staticmethod
    def parse_config(self, content):
        _result = []
        for line in content.splitlines():
            _result.append()
        pass


def main(*argv):
    import optparse
    parser = optparse.OptionParser(usage='%prog: [id]|--input=FILE')
    # parser.add_option('id')
    parser.add_option(
        '-i', '--input',
        dest='filename',
        metavar='FILE',
        help='Read arcconf message from file',
    )
    (options, args) = parser.parse_args(argv)
    _result = []
    if options.filenane is not None:
        if args:
            parser.error('Mutially expusive options <id> and <--input=FILE>')
        else:
            _result.append(ArcconfGetconfig(filename=options.filename))
    elif not args:
        _result.append(ArcconfGetconfig())
    else:
        for i in args:
            _result.append(ArcconfGetconfig(id=i))

    pass


if __name__ == '__main__':
    main(sys.argv)
