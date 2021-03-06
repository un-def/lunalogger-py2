#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
import re
import datetime
from urllib import quote
from urlparse import parse_qs
import cgi
import pymysql
import template
import settings
if settings.pytz_timezone:
    import pytz
    from calendar import timegm
    log_tz = pytz.timezone(settings.pytz_timezone)
    dt_to_ts = lambda dt: timegm(dt.utctimetuple())
else:
    from time import mktime
    log_tz = None
    dt_to_ts = lambda dt: int(mktime(dt.timetuple()))

class Path(object):

    registered = {}

    @classmethod
    def add(self, pattern):
        """ pattern format:
            {var_name[:type][:length]}

                var_name:
                    ...

                type:
                    s (string) - any symbols except '/';
                    d (digit) - only digits;
                    default - string;

                length:
                    m - exactly m symbols;
                    m,n - from m to n symbols;
                    ,n - from 1 to n symbols;
                    m, - min m symbols, infinite upper bound;
                    default - 1,
        """
        def pattern2re(match):
            var_name = match.group(1)
            char_set = '[0-9]' if match.group(3) == 'd' else '[^/]'
            qualifier = '{' + match.group(5) + '}' if match.group(5) else '+'
            return '(?P<{0}>{1}{2})'.format(var_name, char_set, qualifier)
        def add_decorator(call_object):
            if pattern != '/':
                pattern_regexp = re.sub('\{([^:]+?)(:([sd])(:([0-9,]+))?)?\}', pattern2re, pattern) + '/?$'
            else:
                pattern_regexp = '/$'
            self.registered[pattern_regexp] = call_object
            return call_object
        return add_decorator

    @classmethod
    def check(self, path):
        for pattern_regexp, call_object in self.registered.items():
            match = re.match(pattern_regexp, path)
            if match:
                return (call_object, match.groupdict())
        return False


