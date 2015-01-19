#!/usr/bin/env python
from flup.server.fcgi import WSGIServer
from lunalogger import LoggerApp
WSGIServer(LoggerApp, bindAddress = '/tmp/fcgi.sock-0').run()
