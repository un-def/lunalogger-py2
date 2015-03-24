# -*- coding: utf-8 -*-
head = u'''<!DOCTYPE html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{0}</title>
    <link rel="stylesheet" href="/static/css/bootstrap.min.css">
    <link rel="stylesheet" href="/static/css/custom.css">
    <link rel="icon" href="/static/favicon.png" type="image/png">
  </head>
  <body>
'''

def make_foot(linkify, js_for_logpage=False):   # linkify - селектор; js_for_logpage=True - одключает jquery-штуки для страницы лога (плавная прокрутка, модальные окна)
    foot = u'''    <script src="/static/js/jquery-1.11.1.min.js"></script>
    <script src="/static/js/bootstrap.min.js"></script>
'''
    if js_for_logpage or linkify: foot += u'    <script src="/static/js/custom.js"></script>\n'
    if js_for_logpage: foot += u'''    <div class="modal fade" id="log-modal" tabindex="-1" role="dialog" aria-labelledby="log-modal-header" aria-hidden="true">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
            <h4 class="modal-title text-center" id="log-modal-header">Ссылка на это сообщение:</h4>
          </div>
          <div class="modal-body text-center">
            <a id="log-modal-link" href="#"></a>
          </div>
        </div>
      </div>
    </div>
    <script>
      $(window).on("load", function () {
        $("#log-modal-link").on("click", function() {$("#log-modal").modal("hide");});
        $(".panel-body").on("click", ".log-li", showMsgLink);
      });
    </script>
    <script src="/static/js/jquery.arbitrary-anchor.js"></script>
    <script>
      AA_CONFIG = {
        animationLength:  500,
        easingFunction:   "linear",
        scrollOffset:     53
      };
    </script>
'''
    if linkify: foot += u'''    <script src="/static/js/jquery.linkify.min.js"></script>
    <script>
      $(window).on("load", {{selector: "{0}"}}, makeLinks);
    </script>
'''.format(linkify)
    foot += u'''  </body>
</html>
'''
    return foot

def make_navbar(navbar, active=None, right_navbar=None):
    u''' navbar = ((внутреннее имя1, url1, текст ссылки1), (внутреннее имя2, url2, текст ссылки2), …)
        active = нутреннее имя
        navbar_right = ((url1, текст ссылки1), (url2, текст ссылки2), …) '''
    li = u''
    for link_ in navbar:   # link_ = (внутреннее имя, url, текст ссылки)
        style = u' class="active"' if link_[0] == active else ''
        li += u'            <li{0}><a href="{1}">{2}</a></li>\n'.format(style, link_[1], link_[2])
    ul = u'          <ul class="nav navbar-nav">\n{0}          </ul>'.format(li)

    if right_navbar:
        li = u''
        for link_ in right_navbar:
            li += u'            <li><a href="{0}">{1}</a></li>\n'.format(link_[0], link_[1])
        ul_right = u'\n          <ul class="nav navbar-nav navbar-right">\n{0}          </ul>'.format(li)
    else:
        ul_right = u''

    return u'''    <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
      <div class="container">
        <div class="navbar-header">
          <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
          </button>
          <a class="navbar-brand" href="/">lunalogger</a>
        </div>
        <div class="collapse navbar-collapse">
{0}{1}
        </div>
      </div>
    </div>
'''.format(ul, ul_right)

nav_left = u'<span class="glyphicon glyphicon-chevron-left"></span>'
nav_right = u'<span class="glyphicon glyphicon-chevron-right"></span>'
nav_up = u'<span class="glyphicon glyphicon-chevron-up"></span>'
nav_down = u'<span class="glyphicon glyphicon-chevron-down"></span>'


####################
# /
main_title = u''