class LoggerApp(object):

    status = '200 OK'
    plain = False
    title = ''
    linkify = False   # включает linkify
    js_for_logpage = False   # подключает jquery-штуки для страницы лога (плавная прокрутка, модальные окна)
    conn = None
    navbar = None
    default_navbar = (
        # (внутреннее имя, url, текст ссылки)
        ('main', '/', u'главная'),
        ('log', '/log/', u'лог'),
        ('users', '/users/', u'пользователи')
    )

    def __init__(self, environ, start_response):
        self.environ = environ
        self.start = start_response

    def __iter__(self):
        self.headers = []
        self.response = []
        path = self.environ['PATH_INFO']
        make_content = Path.check(path)
        if make_content:
            if settings.append_slash and not path.endswith('/'):
                self.redirect(quote(path, safe='/') + '/', perm=True)
            else:
                make_content[0](self, **make_content[1])
                if self.conn:
                    self.db_close()
        else:
            self.error_404()
        if self.plain:
            self.headers.append(('Content-type', 'text/plain; charset=utf-8'))
        else:
            self.headers.append(('Content-type', 'text/html; charset=utf-8'))
        self.start(self.status, self.headers)
        if not self.plain:
            if self.title != u'':
                title = self.title + settings.title_separator + settings.title_sitename
            else:
                title = settings.title_sitename
            yield template.head.format(title).encode('utf-8')
            if self.navbar:
                yield template.make_navbar(*self.navbar).encode('utf-8')
        for el in self.response:
            yield el.encode('utf-8')
        if not self.plain:
            yield template.make_foot(self.linkify, self.js_for_logpage).encode('utf-8')

    def db_connect(self):
        self.conn = pymysql.connect(**settings.db)
        self.cur = self.conn.cursor()

    def db_close(self):
        self.cur.close()
        self.conn.close()

    def error_404(self):
        self.status = '404 Not Found'
        self.title = template.error_404_title
        self.navbar = (self.__class__.default_navbar, )
        self.response.append(template.error_404)

    def redirect(self, url, perm=False):
        self.status = '301 Moved Permanently' if perm else '302 Found'
        self.plain = True
        if url.startswith('/'):
            url = self.make_abs_url(url)
        self.headers.append(('Location', url))

    def make_abs_url(self, rel_url):
        url = self.environ['wsgi.url_scheme'] + '://'
        if self.environ.get('HTTP_HOST'):
            url += self.environ['HTTP_HOST']
        else:
            url += self.environ['SERVER_NAME']
            if self.environ['wsgi.url_scheme'] == 'https':
                if self.environ['SERVER_PORT'] != '443':
                    url += ':' + self.environ['SERVER_PORT']
            else:
                if self.environ['SERVER_PORT'] != '80':
                    url += ':' + self.environ['SERVER_PORT']
        url += rel_url
        return url

    def get_user(self, nick):
        if not self.conn:
            self.db_connect()
        user = self.cur.execute(u'SELECT `user_id`, `nick`, `message_count` FROM `users` WHERE `nick`=%s;', nick)
        if user:
            return self.cur.fetchone()
        else:
            return False

    def user_not_found(self, nick):
        self.status = '404 Not Found'
        self.title = template.users_user_not_found_title
        self.navbar = (self.__class__.default_navbar, 'users')
        if isinstance(nick, str):
            nick = nick.decode('utf-8')
        self.response.append(template.users_user_not_found.format(cgi.escape(nick)))

    def check_user(self, nick):
        ''' shortcut function:
            user found: return user's info tuple
            user not found: return False and create user_not_found response
        '''
        user = self.get_user(nick)
        if not user:
            self.user_not_found(nick)
        return user

    def make_log(self, log_date, nick=None, user_id=None):
        log_from = dt_to_ts(log_date)
        log_to = log_from + 86399
        if nick:
            query, params = u'SELECT `time`, `message`, `me` FROM `chat` WHERE `user`=%s AND `time` BETWEEN %s AND %s ORDER BY `message_id` ASC;', (user_id, log_from, log_to)
        else:
            query, params = u'SELECT `time`, `message`, `me`, `nick` FROM `chat` INNER JOIN `users` ON `chat`.`user`=`users`.`user_id` WHERE `chat`.`time` BETWEEN %s AND %s ORDER BY `chat`.`message_id` ASC;', (log_from, log_to)
        self.cur.execute(query, params);
        log = []
        for numb, message_tuple in enumerate(self.cur.fetchall(), 1):   # message_tuple = (time, message, me[, nick])
            current_nick = nick if nick else message_tuple[3]
            nick_formatted = (template.log_nick_me if message_tuple[2] else template.log_nick_normal).format(u'/users/{}/'.format(quote(current_nick.encode('utf-8'))), cgi.escape(current_nick))
            log.append(template.log_line.format(numb, datetime.datetime.fromtimestamp(message_tuple[0], tz=log_tz), nick_formatted, cgi.escape(message_tuple[1])))
        return u''.join(log)

    def make_log_navbar(self, log_date, link_format):
        prev_day = log_date - datetime.timedelta(days=1)
        next_day = log_date + datetime.timedelta(days=1)
        return (    (u'#;log-bottom', template.nav_down),
                    (u'#;log-top', template.nav_up),
                    (link_format.format(prev_day), template.nav_left),
                    (link_format.format(next_day), template.nav_right)
        )

    def make_datetime(self, year, month, day):
        try:
            dt = datetime.datetime(int(year), int(month), int(day))
            if log_tz: dt = log_tz.localize(dt)
            return dt
        except ValueError:
            return False

    @Path.add('/')
    def main(self):
        self.title = template.main_title
        self.navbar = (self.__class__.default_navbar, 'main')
        self.response.append(template.main)

    @Path.add('/log')
    def log_redirect(self):
        self.redirect(datetime.datetime.now(tz=log_tz).strftime('/log/%Y/%m/%d/'))

    @Path.add('/log/{year:d:4}/{month:d:2}/{day:d:2}')
    def log(self, year, month, day):
        log_date = self.make_datetime(year, month, day)
        if not log_date:
            self.error_404()
            return
        self.title = template.log_title.format(log_date)
        self.linkify = True
        self.js_for_logpage = True
        self.db_connect()
        log_navbar = self.make_log_navbar(log_date, '/log/{:%Y/%m/%d}/')
        self.navbar = (self.__class__.default_navbar, 'log', log_navbar)
        log = self.make_log(log_date)
        self.response.append(template.log.format(log_date, log))

    @Path.add('/users')
    def users_list(self):
        self.title = template.users_title
        self.db_connect()
        self.cur.execute(u'SELECT COUNT(*) FROM `users`;')
        total_users = self.cur.fetchone()[0]
        self.cur.execute(u'SELECT COUNT(*) FROM `chat`;')
        total_messages = self.cur.fetchone()[0]
        self.cur.execute(u'SELECT `nick`, `message_count` FROM `users` ORDER BY `message_count` DESC LIMIT 100;');
        top_users = []
        for position, top_user in enumerate(self.cur.fetchall(), 1):
            top_users.append(template.users_row.format(position, u'/users/{}/'.format(quote(top_user[0].encode('utf-8'))), cgi.escape(top_user[0]), top_user[1], top_user[1]/total_messages))
        self.navbar = (self.__class__.default_navbar, 'users')
        self.response.append(template.users.format(total_users, total_messages, u''.join(top_users)))

    @Path.add('/users/{nick}')
    def user_info(self, nick):
        user = self.check_user(nick)
        if user:
            user_id, nick, message_count = user
            self.title = template.users_user_title.format(cgi.escape(nick))
            self.linkify = True
            self.cur.execute(u'SELECT @first := MIN(`message_id`), @last := MAX(`message_id`) FROM `chat` WHERE `user`=%s;', user_id)
            self.cur.execute(u'SELECT `time`, `message` FROM `chat` WHERE `message_id`=@first or `message_id`=@last;')
            result = self.cur.fetchone()
            fst_time = datetime.datetime.fromtimestamp(result[0], tz=log_tz)
            fst_text = result[1]
            fst_message = template.users_user_info_message.format(u'/log/{0:%Y/%m/%d/}'.format(fst_time), fst_time, fst_text)
            if message_count > 1:
                result = self.cur.fetchone()
                lst_time = datetime.datetime.fromtimestamp(result[0], tz=log_tz)
                lst_text = result[1]
                lst_message = template.users_user_info_message.format(u'/log/{0:%Y/%m/%d/}'.format(lst_time), lst_time, lst_text)
                messages = template.users_user_info_fst + fst_message + template.users_user_info_lst + lst_message
            else:
                messages = fst_message
            user_navbar = (('user', '/users/{}/'.format(quote(nick.encode('utf-8'))), cgi.escape(nick)),)
            self.navbar = (self.__class__.default_navbar + user_navbar, 'user')
            user_info = template.users_user_info.format(cgi.escape(nick), message_count, messages)
            self.response.append(user_info)

    @Path.add('/users/{nick}/log')
    def user_log_redirect(self, nick):
        user = self.check_user(nick)
        if user:
            self.redirect('/users/{0}/log/{1:%Y/%m/%d}/'.format(quote(nick), datetime.datetime.now(tz=log_tz)))

    @Path.add('/users/{nick}/log/{year:d:4}/{month:d:2}/{day:d:2}')
    def user_log(self, nick, year, month, day):
        user = self.check_user(nick)
        if user:
            log_date = self.make_datetime(year, month, day)
            if not log_date:
                self.error_404()
                return
            user_id, nick, message_count = user
            self.title = template.users_user_log_title.format(nick, log_date)
            self.linkify = True
            self.js_for_logpage = True
            log_navbar = self.make_log_navbar(log_date, '/users/'+quote(nick.encode('utf-8'))+'/log/{:%Y/%m/%d}/')
            user_navbar = (('user', '/users/{}/'.format(quote(nick.encode('utf-8'))), cgi.escape(nick)),)
            self.navbar = (self.__class__.default_navbar + user_navbar, 'user', log_navbar)
            user_log = self.make_log(log_date, nick, user_id)
            self.response.append(template.users_user_log.format(nick, log_date, user_log))

    @Path.add('/api')
    def api(self):
        self.plain = True
        self.response.append(u'API. Just API.')

    @Path.add('/api/{method}')
    def api_method(self, method):
        if method == 'post':
            self.plain = True
            if self.environ['REQUEST_METHOD'] == 'POST':
                try:
                    req_body_size = int(self.environ.get('CONTENT_LENGTH', 0)) # может быть пустой строкой, не существовать вообще или == '0'
                except ValueError:
                    req_body_size = 0
                req_body = self.environ['wsgi.input'].read(req_body_size)
                post_data = parse_qs(req_body)
                try:
                    time = int(post_data['time'][0])
                    me = int(post_data['me'][0])
                    if post_data['token'][0] != settings.post_token: raise ValueError
                    try:
                        user = post_data['user'][0].decode('utf-8')
                        message = post_data['message'][0].decode('utf-8')
                    except UnicodeDecodeError:
                        user = post_data['user'][0].decode(settings.post_encoding, errors='replace')
                        message = post_data['message'][0].decode(settings.post_encoding, errors='replace')
                except (KeyError, ValueError):
                    self.response.append(u'error')
                else:
                    self.db_connect()
                    self.cur.execute(u'INSERT INTO `users` SET `nick`=%s, `message_count`=1 ON DUPLICATE KEY UPDATE `user_id`=LAST_INSERT_ID(`user_id`), `message_count`=`message_count`+1;', user);
                    self.cur.execute(u'INSERT INTO `chat` (`time`, `user`, `message`, `me`) VALUES (%s, LAST_INSERT_ID(), %s, %s);', (time, message, me))
                    self.response.append(u'OK')
        else:
            self.error_404()
