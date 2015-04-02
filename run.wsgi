#!/usr/bin/env python
from flup.server.fcgi import WSGIServer
from lunalogger import LoggerApp
import middleware
import settings

app = middleware.PermCache(LoggerApp) if settings.mw_permcache['enabled'] else LoggerApp
WSGIServer(app).run()
