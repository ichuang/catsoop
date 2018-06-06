# This file is part of CAT-SOOP
# Copyright (c) 2011-2018 Adam Hartz <hz@mit.edu>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Methods for handling requests, or for routing them to the proper handlers
"""

import os
import cgi
import string
import hashlib
import colorsys
import mimetypes
import urllib.parse

from email.utils import formatdate

from . import auth
from . import time
from . import tutor
from . import loader
from . import errors
from . import session
from . import language
from . import base_context

_nodoc = {'CSFormatter', 'formatdate', 'dict_from_cgi_form'}


class CSFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        try:
            return super().get_value(key, args, kwargs)
        except (IndexError, KeyError):
            return ''


def redirect(location):
    '''
    Generate HTTP response that redirects the user to the specified location

    **Parameters:**

    * `location`: the location the user should be redirected to

    **Returns:** a 3-tuple `(response_code, headers, content)` as expected by
    `catsoop.wsgi.application`
    '''
    return ('302', 'Found'), {'Location': str(location)}, ''


def static_file_location(context, path):
    '''
    Given an "intermediate" URL, return the path to that file on disk.
    Used by `serve_static_file`.

    The given path is in CAT-SOOP's internal format, a list of strings.  The
    first string represents the course in question, or one of the following:

    * `__BASE__` to look in the CAT-SOOP source directory
    * `__QTYPE__` to look in a question type's directory
    * `__HANDLER__` to look in a handler's directory
    * `__PLUGIN__` to look in a plugin's directory

    Regardless of whether the first element is a course or one of the special
    values above, the function proceeds by working its way down the given
    directories (all elements but the last in the given list).  Upon arriving
    in that directory, it looks for a directory called `__MEDIA__` containing a
    file with the given name.

    **Parameters:**

    * `context`: the context associated with this request
    * `path`: a list of directory names, starting with the course

    **Returns:** a string containing the location of the requested file on
    disk.
    '''
    loc = ''
    rest = path[2:]
    if path[0] == '__BASE__':
        # serving from base
        loc = os.path.join(
            context.get('cs_fs_root', base_context.cs_fs_root), '__MEDIA__')
        rest = path[1:]
    elif path[0] == '__PLUGIN__':
        # serving from plugin
        course = context.get('cs_course', '')
        loc = os.path.join(
            context.get('cs_data_root', base_context.cs_data_root), 'courses',
            course, '__PLUGINS__', path[1], '__MEDIA__')
    elif path[0] == '__HANDLER__':
        # serving from handler
        loc = os.path.join(
            context.get('cs_fs_root', base_context.cs_fs_root), '__HANDLERS__',
            path[1], '__MEDIA__')
    elif path[0] == '__QTYPE__':
        # serving from qtype
        loc = os.path.join(
            context.get('cs_fs_root', base_context.cs_fs_root), '__QTYPES__',
            path[1], '__MEDIA__')
    elif path[0] == '__AUTH__':
        # serving from qtype
        loc = os.path.join(
            context.get('cs_fs_root', base_context.cs_fs_root), '__AUTH__',
            path[1], '__MEDIA__')
    else:
        # preprocess the path to prune out 'dots' and 'double-dots'
        course = path[0]
        path = path[1:]
        newpath = []
        for ix in range(len(path)):
            cur = path[ix]
            if cur == '.':
                pass
            elif cur == '..':
                newpath = newpath[:-1]
            else:
                dname = loader.get_directory_name(context, course, path[:ix],
                                                  cur)
                newpath.append(dname if dname is not None else cur)

        # trace up the path to find the lowest point that has a
        # __MEDIA__ directory
        basepath = os.path.join(
            context.get('cs_data_root', base_context.cs_data_root), 'courses',
            course)
        for ix in range(len(newpath) - 1, -1, -1):
            loc = os.path.join(*([basepath] + newpath[:ix] + ['__MEDIA__']))
            rest = newpath[ix:]
            if os.path.isdir(loc):
                break

    rest = [i for i in rest if i not in {'..', '.'}]
    return os.path.join(loc, *rest)


def content_file_location(context, path):
    """
    Returns the location (filename on disk) of the content file for the dynamic
    page represented by `path`.

    This function is responsible for looking for content files (regardless of
    their extension), and also for looking for pages that don't have an
    associated directory (i.e., pages represented by a single file).

    **Parameters:**

    * `context`: the context associated with this request
    * `path` is an "intermediate" URL (i.e., a list of strings starting with a
        course).

    **Returns:** a string containing the location of the requested file on
    disk.
    """
    course = path[0]
    path = path[1:]
    newpath = []
    last_dname = None
    broke = False
    cur = ''
    for ix in range(len(path)):
        cur = path[ix]
        if cur == '.':
            pass
        elif cur == '..':
            newpath = newpath[:-1]
        else:
            try:
                dname = loader.get_directory_name(context, course, path[:ix],
                                                  cur)
            except FileNotFoundError:
                return None
            if dname is None:
                if ix != len(path) - 1:
                    return None
                if last_dname is None:
                    return None
                broke = True
                break
            newpath.append(dname if dname != '' else cur)
        last_dname = dname

    basepath = loader.get_course_fs_location(context, course)
    basepath = os.path.join(basepath, *newpath)

    for f in language.source_formats:
        if broke:
            fn = os.path.join(basepath, "%s.%s" % (cur, f))
            if os.path.isfile(fn):
                return fn
        else:
            # then for directories with content files
            fname = os.path.join(basepath, 'content.%s' % f)
            if os.path.isfile(fname):
                return fname
    return None


def serve_static_file(context,
                      fname,
                      environment=None,
                      stream=False,
                      streamchunk=4096):
    """
    Generate an HTTP response to serve up a static file, or a 404 error if the
    file does not exist.  Makes use of the browser's cache when possible.

    **Parameters**:

    * `context`: the context associated with this request
    * `fname`: the location on disk of the file to be sent

    **Optional Parameters:**

    * `environment` (default `{}`): the environment variables associated with
        the request
    * `stream` (default `False`): whether this file should be streamed (instead
        of sent as one bytestring).  Regardless of the value of `stream`, files
        above 1MB are always streamed.
    * `streamchunk` (default `4096`): the size, in bytes, of the chunks in the
        resulting stream
    """
    with open('/tmp/catsoop', 'a') as f:
        print(fname, file=f)
    environment = environment or {}
    try:
        status = ('200', 'OK')
        headers = {
            'Content-type': mimetypes.guess_type(fname)[0] or 'text/plain'
        }
        mtime = os.stat(fname).st_mtime
        headers['ETag'] = str(hash(mtime))
        headers['Cache-Control'] = 'no-cache'
        if ('HTTP_IF_NONE_MATCH' in environment and
                headers['ETag'] == environment['HTTP_IF_NONE_MATCH']):
            return ('304', 'Not Modified'), headers, ''
        headers['Content-length'] = os.path.getsize(fname)
        f = open(fname, 'rb')
        if stream or headers['Content-length'] > 1024 * 1024:

            def streamer():
                r = f.read(streamchunk)
                while len(r) > 0:
                    yield r
                    r = f.read(streamchunk)
                f.close()

            out = streamer()
        else:
            out = f.read()
            f.close()
        headers['Content-length'] = str(headers['Content-length'])
    except:
        status, headers, out = errors.do_404_message(context)
    return status, headers, out


def is_static(context, path):
    """
    **Parameters**:

    * `context`: the context associated with this request
    * `path`: an "intermediate" URL (list of strings) representing a given
        resource

    **Returns: `True` if the path represents a static file, and `False`
    otherwise
    """
    return os.path.isfile(static_file_location(context, path))


def is_resource(context, path):
    """
    **Parameters:**

    * `context`: the context associated with this request
    * `path`: an "intermediate" URL (list of strings) representing a given
        resource

    **Returns:** `True` if the path represents a dynamic page with a content
    file, and `False` otherwise.
    """
    return content_file_location(context, path) is not None


def _real_url_helper(context, url):
    u = [context.get('cs_url_root', base_context.cs_url_root), '__STATIC__']
    u2 = u[:1]
    end = url.split('/')[1:]
    if url.startswith('BASE'):
        new = ['__BASE__']
        pre = u + new if is_static(context, new + end) else u2
    elif url.startswith('COURSE'):
        new = [str(context['cs_course'])]
        floc = content_file_location(context, new + end)
        if floc is not None and os.path.isfile(floc):
            pre = u2 + new
        else:
            pre = u + new
    elif url.startswith('CURRENT'):
        new = context['cs_path_info']
        test_floc = content_file_location(context, new)
        _, test_file = os.path.split(test_floc)
        if test_file.rsplit('.', 1)[0] != 'content':
            new = new[:-1]
        floc = content_file_location(context, new + end)
        if floc is not None and os.path.isfile(floc):
            pre = u2 + new
        else:
            pre = u + new
    elif (url.startswith('__HANDLER__') or url.startswith('__QTYPE__') or
          url.startswith('__PLUGIN__') or url.startswith('__AUTH__')):
        pre = u
        end = [url]
    else:
        pre = [url]
        end = []
    return pre + end


def get_real_url(context, url):
    '''
    Convert a location from our internal representation to something that will
    actually point the web browser to the right place.

    Links in CAT-SOOP can begin with `BASE`, `COURSE`, `CURRENT`, `__QTYPE__`,
    `__HANDLER__`, `__AUTH__`, or `__PLUGIN__`.  This function takes in a URL
    in that form and returns the corresponding URL.

    **Parameters:**

    * `context`: the context associated with this request
    * `url`: a location, possibly starting with a "magic" location (e.g.,
        `CURRENT`)

    **Returns:** a string containing a URL pointing to the corresponding
    resource
    '''
    u = urllib.parse.urlparse(url)
    original = urllib.parse.urlunparse(u[:3] + ('', '', ''))
    new_url = '/'.join(_real_url_helper(context, original))
    u = ('', '', new_url, ) + u[3:]
    return urllib.parse.urlunparse(u)


def dict_from_cgi_form(cgi_form):
    '''
    Convert CGI FieldStorage into a dictionary
    '''
    o = {}
    for key in cgi_form:
        res = cgi_form[key]
        try:
            if res.file:
                o[key] = res.file.read()
            else:
                o[key] = res.value
        except:
            o[key] = res
    return o


def display_page(context):
    """
    Generate the HTTP response for a dynamically-generated page.

    **Parameters:**

    * `context`: the context associated with this request

    **Returns:** a 3-tuple `(response_code, headers, content)` as expected by
    `catsoop.wsgi.application`
    """
    if context['cs_process_theme']:
        context['cs_theme'] = ("%s/cs_util/process_theme"
                               "?theme=%s"
                               "&preload=%s") % (context['cs_url_root'],
                                                 context['cs_theme'],
                                                 context['cs_original_path'])
    headers = {'Content-type': 'text/html'}
    if context.get('cs_user_info', {}).get('real_user', None) is not None:
        impmsg = ('<center><b><font color="red">'
                  'You are viewing this page as <i>%(u)s</i>.<br/>'
                  "Actions you take may affect <i>%(u)s</i>\'s account."
                  '</font></b></center><p>') % {
                      'u': context['cs_username']
                  }
        context['cs_content'] = impmsg + context['cs_content']
    context['cs_content'] = language.handle_custom_tags(
        context, context['cs_content'])
    default = os.path.join(
        context.get('cs_fs_root', base_context.cs_fs_root), '__MEDIA__',
        'templates', "main.template")
    temp = _real_url_helper(context, context['cs_template'])
    if '__STATIC__' in temp:
        default = static_file_location(context, temp[2:])
    loader.run_plugins(context, context['cs_course'], 'post_render', context)
    f = open(default)
    template = f.read()
    f.close()
    out = language.handle_custom_tags(
        context, CSFormatter().format(template, **context)) + '\n'
    headers.update(context.get('cs_additional_headers', {}))
    headers.update({'Last-Modified': formatdate()})
    return ('200', 'OK'), headers, out


def _breadcrumbs_html(context):
    _defined = context.get('cs_breadcrumbs_html', None)
    if callable(_defined):
        return _defined(context)
    if context.get('cs_course', None) in {None, 'cs_util', '__QTYPE__', '__HANDLER__', '__PLUGIN__', '__AUTH__'}:
        return ''
    if len(context.get('cs_loader_states', [])) < 2:
        return ''
    out = '<ol class="breadcrumb">'
    to_skip = context.get('cs_breadcrumbs_skip_paths', [])
    link = 'BASE'
    for ix, elt in enumerate(context['cs_loader_states']):
        link = link + '/' + context['cs_path_info'][ix]
        if '/'.join(context['cs_path_info'][1:ix + 1]) in to_skip:
            continue
        if context.get('cs_breadcrumbs_skip', False):
            continue
        name = elt.get('cs_long_name',
                       context['cs_path_info'][ix]) if ix != 0 else 'Home'
        name = language.source_transform_string(context, name)
        extra = '-active' if ix == len(context['cs_loader_states']) - 1 else ''
        out += '<li class="breadcrumb-item%s"><a href="%s">%s</a></li>' % (
            extra, link, name)
    return out + '</ol>'


def md5(x):
    return hashlib.md5(x.encode()).hexdigest()


def _top_menu_html(topmenu, header=True):
    if isinstance(topmenu, str):
        return topmenu
    else:
        out = ''
    for i in topmenu:
        if i == 'divider':
            out += '\n<div class="divider"></div>'
            continue
        link = i['link']
        if isinstance(link, str):
            out += '\n<a href="%s">%s</a>' % (link, i['text'])
        else:
            menu_id = md5(str(i))
            out += '\n<div class="dropdown" onmouseleave="this.children[1].checked = false;">'
            out += '\n<label class="dropbtn" for="cs_menu_%s">%s<span class="downarrow">▼</span></label>' % (menu_id, i['text'])
            out += '\n<input type="checkbox" class="dropdown-checkbox" id="cs_menu_%s" checked="false"/>' % menu_id
            out += '\n<div class="dropdown-content">'
            out += _top_menu_html(link, False)
            out += '</div>'
            out += '</div>'
    if header:
        return out + '<a href="javascript:void(0);" class="icon" onclick="toggleResponsiveHeader()">&#9776;</a>'
    return out


def _set_colors(context):
    if context['cs_light_color'] is None:
        context['cs_light_color'] = _compute_light_color(context['cs_base_color'])

    if context.get('cs_base_font_color', None) is None:
        context['cs_base_font_color'] = _font_color_from_background(context['cs_base_color'])

    if context.get('cs_light_font_color', None) is None:
        context['cs_light_font_color'] = _font_color_from_background(context['cs_light_color'])


def _hex_to_rgb(x):
    if x.startswith('#'):
        return _hex_to_rgb(x[1:])
    if len(x) == 3:
        return _hex_to_rgb(''.join(i*2 for i in x))
    try:
        return tuple(int(x[i*2:i*2+2], 16) for i in range(3))
    except:
        return (0, 0, 0)


def _luminance(rgb_tuple):
    r, g, b = rgb_tuple
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _font_color_from_background(bg):
    return '#000' if _luminance(_hex_to_rgb(bg)) >= 0.5 else '#fff'


def _hex(n):
    n = int(n)
    return hex(n)[2:4]


def _rgb_to_hex(tup):
    return '#%s%s%s' % tuple(map(_hex, tup))


def _rgb_to_hsv(tup):
    return colorsys.rgb_to_hsv(*(i/255 for i in tup))


def _hsv_to_rgb(tup):
    return tuple(int(i*255) for i in colorsys.hsv_to_rgb(*tup))


def _clip(x, lo=0, hi=1):
    return min(hi, max(x, lo))


def _compute_light_color(base):
    base_hsv = _rgb_to_hsv(_hex_to_rgb(base))
    light_hsv = (base_hsv[0], _clip(base_hsv[1]-0.2), _clip(base_hsv[2]+0.2))
    return _rgb_to_hex(_hsv_to_rgb(light_hsv))


def main(environment):
    """
    Generate the page content associated with this request, properly handling
    dynamic pages and static files.

    This function is the main entrypoint into CAT-SOOP.  It is responsible for:

    * gathering form data
    * organizing execution of `preload.py` files
    * authenticating users
    * loading page source and dispatching to the proper handlers
    * displaying the result
    * handling errors in these steps

    **Parameters:**

    * `environment`: a dictionary containing the environment variables
        associated with this request.

    **Returns:** a 3-tuple `(response_code, headers, content)` as expected by
    `catsoop.wsgi.application`
    """
    context = {}
    context['cs_env'] = environment
    context['cs_now'] = time.now()
    force_error = False
    try:
        # DETERMINE WHAT PAGE WE ARE LOADING
        path_info = environment.get('PATH_INFO', '/')
        context['cs_original_path'] = path_info[1:]
        path_info = [i for i in path_info.split('/') if i != '']

        # RETURN STATIC FILE RESPONSE RIGHT AWAY
        if len(path_info) > 0 and path_info[0] == '__STATIC__':
            return serve_static_file(context,
                                     static_file_location(
                                         context, path_info[1:]), environment)

        # LOAD FORM DATA
        if 'wsgi.input' in environment:
            # need to read post variables from wsgi.input
            fields = cgi.FieldStorage(
                fp=environment['wsgi.input'],
                environ=environment,
                keep_blank_values=True)
        else:
            fields = cgi.FieldStorage()
        form_data = dict_from_cgi_form(fields)

        # INITIALIZE CONTEXT
        context['cs_additional_headers'] = {}
        context['cs_path_info'] = path_info
        context['cs_form'] = form_data
        qstring = urllib.parse.parse_qs(environment.get('QUERY_STRING', ''))
        context['cs_qstring'] = qstring

        # LOAD GLOBAL DATA
        e = loader.load_global_data(context)
        if len(path_info) > 0:
            context['cs_short_name'] = path_info[-1]
            context['cs_course'] = path_info[0]
            path_info = path_info[1:]

        # SET SOME CONSTANTS FOR THE TEMPLATE (may be changed later)
        course = context.get('cs_course', None)
        if course is None or course in {'cs_util', '__QTYPE__', '__HANDLER__', '__PLUGIN__', '__AUTH__'}:
            context['cs_home_link'] = 'BASE'
            context['cs_source_qstring'] = ''
        else:
            context['cs_home_link'] = 'COURSE'
            context['cs_source_qstring'] = '?course=%s' % course
        context['cs_top_menu_html'] = ''
        context['cs_breadcrumbs_html'] = ''

        # CHECK FOR VALID CONFIGURATION
        if e is not None:
            return (('500', 'Internal Server Error'), {
                'Content-type': 'text/plain',
                'Content-length': str(len(e))
            }, e)
        if len(context['_cs_config_errors']) > 0:
            m = ('The following errors occurred while '
                 'loading global configuration:\n\n')
            m += '\n'.join(context['_cs_config_errors'])
            out = errors.do_error_message(context, m)
            force_error = True
            raise Exception

        # LOAD SESSION DATA (if any)
        context['cs_sid'], new = session.get_session_id(environment)
        if new:
            hdr = context['cs_additional_headers']
            url_root = urllib.parse.urlparse(context['cs_url_root'])
            domain = url_root.netloc.rsplit(':', 1)[0]
            path = url_root.path or '/'
            hdr['Set-Cookie'] = 'sid=%s; Domain=%s; Path=%s' % (
                context['cs_sid'], domain, path)
        session_data = session.get_session_data(context, context['cs_sid'])
        context['cs_session_data'] = session_data

        # DO EARLY LOAD FOR THIS REQUEST
        if context['cs_course'] is not None:
            cfile = content_file_location(context,
                                          [context['cs_course']] + path_info)
            x = loader.do_early_load(context, context['cs_course'], path_info,
                                     context, cfile)
            if x == 'missing':
                return errors.do_404_message(context)

            _set_colors(context)

            # AUTHENTICATE
            # doesn't happen until now because what we want to do might depend
            # on what is in the EARLY_LOAD files, unfortunately
            if context.get('cs_auth_required', True):
                user_info = auth.get_logged_in_user(context)
                context['cs_user_info'] = user_info
                context['cs_username'] = str(user_info.get('username', None))
                if user_info.get('cs_render_now', False):
                    session.set_session_data(context, context['cs_sid'],
                                             context['cs_session_data'])
                    return display_page(context)
                redir = None
                if user_info.get('cs_reload', False):
                    redir = '/'.join([context.get('cs_url_root', base_context.cs_url_root)] +
                                     context['cs_path_info'])
                if redir is None:
                    redir = user_info.get('cs_redirect', None)
                if redir is not None:
                    session.set_session_data(context, context['cs_sid'],
                                             context['cs_session_data'])
                    return redirect(redir)

                # ONCE WE HAVE THAT, GET USER INFORMATION
                context['cs_user_info'] = auth.get_user_information(context)
            else:
                context['cs_user_info'] = {}
                context['cs_username'] = None

            # now with user information, update top menu if we can
            menu = context.get('cs_top_menu', None)
            if isinstance(menu, list) and context.get('cs_auth_required', True):
                uname = context['cs_username']
                base_url = '/'.join([context['cs_url_root']] + context['cs_path_info'])
                if str(uname) == 'None':
                    menu.append({'text': 'Log In',
                                 'link': '%s?loginaction=login' % base_url})
                else:
                    menu_entry = {'text': uname, 'link': []}
                    auth_method = auth.get_auth_type(context)
                    for i in auth_method.get('user_menu_options', lambda c: [])(context):
                        menu_entry['link'].append(i)
                    menu_entry['link'].append({'text': 'Log Out',
                                               'link': '%s?loginaction=logout' % base_url})
                    menu.append(menu_entry)

            # MAKE SURE LATE LOAD EXISTS; 404 IF NOT
            if context.get('cs_course', None):
                result = is_resource(context,
                                     [context['cs_course']] + path_info)
                if not result:
                    return errors.do_404_message(context)

            # FINALLY, DO LATE LOAD
            loader.do_late_load(context, context['cs_course'], path_info,
                                context, cfile)
        else:
            default_course = context.get('cs_default_course', None)
            if default_course is not None:
                return redirect(
                    '/'.join([context.get('cs_url_root', base_context.cs_url_root), default_course]))
            else:
                _set_colors(context)
                root = context.get('cs_fs_root', base_context.cs_fs_root)
                path = os.path.join(root, '__MEDIA__', 'mainpage.md')
                with open(path) as f:
                    context['cs_content'] = f.read()
                context['cs_content'] = language.handle_includes(context, context['cs_content'])
                context['cs_content'] = language.handle_python_tags(
                    context, context['cs_content'])
                context['csm_language'].md_pre_handle(context)
                context['cs_handler'] = 'passthrough'

        res = tutor.handle_page(context)

        if res is not None:
            # if we're here, the handler wants to give a specific HTTP response
            # (maybe a redirect?)
            session.set_session_data(context, context['cs_sid'],
                                     context['cs_session_data'])
            return res
        if 'cs_post_handle' in context:
            context['cs_post_handle'](context)
        loader.run_plugins(context, context['cs_course'], 'post_handle',
                           context)

        # SET SOME MORE TEMPLATE-SPECIFIC CONSTANTS, AND RENDER THE PAGE
        context['cs_top_menu_html'] = _top_menu_html(context['cs_top_menu'],
                                                     True)
        context['cs_breadcrumbs_html'] = _breadcrumbs_html(context)

        out = display_page(context)  # tweak and display HTML

        session_data = context['cs_session_data']
        session.set_session_data(context, context['cs_sid'], session_data)
    except:
        if not force_error:
            out = errors.do_error_message(context)
    out = out[:-1] + (out[-1].encode('utf-8'), )
    out[1].update({'Content-length': str(len(out[-1]))})
    return out
