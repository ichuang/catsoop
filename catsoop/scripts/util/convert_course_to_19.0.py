import os
import re
import sys

section = r"((?:chapter)|(?:(?:sub){0,2}section)|ref)\*?"
section_star = r"<(?P<tag>%s)(?P<extras>[^>]*)>(?P<body>.*?)</(?P=tag)>" % section
section_star = re.compile(section_star, re.MULTILINE | re.DOTALL | re.IGNORECASE)


def _replacer(m):
    d = m.groupdict()
    return "<catsoop-%s%s>%s</catsoop-%s>" % (
        d["tag"],
        d["extras"],
        d["body"],
        d["tag"],
    )


for root, dirs, files in os.walk(sys.argv[1]):
    for skip in (".git", ".hg", "__STATIC__"):
        if skip in dirs:
            dirs.remove(skip)
    for f in files:
        if not any(f.endswith(i) for i in (".catsoop", ".py", ".md", ".xml")):
            continue
        fullname = os.path.join(root, f)
        try:
            with open(fullname, "r") as f:
                text = f.read()
        except:
            continue
        print(list(section_star.finditer(text)))
        text = re.sub(section_star, _replacer, text)
        text = re.sub(
            "csq_python_sandbox(?!_type|_interpreter)", "csq_python_sandbox", text
        ).replace("csq_python_interpreter", "csq_python_sandbox_interpreter")
        with open(fullname, "w") as f:
            f.write(text)
