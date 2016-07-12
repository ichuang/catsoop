/*
Language: Python
Category: common
*/

function(hljs) {
  var PROMPT = {
    className: 'meta',  begin: /^(>>>|\.\.\.) /
  };
  var STRING = {
    className: 'string',
    contains: [hljs.BACKSLASH_ESCAPE],
    variants: [
      {
        begin: /(u|b)?r?'''/, end: /'''/,
        contains: [PROMPT],
        relevance: 10
      },
      {
        begin: /(u|b)?r?"""/, end: /"""/,
        contains: [PROMPT],
        relevance: 10
      },
      {
        begin: /(u|r|ur)'/, end: /'/,
        relevance: 10
      },
      {
        begin: /(u|r|ur)"/, end: /"/,
        relevance: 10
      },
      {
        begin: /(b|br)'/, end: /'/
      },
      {
        begin: /(b|br)"/, end: /"/
      },
      hljs.APOS_STRING_MODE,
      hljs.QUOTE_STRING_MODE
    ]
  };
  var NUMBER = {
    className: 'number', relevance: 0,
    variants: [
      {begin: hljs.BINARY_NUMBER_RE + '[lLjJ]?'},
      {begin: '\\b(0o[0-7]+)[lLjJ]?'},
      {begin: hljs.C_NUMBER_RE + '[lLjJ]?'}
    ]
  };
  var PARAMS = {
    className: 'params',
    begin: /\(/, end: /\)/,
    contains: ['self', PROMPT, NUMBER, STRING]
  };
  return {
    aliases: ['py', 'gyp'],
    keywords: {
      keyword:
        'and elif is global as in if from raise for except finally print import pass return ' +
        'exec else break not with class assert yield try while continue del or def lambda ' +
        'async await nonlocal|10 None True False',
      built_in:
        'True EnvironmentError OSError None input property iter NotImplemented UnicodeError ' +
        'memoryview PendingDeprecationWarning NotADirectoryError map FileExistsError __debug__ ' +
        'IndexError UnicodeTranslateError zip bin ArithmeticError classmethod dict slice credits ' +
        'FloatingPointError BlockingIOError max vars bytes next __spec__ False __package__ ' +
        'TypeError open len MemoryError id __loader__ range UnicodeEncodeError EOFError pow ' +
        'Ellipsis ZeroDivisionError callable UnicodeDecodeError __import__ int ConnectionError ' +
        'enumerate tuple FutureWarning __name__ Exception min RecursionError issubclass all '
        'bytearray dir repr UserWarning chr BrokenPipeError license format reversed ImportError ' +
        'AttributeError any StopIteration getattr object hex BaseException exec staticmethod ' +
        'setattr sum BufferError ValueError list IsADirectoryError locals ChildProcessError ' +
        'OverflowError SystemExit print ascii oct KeyError divmod TimeoutError compile ' +
        'ConnectionRefusedError ProcessLookupError copyright NotImplementedError Warning ' +
        'ImportWarning IOError ord quit __doc__ UnboundLocalError isinstance hash round ' +
        'PermissionError set exit StopAsyncIteration ConnectionResetError ConnectionAbortedError ' +
        'filter SystemError UnicodeWarning IndentationError SyntaxError hasattr SyntaxWarning ' +
        'globals bool frozenset _ NameError float KeyboardInterrupt ResourceWarning AssertionError ' +
        'FileNotFoundError LookupError complex __build_class__ super TabError DeprecationWarning ' +
        'BytesWarning help eval GeneratorExit RuntimeError sorted ReferenceError type delattr ' +
        'RuntimeWarning str InterruptedError abs'
    },
    illegal: /(<\/|->|\?)/,
    contains: [
      PROMPT,
      NUMBER,
      STRING,
      hljs.HASH_COMMENT_MODE,
      {
        variants: [
          {className: 'function', beginKeywords: 'def', relevance: 10},
          {className: 'class', beginKeywords: 'class'}
        ],
        end: /:/,
        illegal: /[${=;\n,]/,
        contains: [
          hljs.UNDERSCORE_TITLE_MODE,
          PARAMS,
          {
            begin: /->/, endsWithParent: true,
            keywords: 'None'
          }
        ]
      },
      {
        className: 'meta',
        begin: /^[\t ]*@/, end: /$/
      },
      {
        begin: /\b(print|exec)\(/ // don’t highlight keywords-turned-functions in Python 3
      }
    ]
  };
}
