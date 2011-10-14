#
# Copyright (c) 2011 Daniel Truemper truemped@googlemail.com
#
# test_daniel.py 13-Oct-2011
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

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

    def user_db_callback(db):
        eq(db.error, False)
        ioloop.stop()

    def session_callback(cookie, inner_response):
        response.append(inner_response)
        s.get('_users', user_db_callback)

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

    def add_user_cb(db):
        assert not db.error
        result['db'] = db
        ioloop.stop()

    # get the users db
    s.get('_users', add_user_cb)
    ioloop.start()

    # add a user
    salt = '123456'
    user = {'name': 'test', 'salt': salt, 'type': 'user', 'roles': []}
    user['password_sha'] = hashlib.sha1('test' + salt).hexdigest()
    result['db'].set('org.couchdb.user:test', user, add_user_callback)
    ioloop.start()

    # login
    s.session(session_callback, username="test", password="test")
    ioloop.start()

    # check for the cookie and user info
    eq(result['cookie'].startswith("AuthSession="), True)
    eq(result['session_info'], {u'ok': True, u'name': u'test', u'roles': []})
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
