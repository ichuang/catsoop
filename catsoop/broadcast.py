import os
import json
from google.cloud import firestore

if 0:
    cs_handler = 'raw_response'
    content_type = "application/json"
    response = json.dumps(get_msg())

def get_msg():
    db = firestore.Client()
    ref = db.collection("broadcast").document("msg")
    doc = ref.get()
    if doc.exists:
        return doc.to_dict()
    return {}

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
    
