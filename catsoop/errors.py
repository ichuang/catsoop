# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE

def clear_info(context, text):
    """
    Clear sensitive information from a string
    """
    text = text.replace(
        context.get('cs_fs_root', gb.cs_fs_root), '<CATSOOP ROOT>')
    text = text.replace(
        context.get('cs_data_root', gb.cs_data_root), '<DATA ROOT>')
    for i, j in context.get('cs_extra_clear', []):
        text = text.replace(i, j)
    return text


def error_message_content(context):
    """
    @return: An HTML-ready string containing an error message.
    """
    return html_format(clear_info(context, traceback.format_exc()))


def do_error_message(context, msg=None):
    """
    Display an error message

    @param context: The context associated with this request
    @return: A 3-tuple, as expected by L{render}
    """
    new = dict(context)
    loader.load_global_data(new)
    if 'cs_user_info' not in new:
        new['cs_user_info'] = {}
        new['cs_username'] = None
    if 'cs_handler' in new:
        del new['cs_handler']
    m = msg if msg is not None else error_message_content(context)
    new['cs_content'] = '<textarea rows=20 cols=110>ERROR:\n%s</textarea>' % m
    e = ': <font color="red">ERROR</font>'
    new['cs_header'] = new.get('cs_header', '') + e
    new['cs_content_header'] = 'An Error Occurred:'
    s, h, o = display_page(new)
    return ('500', 'Internal Server Error'), h, o

