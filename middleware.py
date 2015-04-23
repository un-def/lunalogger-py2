#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import gzip
import StringIO
import datetime
from urllib import quote
import settings
if settings.pytz_timezone:
    import pytz
    log_tz = pytz.timezone(settings.pytz_timezone)
else:
    log_tz = None

class PermCache(object):

    def __init__(self, app):
        self.app = app
        path_regex = '/log/(\d{4}/\d{2}/\d{2})/' + ('$' if settings.append_slash else '?$')
        self.path_regex = re.compile(path_regex)

    def __call__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        self.status_ok = False
        self.accept_gzip = True if 'gzip' in self.environ.get('HTTP_ACCEPT_ENCODING', '') else False
        is_log = self.path_regex.search(environ['PATH_INFO'])
        if is_log:
            try:
                log_date = datetime.datetime.strptime(is_log.group(1), '%Y/%m/%d').date()
            except ValueError:
                return self.as_is()
            # не кэшируем будущее, сегодняшний день и вчерашний, если сейчас меньше 01:00
            now = datetime.datetime.now(tz=log_tz)
            if log_date >= now.date() or log_date == now.date()-datetime.timedelta(days=1) and now.hour < 1:
                return self.as_is()
            path_split = [quote(el, safe='') for el in environ['PATH_INFO'].strip('/').split('/')]
            cache_dir = os.path.join(settings.mw_permcache['cache_dir'], *path_split[:-1])
            cache_file = os.path.join(cache_dir, path_split[-1]+'.html.gz')
            if os.path.exists(cache_file):
                self.wrapper_start_response('200 OK', [('Content-type', 'text/html; charset=utf-8')])
                fileobj = open(cache_file, 'rb') if self.accept_gzip else gzip.open(cache_file, 'rb')
                return self.fileobj_iter(fileobj, settings.mw_permcache['chunk_size'])
            else:
                content_iter = self.app(environ, self.wrapper_start_response)
                content = list(content_iter)
                if hasattr(content_iter, 'close'):
                    content_iter.close()
                if self.status_ok:   # не кэшируем редиректы и 404
                    content.append('<!-- сached at {0:%d.%m.%Y %H:%M:%S} -->\n'.format(now))
                    if not os.path.isdir(cache_dir):
                        os.makedirs(cache_dir)
                    buf = StringIO.StringIO()
                    gzipped = gzip.GzipFile(mode='wb', fileobj=buf)
                    try:
                        for el in content:
                            gzipped.write(el)
                    finally:
                        gzipped.close()
                    with open(cache_file, 'wb') as fileobj:
                        fileobj.write(buf.getvalue())
                    if self.accept_gzip:
                        buf.seek(0)
                        return self.fileobj_iter(buf, settings.mw_permcache['chunk_size'])
                return content
        else:
            return self.as_is()

    def wrapper_start_response(self, status, headers, exc_info=None):
        if status == '200 OK':
            self.status_ok = True
        if self.accept_gzip:
            headers.append(('Content-Encoding', 'gzip'))
        return self.start_response(status, headers, exc_info)

    def as_is(self):
        return self.app(self.environ, self.start_response)

    def fileobj_iter(self, fileobj, chunk_size=8192):
        try:
            while True:
                chunk = fileobj.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            fileobj.close()
