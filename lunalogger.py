#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division
import re
import datetime
import time
from urllib import quote_plus
from urlparse import parse_qs
import cgi
import pymysql
import template
import settings

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
    title_sitename = u'lunalogger'
    linkify = None   # селектор, для которого применяется linkify
    js_for_logpage = False   # подключает jquery-штуки для страницы лога (плавная прокрутка, модальные окна)
    conn = None
    navbar = None
    # (внутреннее имя (чтобы поменить ссылку активной, active=внутреннее имя), url, текст ссылки)
    default_navbar = (
        ('main', '/', u'главная'),
        ('log', '/log', u'лог'),
        ('users', '/users', u'пользователи')
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
                title = self.title + u' :: ' + self.__class__.title_sitename
            else:
                title = self.__class__.title_sitename
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

    def make_log(self, log_from, log_to, nick=None, user_id=None):
        if nick:
            query, params = u'SELECT `time`, `message`, `me` FROM `chat` WHERE `user`=%s AND `time` BETWEEN %s AND %s ORDER BY `message_id` ASC;', (user_id, log_from, log_to)
        else:
            query, params = u'SELECT `time`, `message`, `me`, `nick` FROM `chat` INNER JOIN `users` ON `chat`.`user`=`users`.`user_id` WHERE `chat`.`time` BETWEEN %s AND %s ORDER BY `chat`.`message_id` ASC;', (log_from, log_to)
        self.cur.execute(query, params);
        log = []
        for numb, message_tuple in enumerate(self.cur.fetchall(), 1):   # message_tuple = (time, message, me[, nick])
            current_nick = nick if nick else message_tuple[3]
            nick_formatted = (template.log_nick_me if message_tuple[2] else template.log_nick_normal).format(u'/users/' + quote_plus(current_nick.encode('utf-8')), cgi.escape(current_nick))
            log.append(template.log_line.format(numb, datetime.datetime.fromtimestamp(message_tuple[0]), nick_formatted, cgi.escape(message_tuple[1])))
        return u''.join(log)


    @Path.add('/')
    def main(self):
        self.title = template.main_title
        self.navbar = (self.__class__.default_navbar, 'main')
        self.response.append(template.main)

    @Path.add('/log')
    def log_redirect(self):
        self.status = '302 Found'
        self.plain = True
        self.headers.append(('Location', datetime.date.today().strftime('/log/%Y/%m/%d')))

    @Path.add('/log/{year:d:4}/{month:d:2}/{day:d:2}')
    def log(self, year, month, day):
        try:
            log_date = datetime.datetime(int(year), int(month), int(day))
        except ValueError:
            self.error_404()
            return
        self.title = template.log_title.format(log_date)
        self.linkify = u'.log-message'
        self.js_for_logpage = True
        self.db_connect()
        log_from = int(time.mktime(log_date.timetuple()))
        log_to = log_from + 86399
        prev_day = log_date - datetime.timedelta(days=1)
        next_day = log_date + datetime.timedelta(days=1)
        log_navbar = ((u'##log-bottom', template.nav_down), (u'##log-top', template.nav_up), (u'/log/{:%Y/%m/%d}'.format(prev_day), template.nav_left), ('/log/{:%Y/%m/%d}'.format(next_day), template.nav_right))
        self.navbar = (self.__class__.default_navbar, 'log', log_navbar)
        log = self.make_log(log_from, log_to)
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

            top_users.append(template.users_row.format(position, u'/users/' + quote_plus(top_user[0].encode('utf-8')), cgi.escape(top_user[0]), top_user[1], top_user[1]/total_messages))
        self.navbar = (self.__class__.default_navbar, 'users')
        self.response.append(template.users.format(total_users, u''.join(top_users)))

    @Path.add('/users/{nick}')
    def user_info(self, nick):
        self.db_connect()
        user_found = self.cur.execute(u'SELECT `user_id`, `nick`, `message_count` FROM `users` WHERE `nick`=%s;', nick)
        if user_found:
            user_id, nick, message_count = self.cur.fetchone()
            self.title = template.users_user_title.format(cgi.escape(nick))
            self.linkify = u'.bg-info'
            navbar_user = (('user', '/users/' + quote_plus(nick.encode('utf-8')), cgi.escape(nick)),)
            self.cur.execute(u'SELECT @first := MIN(`message_id`), @last := MAX(`message_id`) FROM `chat` WHERE `user`=%s;', user_id)
            self.cur.execute(u'SELECT `time`, `message` FROM `chat` WHERE `message_id`=@first or `message_id`=@last;')
            result = self.cur.fetchone()
            fst_time = datetime.datetime.fromtimestamp(result[0])
            fst_text = result[1]
            fst_message = template.users_user_info_message.format(u'/log/{0:%Y/%m/%d}'.format(fst_time), fst_time, fst_text)
            if message_count > 1:
                result = self.cur.fetchone()
                lst_time = datetime.datetime.fromtimestamp(result[0])
                lst_text = result[1]
                lst_message = template.users_user_info_message.format(u'/log/{0:%Y/%m/%d}'.format(lst_time), lst_time, lst_text)
                messages = template.users_user_info_fst + fst_message + template.users_user_info_lst + lst_message
            else:
                messages = fst_message
            user_info = template.users_user_info.format(cgi.escape(nick), message_count, messages)
            self.navbar = (self.__class__.default_navbar + navbar_user, 'user')
            self.response.append(user_info)
        else:
            self.title = template.users_user_not_found_title
            self.navbar = (self.__class__.default_navbar, 'users')
            self.response.append(template.users_user_not_found.format(cgi.escape(nick)))

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
                    if post_data['token'][0] != settings.token: raise ValueError
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
