import os
import subprocess

from datetime import datetime

cs_long_name = "Documentation"

docs_loc = os.path.join(cs_data_root, "courses", cs_course, "docs")
cs_title = "Documentation | CAT-SOOP"

cs_top_menu = [
    {
        "text": "Navigation",
        "link": [
            {"link": "COURSE", "text": "CAT-SOOP Home"},
            {"link": "COURSE/docs", "text": "Docs Home"},
            {"link": "COURSE/docs/about", "text": "About"},
            {"link": "COURSE/docs/installing", "text": "Installing"},
            {"link": "COURSE/docs/authoring", "text": "Authoring"},
            {"link": "COURSE/docs/extending", "text": "Extending"},
            {"link": "COURSE/docs/contributing", "text": "Contributing"},
            {"link": "COURSE/docs/api?p=catsoop", "text": "API"},
        ],
    }
]


todo = """!!! warning: This Page Needs Attention
    Contributions to documentation are more than welcome!
    You can e-mail suggestions, questions, or other feedback to `catsoop-users@mit.edu`.
    """
