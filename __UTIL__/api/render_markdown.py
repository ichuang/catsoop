import json

if 'source' in cs_form:
    try:
        sources = json.loads(cs_form['source'])
    except:
        sources = [cs_form['source']]
else:
    sources = []

cs_handler = 'raw_response'
content_type = 'application/json'

lang = csm_language
soup = csm_tools.bs4.BeautifulSoup

response = [csm_language._md_format_string(globals(), i, False) for i in sources]
response = json.dumps([str(lang.handle_math_tags(soup(i, 'html.parser')))
                       for ix, i in enumerate(response)])
