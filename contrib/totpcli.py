#!/usr/bin/python -tt
##
# Copyright (C) 2012 by Konstantin Ryabitsev and contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
import os
import sys
import syslog
import logging

from optparse import OptionParser

import totpcgi
import totpcgi.backends

import ConfigParser
import json

syslog.openlog('totpcli', syslog.LOG_PID, syslog.LOG_AUTH)

def bad_request(why, use_json):
    if use_json:
        js = {
            'success' : False,
            'message' : why
        }
        json.dump(js, sys.stdout)

    else:
        output = 'ERR\n' + why + '\n'
        sys.stdout.write(output)

    sys.exit(1)

def climain():
    usage = '''usage: %prog [--config totpcgi.conf --json]
    Use this tool to interact with totpcgi via the command line
    instead of via the CGI interface.
    '''

    parser = OptionParser(usage=usage, version='0.1')
    parser.add_option('-c', '--config', dest='config_file',
            default='/etc/totpcgi/totpcgi.conf',
            help='Path to totpcgi.conf (default=%default)')
    parser.add_option('-j', '--json', dest='use_json', action='store_true',
            default=False,
            help='Input and output JSON (default=%default)')

    (opts, args) = parser.parse_args()
    config = ConfigParser.RawConfigParser()
    config.read(opts.config_file)

    require_pincode = config.getboolean('main', 'require_pincode')
    success_string  = config.get('main', 'success_string')

    backends = totpcgi.backends.Backends()

    try:
        backends.load_from_config(config)
    except totpcgi.backends.BackendNotSupported, ex:
        syslog.syslog(syslog.LOG_CRIT,
                'Backend engine not supported: %s' % ex)
        sys.exit(1)

    if opts.use_json:
        try:
            js = json.load(sys.stdin)
        except:
            bad_request('Error parsing json', True)

        must_keys = ('user', 'token')
        for must_key in must_keys:
            if must_key not in js:
                bad_request("Missing field: %s" % must_key, True)

        user  = js['user']
        token = js['token']

    else:
        req = sys.stdin.read()
        req = req.strip()
        try:
            (user, token) = req.split('\n')
        except:
            bad_request('Format must be username\\ntoken', False)

        user  = user.strip()
        token = token.strip()

    ga = totpcgi.GoogleAuthenticator(backends, require_pincode)

    try:
        status = ga.verify_user_token(user, token)
    except Exception, ex:
        syslog.syslog(syslog.LOG_NOTICE,
            'Failure: user=%s, mode=totpcli, host=localhost, message=%s' % (
                user, str(ex)))
        bad_request(str(ex), opts.use_json)

    syslog.syslog(syslog.LOG_NOTICE,
        'Success: user=%s, mode=totpcli, host=localhost, message=%s' % (
            user, status))

    if opts.use_json:
        js = {
            'success' : True,
            'message' : status,
        }
        json.dump(js, sys.stdout)

    else:
        sys.stdout.write(success_string)

if __name__ == '__main__':
    climain()

