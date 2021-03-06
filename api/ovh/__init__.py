# Based on ovh_app of Antoine Sirinelli <antoine@monte-stello.com> 
# https://github.com/asirinelli/ovh_app

import requests
import json
import time
import hashlib
import os
import re

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.append('/')

from alkivi.common import logger
from alkivi.common.logger import Logger

# Custom debug for API low level
DEBUG = False

class APIError(Exception):
    def __init__(self, status_code, r):
        self.status_code = status_code
        self.response = r
    def __str__(self):
        error = self.response.json
        return 'httpCode: %s errorCode: %s message: %s' % (error['httpCode'], error['errorCode'], error['message'])


class API:

    def __init__(self, useData, accessRules = [],
                 url='https://api.ovh.com/1.0'):

        self.application = None
        self.secret      = None
        self.consumerKey = None
        self.accessRules = accessRules
        self.url         = url


        # Going to extract data from /alkivi/.secureData
        base = '/alkivi/.secureData/api_ovh/'
        file = base + useData

        # Test file is ok
        if(not(os.path.exists(file))):
            Logger.instance().warning('Unable to fetch correct file. Check that %s exists and is readable' % (file))
            raise

        # Open file
        f = open(file)

        # Check syntax
        rx = re.compile('^(.*?):(.*?):(.*?)$')
        for line in f:
            m = rx.search(line)
            if(m):
                self.application, self.secret, self.consumerKey = m.groups()

        # Check that we are good to go
        if(not(self.application) or not(self.secret) or not(self.consumerKey)):
            Logger.instance().warning('Did not find any file that contains correct data, bazinga')
            raise
        else:
            self.drift       = self.get_drift()

    def get(self, path, params=None):
        extra=[]
        if(params):
            for key, value in params.iteritems():
                extra.append(key+'='+value)

        if(len(extra) > 0):
            path = path + '?' + '&'.join(extra)

        if(DEBUG):
            Logger.instance().debug("[API OVH] Going to %s on %s" % ('get', path))
            
        return self._ovh_req(path, "GET", self.consumerKey)
    
    def post(self, path, params):
        if(DEBUG):
            Logger.instance().debug("[API OVH] Going to %s on %s with params : " % ('post', 'path'), params)

        return self._ovh_req(path, "POST", self.consumerKey, params)

    def delete(self, path):
        if(DEBUG):
            Logger.instance().debug("Going to %s on %s" % ('delete', path))

        return self._ovh_req(path, "DELETE", self.consumerKey)

    def put(self, path, params):
        if(DEBUG):
            Logger.instance().debug("[API OVH] Going to %s on %s" % ('put', path))

        return self._ovh_req(path, "PUT", self.consumerKey, params)

    def request_CK(self, redirection=None):
        headers = { 'Content-type': 'application/json',
                    'X-Ovh-Application': self.application}
        params = { 'accessRules': self.accessRules}

        if redirection:
            params['redirection'] = redirection

        q = requests.post(self.url+'/auth/credential', headers=headers, data=json.dumps(params))
        print q.json

    def get_drift(self):
        t_ovh = int(requests.get(self.url+'/auth/time').text)
        t_here = int(time.time())
        return t_ovh - t_here

    def _ovh_req(self, path, req_type, CK, params=None):
        now = str(int(time.time()) + self.drift)

        if params:
            data = json.dumps(params)
        else:
            data = ""

        url = self.url+path

        s1 = hashlib.sha1()
        s1.update("+".join([self.secret, CK, req_type, url, data, now]))
        sig = "$1$" + s1.hexdigest()

        headers = { 'Content-type': 'application/json',
                    'X-Ovh-Application':  self.application,
                    "X-Ovh-Consumer": CK,
                    'X-Ovh-Timestamp': now,
                    "X-Ovh-Signature": sig,
                    }

        if req_type == "GET":
            r = requests.get(url, headers=headers)
        elif req_type == "POST":
            r = requests.post(url, headers=headers, data=data)
        elif req_type == "DELETE":
            r = requests.delete(url, headers=headers)
        elif req_type == "PUT":
            r = requests.put(url, headers=headers, data=data)

        if r.status_code != 200:
            raise APIError(int(r.status_code), r)

        return r.json

