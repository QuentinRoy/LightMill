# -*- coding: utf-8 -*-
"""
    jinja2htmlcompress
    ~~~~~~~~~~~~~~~~~~
    A Jinja2 extension that eliminates useless whitespace at template
    compilation time without extra overhead.
    :copyright: (c) 2014 by erthalion (9erthalion6@gmail.com).
    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import print_function
from builtins import zip
from builtins import range
from builtins import object
import re
from jinja2.ext import Extension
from jinja2.lexer import Token, describe_token
from jinja2 import TemplateSyntaxError


_tag_re = re.compile(r'(?:<(/?)([:a-zA-Z0-9_-]+)\s*|(>\s*))(?s)')
_ws_normalize_re = re.compile(r'[ \t\r\n]+')
_incomplete_class_re = re.compile(r'(^class|^.* class)="[^"]+$', re.DOTALL)
_incomplete_tag_re = re.compile(r'.*<[a-zA-Z]*$', re.DOTALL)
_closing_tag_re = re.compile(r'.*/[:a-zA-Z]*>$', re.DOTALL)
_opening_tag_re = re.compile(r'^<[:a-zA-Z]+.*', re.DOTALL)
_end_attr_re = re.compile(r'.*[:a-zA-Z0-9_-]*="[:a-zA-Z0-9-_]*"$', re.DOTALL)


class StreamProcessContext(object):

    def __init__(self, stream):
        self.stream = stream
        self.token = None
        self.stack = []

    def fail(self, message):
        raise TemplateSyntaxError(message, self.token.lineno,
                                  self.stream.name, self.stream.filename)


def _make_dict_from_listing(listing):
    rv = {}
    for keys, value in listing:
        for key in keys:
            rv[key] = value
    return rv


class HTMLCompress(Extension):
    isolated_elements = set(['style', 'noscript', 'textarea'])
    void_elements = set(['br', 'img', 'area', 'hr', 'param', 'input',
                         'embed', 'col'])
    block_elements = set(['div', 'p', 'form', 'ul', 'ol', 'li', 'table', 'tr',
                          'tbody', 'thead', 'tfoot', 'tr', 'td', 'th', 'dl',
                          'dt', 'dd', 'blockquote', 'h1', 'h2', 'h3', 'h4',
                          'h5', 'h6', 'pre'])
    breaking_rules = _make_dict_from_listing([
        (['p'], set(['#block'])),
        (['li'], set(['li'])),
        (['td', 'th'], set(['td', 'th', 'tr', 'tbody', 'thead', 'tfoot'])),
        (['tr'], set(['tr', 'tbody', 'thead', 'tfoot'])),
        (['thead', 'tbody', 'tfoot'], set(['thead', 'tbody', 'tfoot'])),
        (['dd', 'dt'], set(['dl', 'dt', 'dd']))
    ])

    def is_isolated(self, stack):
        for tag, value in reversed(stack):
            if (tag in self.isolated_elements
                    or (tag == "script" and "ng-template" not in value)):
                return True
        return False

    def is_breaking(self, tag, other_tag):
        breaking = self.breaking_rules.get(other_tag)
        return breaking and (
            tag in breaking or (
                '#block' in breaking and tag in self.block_elements))

    def enter_tag(self, tag, ctx):
        while ctx.stack and self.is_breaking(tag, ctx.stack[-1][0]):
            self.leave_tag(ctx.stack[-1][0], ctx)
        if tag not in self.void_elements:
            ctx.stack.append((tag, ctx.token.value))

    def leave_tag(self, tag, ctx):
        if not ctx.stack:
            ctx.fail('Tried to leave "%s" but something closed '
                     'it already' % tag)
        if tag == ctx.stack[-1][0]:
            ctx.stack.pop()
            return
        for idx, other_tag in enumerate(reversed(ctx.stack)):
            if other_tag == tag:
                for num in range(idx + 1):
                    ctx.stack.pop()
            elif not self.breaking_rules.get(other_tag):
                break

    def normalize(self, ctx):
        pos = 0
        token_buffer = []

        def write_data(token_value, normalize=True):
            if not token_value:
                return

            if normalize and not self.is_isolated(ctx.stack):
                token_value = _ws_normalize_re.sub(' ', token_value.strip())

            token_buffer.append(token_value)

        def validate(prev, value, next):
            if not value:
                return value

            space_before = False
            space_after = False

            # if it's the first token, check for
            # space between previous attributes
            if not prev and value and _end_attr_re.match(getattr(ctx, 'previous_value', None) or ""):
                space_before = True

            if not space_after and _incomplete_class_re.match(value):
                space_after = True

            if not space_after and _incomplete_tag_re.match(value):
                space_after = True

            if not space_before and (_closing_tag_re.match(prev or "") or prev == ">") and value[0] != "<":
                space_before = True

            if not space_after and (_opening_tag_re.match(next or "") or next == "<") and value[-1] != ">":
                space_after = True

            if space_before:
                value = " " + value

            if space_after:
                value += " "

            return value

        for match in _tag_re.finditer(ctx.token.value):
            closes, tag, sole = match.groups()
            preamble = ctx.token.value[pos:match.start()]
            write_data(preamble)
            if sole:
                write_data(sole)
            else:
                write_data(match.group(), normalize=False)
                (closes and self.leave_tag or self.enter_tag)(tag, ctx)
            pos = match.end()

        write_data(ctx.token.value[pos:])

        return u''.join([
            validate(prev, value, next)
            for prev, value, next in
            zip([None, ] + token_buffer[:-1],
                token_buffer, token_buffer[1:] + [None, ])
        ])

    def filter_stream(self, stream):
        ctx = StreamProcessContext(stream)
        ctx.previous_value = None
        skip = False

        for token in stream:
            if token.type == 'name' and token.value == u'trans':
                skip = True

            if token.type == 'name' and token.value == u'endtrans':
                skip = False

            if token.type != 'data' or skip:
                yield token
                continue

            ctx.token = token
            value = self.normalize(ctx)
            ctx.previous_value = value
            yield Token(token.lineno, 'data', value)


class SelectiveHTMLCompress(HTMLCompress):

    def filter_stream(self, stream):
        ctx = StreamProcessContext(stream)
        strip_depth = 0
        while True:
            if stream.current.type == 'block_begin':
                if stream.look().test('name:strip') or \
                   stream.look().test('name:endstrip'):
                    stream.skip()
                    if stream.current.value == 'strip':
                        strip_depth += 1
                    else:
                        strip_depth -= 1
                        if strip_depth < 0:
                            ctx.fail('Unexpected tag endstrip')
                    stream.skip()
                    if stream.current.type != 'block_end':
                        ctx.fail('expected end of block, got %s' %
                                 describe_token(stream.current))
                    stream.skip()
            if strip_depth > 0 and stream.current.type == 'data':
                ctx.token = stream.current
                value = self.normalize(ctx)
                yield Token(stream.current.lineno, 'data', value)
            else:
                yield stream.current
            next(stream)


def test():
    from jinja2 import Environment
    env = Environment(extensions=[HTMLCompress])
    tmpl = env.from_string('''
        <html>
          <head>
            <title>{{ title }}</title>
          </head>
          <script type=text/javascript>
            if (foo < 42) {
              document.write('Foo < Bar');
            }
          </script>
          <body>
            <li><a href="{{ href }}">{{ title }}</a><br>Test   Foo
            <li><a href="{{ href }}">{{ title }}</a><img src=test.png>
          </body>
        </html>
    ''')
    print(tmpl.render(title=42, href='index.html'))

    env = Environment(extensions=[SelectiveHTMLCompress])
    tmpl = env.from_string('''
        Normal   <span>  unchanged </span> stuff
        {% strip %}Stripped <span class=foo  >   test   </span>
        <a href="foo">  test </a> {{ foo }}
        Normal <stuff>   again {{ foo }}  </stuff>
        <p>
          Foo<br>Bar
          Baz
        <p>
          Moep    <span>Test</span>    Moep
        </p>
        {% endstrip %}
    ''')
    print(tmpl.render(foo=42))


if __name__ == '__main__':
    test()
