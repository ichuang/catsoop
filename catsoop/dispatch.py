# This file is part of CAT-SOOP
# Copyright (c) 2011-2016 Adam Hartz <hartz@mit.edu>
# CAT-SOOP is free software, licensed under the terms described in the LICENSE
# file.  If you did not receive a copy of this file with CAT-SOOP, please see:
# https://cat-soop.org/LICENSE


def redirect(location):
    '''
    Generate HTTP response that redirects the user to the specified location
    '''
    return ('302', 'Found'), {'Location': str(location)}, ''


def static_file_location(context, path):
    '''
    Given an "intermediate" URL, return the path to that file on disk.
    Used by serve_static_file.
    '''
    loc = ''
    rest = []
    if path[0] == '__BASE__':
        # serving from base
        loc = os.path.join(
            context.get('cs_fs_root', gb.cs_fs_root), '__MEDIA__')
        rest = path[1:]
    elif path[0] == '__HANDLER__':
        # serving from atype
        loc = os.path.join(
            context.get('cs_fs_root', gb.cs_fs_root), '__HANDLERS__', path[1],
            '__MEDIA__')
        rest = path[2:]
    elif path[0] == '__QTYPE__':
        # serving from qtype
        loc = os.path.join(
            context.get('cs_fs_root', gb.cs_fs_root), '__QTYPES__', path[1],
            '__MEDIA__')
        rest = path[2:]
    else:
        # preprocess the path to prune out 'dots' and 'double-dots'
        course = path[0]
        path = path[1:]
        newpath = []
        for ix in xrange(len(path)):
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
            context.get('cs_data_root', gb.cs_data_root), 'courses', course)
        for ix in xrange(len(newpath) - 1, -1, -1):
            loc = os.path.join(*([basepath] + newpath[:ix] + ['__MEDIA__']))
            rest = newpath[ix:]
            if os.path.isdir(loc):
                break

    rest = [i for i in rest if i not in {'..', '.'}]
    return os.path.join(loc, *rest)


def content_file_location(context, path):
    """
    Returns the location (filename on disk) of the content file for the
    resource given by path.
    """
    course = path[0]
    path = path[1:]
    newpath = []
    last_dname = None
    broke = False
    cur = ''
    for ix in xrange(len(path)):
        cur = path[ix]
        if cur == '.':
            pass
        elif cur == '..':
            newpath = newpath[:-1]
        else:
            dname = loader.get_directory_name(context, course, path[:ix], cur)
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

    for f in loader.source_formats:
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


def serve_static_file(fname, environment=None, stream=False, streamchunk=4096):
    """
    Generate HTTP response to serve up a static file, or a 404 error if the
    file does not exist.  Makes use of the browser's cache when possible.
    """
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
        status = ('404', 'Static file not found')
        headers = {}
        out = ''
    return status, headers, out


def is_static(meta, path):
    """
    Returns True if the path represents a file on disk, False otherwise
    """
    return os.path.isfile(static_file_location(meta, path))


def is_resource(context, path):
    """
    @param path: The path to the resource in question
    @return: C{True} if the path represents a valid resource (has a content
    file), and C{False} otherwise
    """
    return content_file_location(context, path) is not None


def _real_url_helper(context, url):
    u = [context.get('cs_url_root', gb.cs_url_root), '__STATIC__']
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
    elif url.startswith('__HANDLER__') or url.startswith('__QTYPE__'):
        pre = u
        end = [url]
    else:
        pre = [url]
        end = []
    return pre + end


def get_real_url(context, url):
    '''
    Convert a URL from our internal representation to something that will
    actually point the web browser to the right place.
    '''
    u = urllib.parse.urlparse(url)
    original = urllib.parse.urlunparse(u[:3] + ('', '', ''))
    new_url = '/'.join(_real_url_helper(context, original))
    u = ('',
         '',
         new_url, ) + u[3:]
    return urllib.parse.urlunparse(u)


def fix_single(context, text, matcher, gen):
    """
    For a single (regex, gen) pair, replace all instances.
    Fixes hyperrefs with get_real_url.
    """
    out = ''
    end = 0
    for match in matcher.finditer(text):
        d = match.groupdict()
        if 'url' in d:
            d['url'] = get_real_url(context, d.get('url', ''))
        out += text[end:match.start()]
        end = match.end()
        out += gen.format(**d)
    return out + text[end:]