main = u'''    <div class="container">
      <div class="panel panel-warning">
        <div class="panel-heading">
          <h3 class="panel-title">Uwaga!</h3>
        </div>
        <div class="panel-body text-center">
          <h4>Веб-аппликуха на питоне с вёрсткой на бутстрапе и свистелками на жквери.</h4>
          <p>Python (2 & 3), Bootstrap, jQuery, lighttpd, <abbr title="flup.server.fcgi.WSGIServer">flup</abbr>, MySQL, вот это всё.</p>
          <p>Настоящий highload — крутится на коробочке с SoC Atheros AR9344 (MIPS 74Kc @ 560 MHz) и 128 MiB RAM.</p>
        </div>
      </div>
      <p class="text-center small">GitHub: <a href="https://github.com/un-def/lunalogger-py2" class="badge">py2</a> <a href="https://github.com/un-def/lunalogger" class="badge">py3</a></p>
    </div>
'''


####################
# /log/{date}
log_title = u'Лог чата за {0:%d.%m.%Y}'

log = u'''    <div id="log-top" class="container">
      <div class="panel panel-info">
        <div class="panel-heading">
          <h3 class="panel-title">Лог чата за {0:%d.%m.%Y}</h3>
        </div>
        <div class="panel-body">
          <ol class="log-ol">
{1}
          </ol>
        </div>
      </div>
      <span id="log-bottom"></span>
    </div>
'''

log_line = u'''            <li id="{0}" class="log-li"><span class="log-time text-muted">[{1:%H:%M:%S}]</span> {2} <span class="log-message">{3}</span></li>
'''

log_nick_normal = u'&lt;<strong><a href="{0}">{1}</a></strong>&gt;'

log_nick_me = u'* <strong><a href="{0}">{1}</a></strong>'


####################
# /users
users_title = u'Пользователи'

users = u'''    <div class="container">
      <p>Всего пользователей: {0}</p>
      <p>Всего сообщений: {1}</p>
      <br>
      <h4>ТОП-100 наиболее активных пользователей:</h4>
      <div class="row">
        <div class="col-md-6">
          <table class="table table-condensed table-striped">
            <thead>
              <tr>
                <th>#</th>
                <th>Ник</th>
                <th>Сообщений</th>
              </tr>
            </thead>
            <tbody>
{2}
            </tbody>
          </table>
        </div>
      </div>
    </div>
'''

users_row = u'''              <tr>
                <td>{0}</td>
                <td><a href="{1}">{2}</a></td>
                <td>{3} <span class="text-muted">({4:.2%})</span></td>
              </tr>
'''


####################
# /users/{user}
users_user_title = u'Информация о пользователе {0}'

users_user_info = u'''    <div class="container">
      <div class="panel panel-info">
        <div class="panel-heading">
          <h3 class="panel-title">Информация о пользователе {0}</h3>
        </div>
        <div class="panel-body">
          <p>Всего сообщений: {1}</p>
{2}
        </div>
      </div>
    </div>
'''

users_user_info_message = u'''          <p class="bg-info">
            <a href="{0}">{1:%d.%m.%Y %H:%M:%S}</a> {2}
          </p>
'''

users_user_info_fst = u'''          Первое сообщение:
'''

users_user_info_lst = u'''          Последнее сообщение:
'''


####################
# /users/{user}/log/{date}
users_user_log_title = u'Лог сообщений {0} за {1:%d.%m.%Y}'

users_user_log = u'''    <div id="log-top" class="container">
      <div class="panel panel-info">
        <div class="panel-heading">
          <h3 class="panel-title">Лог сообщений {0} за {1:%d.%m.%Y}</h3>
        </div>
        <div class="panel-body">
          <ol class="log-ol">
{2}
          </ol>
        </div>
      </div>
      <span id="log-bottom"></span>
    </div>
'''


####################
# /users/{unknownuser}
users_user_not_found_title = u'Пользователь не найден'

users_user_not_found = u'''    <div class="container">
      <div class="alert alert-warning" role="alert">
        Пользователь с ником {0} не найден.
      </div>
    </div>
'''


####################
# 404
error_404_title = u'Страница не найдена'

error_404 = u'''    <div class="container">
      <div class="alert alert-danger" role="alert">
        404 Страница не найдена.
      </div>
    </div>
'''

