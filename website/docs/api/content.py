import ast
import inspect

module = cs_form.get("p", "catsoop")

cs_problem_spec = []

if not (module.startswith("catsoop.") or module == "catsoop"):
    module = "catsoop"


def _print(*args):
    cs_problem_spec.extend(str(i) for i in args)
    cs_problem_spec.append("\n")


broke = False
try:
    module = __import__(module, fromlist="dummy")
except:
    broke = True

if not broke:
    if module != "catsoop":
        cs_content_header += ": <code>%s</code>" % module.__name__

    if module.__file__.endswith("__init__.py"):
        # this is a package; list its contents
        if module.__doc__ is not None:
            _print(module.__doc__)
            _print()
        _print("## Members:")
        for child in sorted(dir(module)):
            if child.startswith("_"):
                continue
            child_mod = getattr(module, child)
            if not isinstance(child_mod, type(module)):
                continue
            docline = ((child_mod.__doc__ or "").strip() or "\n").splitlines()[0]
            _print("* [%s](CURRENT?p=%s): %s" % (child, child_mod.__name__, docline))
    else:
        with open(module.__file__) as f:
            tree = ast.parse(f.read())
        _docs = {}
        for ix, node in enumerate(tree.body[:-1]):
            nextnode = tree.body[ix + 1]
            if (
                isinstance(node, ast.Assign)
                and ix < len(tree.body) - 1
                and isinstance(nextnode, ast.Expr)
                and isinstance(nextnode.value, ast.Str)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                _docs[node.targets[0].id] = nextnode.value.s

        s = '<a href="%s/%s.py" target="_blank">View Source</a>' % (
            source_view_url_root,
            module.__name__.replace(".", "/"),
        )
        if module.__doc__ is not None:
            _print(module.__doc__)
            _print()
        _print(s)

        _print("## Members")
        for vname in sorted(dir(module)):
            if vname.startswith("_") or vname in getattr(module, "_nodoc", set()):
                continue

            x = getattr(module, vname)
            if type(x) == type(module):
                # this is a module, skip
                continue

            doc = x.__doc__
            if x.__doc__ == type(x).__doc__:
                doc = None
            if vname in _docs:
                doc = _docs[vname]

            try:
                lines, start = inspect.getsourcelines(x)
                l = ', <a href="%s/%s.py#L%s" target="_blank">lines %s-%s</a>' % (
                    source_view_url_root,
                    module.__name__.replace(".", "/"),
                    start,
                    start,
                    start + len(lines) - 1,
                )
            except:
                l = ""
            _print('<a name="%s"></a>' % vname)
            _print()
            _print(
                '* <font size="+2">**%s**</font> (`%s`%s)'
                % (module.__name__ + "." + vname, type(x).__name__, l)
            )

            if doc is not None:
                _print()
                _print()
                _print(
                    "\n".join(
                        "    %s" % (i[4:] if i.startswith("    ") else i)
                        for i in doc.strip().splitlines()
                    )
                )
            _print("<p>&nbsp;</p>")
            _print()

cs_problem_spec = [
    csm_language._md_format_string(globals(), "".join(cs_problem_spec), False)
]
