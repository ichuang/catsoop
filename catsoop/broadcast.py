import os
import json
from catsoop import cslog

if 0:
    cs_handler = 'raw_response'
    content_type = "application/json"
    response = json.dumps(get_msg())

def get_msg():
    msg = cslog.read_log_file("broadcast_msg")
    return msg

def return_content():
    content = json.dumps(get_msg())
    typ = "application/json"
    headers = {"Content-type": typ, "Content-length": str(len(content))}
    return ("200", "OK"), headers, content
    
def return_static(path_info):
    prefix = os.environ.get('STATIC_URL_PREFIX')
    if prefix:
        url = '/'.join([prefix] + path_info[1:])
        content = ("307", "Temporary Redirect"), {"Location": url}, ""
        return content
    
