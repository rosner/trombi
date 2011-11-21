#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_session.py 13-Oct-2011
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import with_statement

from datetime import datetime
import hashlib
import sys

from nose.tools import eq_ as eq
from .couch_util import setup_with_admin as setup, teardown, with_couchdb
from .util import with_ioloop, DatetimeEncoder

try:
    import json
except ImportError:
    import simplejson as json

try:
    # Python 3
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    # Python 2
    from urllib2 import urlopen
    from urllib2 import HTTPError

import trombi
import trombi.errors


@with_ioloop
@with_couchdb
def test_session_api_with_wrong_credentials(baseurl, ioloop):
    s = trombi.Server(baseurl, io_loop=ioloop)
    response = []

    def session_callback(cookie, inner_response):
        response.append(inner_response)
        ioloop.stop()

    s.session(session_callback, username="daniel", password="daniel")
    ioloop.start()
    eq(response[0], {u'reason': u'Name or password is incorrect.',
            u'error': u'unauthorized'})

@with_ioloop
@with_couchdb
def test_session_with_user(baseurl, ioloop):
    s = trombi.Server(baseurl, io_loop=ioloop)
    result = {}

    def session_callback(cookie, session_info):
        result['cookie'] = cookie
        result['session_info'] = session_info
        ioloop.stop()

    def add_user_callback(response):
        assert not response.error
        ioloop.stop()

    # add a user
    s.add_user('testuser', 'testpassword', add_user_callback)
    ioloop.start()

    # login
    s.session(session_callback, username="testuser", password="testpassword")
    ioloop.start()

    # check for the cookie and user info
    eq(result['cookie'].startswith("AuthSession="), True)
    eq(result['session_info'], {u'ok': True, u'name': u'testuser',
        u'roles': []})
    eq(s._fetch_args['headers'], {'Cookie': result['cookie'],
            'X-Couchdb-Www-Authenticate': "Cookie"})

    # get the session info
    s.session(session_callback)
    ioloop.start()

    # check that no cookie has been sent and the session info is correct
    eq(result['cookie'], None)
    eq(result['session_info'], {u'info': {u'authentication_handlers':
            [u'oauth', u'cookie', u'default'], u'authentication_db':
            u'_users'}, u'userCtx': {u'name': None, u'roles': []}, u'ok':
            True})

    # check that logout is working
    s.session(session_callback, logout=True)
    ioloop.start()

    eq(result['cookie'], "AuthSession=")
    eq(result['session_info'], {u'ok': True})
    eq('headers' in s._fetch_args, True)
    eq('Cookie' in s._fetch_args['headers'], False)
    eq('X-Couchdb-Www-Authenticate' in s._fetch_args['headers'], False)