def dict_from_cgi_form(cgi_form):
    '''
    Dump CGI form info into a dictionary
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
    """
    headers = {'Content-type': 'text/html'}
    if context.get('cs_user_info', {}).get('real_user', None) is not None:
        impmsg = ('<center><b><font color="red">'
                  'You are viewing this page as <i>%(u)s</i>.<br/>'
                  "Actions you take may affect <i>%(u)s</i>\'s account."
                  '</font></b></center><p>') % {'u': context['cs_username']}
        context['cs_content'] = impmsg + context['cs_content']
    context['cs_content'] = handle_custom_tags(context, context['cs_content'])
    default = os.path.join(
        context.get('cs_fs_root', gb.cs_fs_root), '__MEDIA__', 'templates',
        "main.template")
    temp = _real_url_helper(context, context['cs_template'])
    if '__STATIC__' in temp:
        default = static_file_location(context, temp[2:])
    f = open(default)
    template = f.read()
    f.close()
    fmt = dict((i, j.decode('ascii', 'ignore')
                if isinstance(j, (str, unicode)) else j)
               for i, j in context.iteritems())
    out = handle_custom_tags(context, template.format(**fmt)) + '\n'
    headers.update(context.get('cs_additional_headers', {}))
    headers.update({'Last-Modified': formatdate()})
    return ('200', 'OK'), headers, out


def main(environment):
    """
    Generate the page content associated with this request, properly handling
    activities and static files.

    Returns a 3-tuple (response_code, headers, content)

    The "environment" parameter is a dictionary containing the environment
    variables associated with this request.
    """
    context = {}
    context['cs_env'] = environment
    context['cs_ip'] = environment['REMOTE_ADDR']
    force_error = False
    try:
        # DETERMINE WHAT PAGE WE ARE LOADING
        static = None
        path_info = environment.get('PATH_INFO', '/').split('/')
        path_info = [i for i in path_info if i != '']

        # RETURN STATIC FILE RESPONSE RIGHT AWAY
        if len(path_info) > 0 and path_info[0] == '__STATIC__':
            return serve_static_file(
                static_file_location(context, path_info[1:]), environment)

        # LOAD FORM DATA
        if 'wsgi.input' in environment:
            # need to read post variables from wsgi.input
            fields = cgi.FieldStorage(fp=environment['wsgi.input'],
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

        # CHECK FOR VALID CONFIGURATION
        if e is not None:
            return (('500', 'Internal Server Error'),
                    {'Content-type': 'text/plain',
                     'Content-length': str(len(e))}, e)
        if len(context['_cs_config_errors']) > 0:
            m = ('The following errors occurred while '
                 'loading global configuration:\n\n')
            m += '\n'.join(context['_cs_config_errors'])
            out = do_error_message(context, m)
            force_error = True
            raise Exception

        # LOAD SESSION DATA (if any)
        context['cs_sid'], new = session.get_session_id(environment)
        if new:
            hdr = context['cs_additional_headers']
            hdr['Set-Cookie'] = 'sid=%s' % context['cs_sid']
        session_data = session.get_session_data(context['cs_sid'])
        context['cs_session_data'] = session_data

        # DO EARLY LOAD FOR THIS REQUEST
        if context['cs_course'] is not None:
            cfile = content_file_location(context,
                                          [context['cs_course']] + path_info)
            x = loader.do_early_load(context, context['cs_course'], path_info,
                                     context, cfile)
            if x == 'missing':
                status = ('404', "Resource not found")
                headers = {}
                out = ''
                return status, headers, out

            # AUTHENTICATE
            # doesn't happen until now because what we want to do might depend
            # on what is in the EARLY_LOAD files, unfortunately
            if context.get('cs_auth_required', True):
                user_info = auth.get_logged_in_user(context)
                context['cs_user_info'] = user_info
                context['cs_username'] = str(user_info.get('username', None))
                if user_info.get('cs_render_now', False):
                    session.set_session_data(context['cs_sid'],
                                             context['cs_session_data'])
                    return display_page(context)
                if user_info.get('cs_reload', False):
                    session.set_session_data(context['cs_sid'],
                                             context['cs_session_data'])
                    return redirect('/'.join([gb.cs_url_root] + context[
                        'cs_path_info']))

                # ONCE WE HAVE THAT, GET USER INFORMATION
                context['cs_user_info'] = auth.get_user_information(context)

            # MAKE SURE LATE LOAD EXISTS; 404 IF NOT
            if context.get('cs_course', None):
                result = is_resource(context,
                                     [context['cs_course']] + path_info)
                if not result:
                    status = ('404', 'Resource not found')
                    headers = {}
                    out = ''
                    return status, headers, out

            # FINALLY, DO LATE LOAD
            loader.do_late_load(context, context['cs_course'], path_info,
                                context, cfile)
        else:
            context['cs_content'] = 'Placeholder for main page'
            context['cs_handler'] = 'passthrough'

        if 'cs_post_load' in context:
            context['cs_post_load'](context)

        res = tutor.handle_page(context)

        if res is not None:
            # if we're here, the handler wants to give a specific HTTP response
            # (maybe a redirect?)
            session.set_session_data(context['cs_sid'],
                                     context['cs_session_data'])
            return res
        elif 'cs_post_handle' in context:
            context['cs_post_handle'](context)

        out = display_page(context)  # tweak and display HTML

        session_data = context['cs_session_data']
        session.set_session_data(context['cs_sid'], session_data)
    except:
        if not force_error:
            out = do_error_message(context)
    out[1].update({'Content-length': str(len(out[-1]))})
    return out
