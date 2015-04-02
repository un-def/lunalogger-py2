#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import datetime as dt
from urllib import quote
import settings

class PermCache(object):

    def __init__(self, app):
        self.app = app
        path_regex = '/log/(\d{4}/\d{2}/\d{2})/' + ('$' if settings.append_slash else '?$')
        self.path_regex = re.compile(path_regex)

    def __call__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        self.status_ok = False
        is_log = self.path_regex.search(environ['PATH_INFO'])
        if is_log:
            try:
                log_date = dt.datetime.strptime(is_log.group(1), '%Y/%m/%d').date()
            except ValueError:
                return self.app(environ, start_response)
            # не кэшируем будущее, сегодняшний день и вчерашний, если сейчас меньше 01:00
            if log_date >= dt.date.today() or log_date == dt.date.today()-dt.timedelta(days=1) and dt.datetime.today().hour < 1:
                return self.app(environ, start_response)
            path_split = [quote(el, safe='') for el in environ['PATH_INFO'].strip('/').split('/')]
            cache_dir = os.path.join(settings.mw_permcache['cache_dir'], *path_split[:-1])
            cache_file = os.path.join(cache_dir, path_split[-1]+'.html')
            if os.path.exists(cache_file):
                content = self.file_iter(cache_file, settings.mw_permcache['chunk_size'])
                self.start_response('200 OK', [('Content-type', 'text/html; charset=utf-8')])
            else:
                content_iter = self.app(environ, self.custom_start_response)
                content = list(content_iter)
                if hasattr(content_iter, 'close'):
                    content_iter.close()
                if self.status_ok:   # не кэшируем редиректы и 404
                    content.append('<!-- сached at {0:%d.%m.%Y %H:%M:%S} -->\n'.format(dt.datetime.today()))
                    if not os.path.isdir(cache_dir):
                        os.makedirs(cache_dir)
                    with open(cache_file, 'wb') as file_obj:
                        for el in content:
                            file_obj.write(el)
            return content
        else:
            return self.app(environ, start_response)

    def custom_start_response(self, status, headers, exc_info=None):
        if status == '200 OK':
            self.status_ok = True
        return self.start_response(status, headers, exc_info)

    def file_iter(self, file_name, chunk_size=8192):
        with open(file_name, 'rb') as file_obj:
            while True:
                chunk = file_obj.read(chunk_size)
                if not chunk:
                    break
                yield chunk
