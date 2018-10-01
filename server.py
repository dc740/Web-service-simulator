# -*- coding: utf-8 -*-
"""
@author: Emilio Moretti
    Copyright 2012 Emilio Moretti <emilio.morettiATgmailDOTcom>
    This program is distributed under the terms of the GNU Lesser General Public License.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU  Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import sys
import socket
import re
import logging
import uuid
import random
import base64
from urlparse import urlparse


try:
    from urlparse import parse_qs
except:
    from cgi import parse_qs
try:
    import json
except ImportError:
    import simplejson as json
    
'''
Custom web server implementation
'''
bufsize = 4048


class Headers(object):
    def __init__(self, headers):
        self.__dict__.update(headers)

    def __getitem__(self, name):
        return getattr(self, name)

    def get(self, name, default=None):
        return getattr(self, name, default)

    def items(self):
        self.__dict__.iter


class Request(object):
    header_re = re.compile(r'([a-zA-Z-]+):? ([^\r|^\n]+)', re.M)

    def __init__(self, sock):
        header_off = -1
        data = ''
        while header_off == -1:
            data += sock.recv(bufsize)
            header_off = data.find('\r\n\r\n')
        self.header_string = data[:header_off]
        self.content = data[header_off + 4:]

        lines = self.header_re.findall(self.header_string)
        self.method, path = lines.pop(0)
        path, protocol = path.split(' ')
        logging.info("New request\n Path:" + path + " Protocol:" + protocol)
        self.headers = Headers(
            (name.lower().replace('-', '_'), value)
            for name, value in lines
        )

        if self.method in ['POST', 'PUT']:
            content_length = int(self.headers.get('content_length', 0))
            while len(self.content) < content_length:
                self.content += sock.recv(bufsize)

        parsed_path = urlparse(path)
        self.query = parsed_path[4]
        self.params = parsed_path[3]
        self.path = parsed_path[2]


'''
Web service simulator logic
'''
responseMap = {}
replaceMap = {}
counters = {}
globalVars = {}
random.seed()


def processPostParam(request, dataKey, data, replace_key, value):
    # let's get the value of the post param from the data
    params = parse_qs(request.content)
    try:
        # WARNING! get the first value. the post params should not send several
        # values!
        replace_value = params[value][0]
        return str(data).replace("{" + replace_key + "}", replace_value)
    except KeyError:
        logging.error('Post param not sent to replace ' +
                      replace_key +
                      '. Returning data without modification.')
        return str(data)


def processCounter(request, dataKey, data, replace_key, value):
    '''
    Replace the key by an internal counter incremented by one on each call
    '''
    try:
        counter_value = counters[value]
        counter_value += 1
    except KeyError:
        counter_value = 0

    counters[value] = counter_value
    return str(data).replace("{" + replace_key + "}", str(counter_value))


def processRandomUUID(request, dataKey, data, replace_key, value):
    '''
    Replace key with a random UUID
    '''
    return str(data).replace("{" + replace_key + "}", str(uuid.uuid4()))


def processRandomInteger(request, dataKey, data, replace_key, value):
    '''
    Replace key witha  random integer between A and B.
    value must have the following format: a-b
    where a and b are integers
    '''
    values = value.split('-')
    try:
        a = int(values[0])
        b = int(values[1])
        return str(data).replace("{" + replace_key + "}",
                                     str(random.randint(a, b)))
    except ValueError:
        logging.error(
            'Invalid random int range. '
            'Returning data without modification.')
        return str(data)


def processCustomParser(request, dataKey, data, replace_key, value):
    variables = globalVars
    try:
        code = base64.b64decode(str(value))
        exec code
        return data
    except Exception, e:
        logging.error('Error running custom code: %s\n'
                      'Custom code:\n%sdata:%s' % (
                          e, code, data))


# Oks, I have to admint that this is a little cryptic for those not used to python
# we basically use a dictionary as a replacement for a switch statement :)
def preProcessData(request, responseKey, data, replace_key, value,
                       key_type):
    try:
        return {'postParam': processPostParam,
                'counter': processCounter,
                'randomUUID': processRandomUUID,
                'randomInt': processRandomInteger,
                'custom': processCustomParser}[key_type](request, responseKey,
                                                         data, replace_key,
                                                         value)
    except KeyError, e:
        logging.error(str(
            key_type) + ' is not a valid key. Try '
            'post_params|counter|custom|randomUUID|randomInt|custom. '
            'Error: %s' % e)


def requestProcessor(request, responseKey):
    data = request.content
    logging.info('---------------------------------')
    logging.info(str(responseKey))
    logging.info('---------------------------------')
    logging.info('Received: ' + str(data))
    header, response = responseMap[responseKey]
    try:
        replace_keys = replaceMap[responseKey]
        for key in replace_keys:
            header = preProcessData(
                request, responseKey, header, key['key'], key['value'],
                key['type'])
            response = preProcessData(
                request, responseKey, response, key['key'], key['value'],
                key['type'])
    except KeyError:
        pass
    final_response = str(header) + '\n' + str(response)
    logging.info('Response: ' + final_response)
    return final_response


def requestSetter(header, data, responseKey, replace_keys=None):
    responseMap[responseKey] = (str(header), str(data))
    if (replace_keys):
        replaceMap[responseKey] = replace_keys
    response = 'Updated response for ' + \
        str(responseKey) + ' to:\n' + str(data)
    logging.info(str(response))
    return response


def buildKey(method, endpoint):
    key = method
    if (method.lower() == 'post'):
        key = 'POST:'
    elif (method.lower() == 'get'):
        key = 'GET:'
    elif (method.lower() == 'put'):
        key = 'PUT:'
    elif (method.lower() == 'delete'):
        key = 'DELETE:'
    key = key + endpoint
    return key


def registerResponse(header, response, endpoint, method, replace_keys=None):
    key = buildKey(method, endpoint)
    return requestSetter(header, response, key, replace_keys)


def endpoint_register(socket, request):
    try:
        data = json.loads(request.content)
    except ValueError, e:
        logging.error(
            'Fatal error, invalid json sent to the register endpoint: %s' % e)
        return

    header = data['header']
    endpoint = data['endpoint']
    method = data['method']

    key = buildKey(method, endpoint)

    try:
        response = data['response']
    except KeyError:
        response = None
    try:
        replace_keys = data['replaceKeys']
    except KeyError:
        replace_keys = None

    def callback(sock, req):
        sock.send(str(requestProcessor(req, key)))

    if (method == 'post'):
        post_endpoints[endpoint] = callback
    if (method == 'get'):
        get_endpoints[endpoint] = callback
    if (method == 'put'):
        put_endpoints[endpoint] = callback
    if (method == 'delete'):
        delete_endpoints[endpoint] = callback
    if (response):
        if (type(response) is dict or type(response) is list):
            registerResponseResult = registerResponse(str(header),
                                                      json.dumps(response),
                                                      endpoint, method,
                                                      replace_keys)
        else:
            registerResponseResult = registerResponse(str(header),
                                                      base64.b64decode(response),
                                                      endpoint, method,
                                                      replace_keys)
    else:
        registerResponseResult = registerResponse(str(header), '', endpoint, method, replace_keys)

    socket.send('Registered endpoint ' + str(endpoint) +
                ' \n' + str(registerResponseResult))


post_endpoints = {'/register': endpoint_register}
put_endpoints = {}
get_endpoints = {}
delete_endpoints = {}


if __name__ == '__main__':

    # we don't handle arguments to avoid having to check if optparse or argparse are available
    # if there is an argument then we print it encoded in base64
    if (len(sys.argv) > 1):
        print(base64.b64encode(str(sys.argv[1])))
        exit(1)
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)-8s '
        '[%(filename)s:%(lineno)d] %(message)s',
        filename='./ws_simulator.log', level=logging.DEBUG)
    acceptor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    acceptor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )
    acceptor.bind(('', 2501))
    acceptor.listen(10)

    while True:
        sock, info = acceptor.accept()
        request = Request(sock)
        if (request.method == 'POST'):
            method_handler = post_endpoints
        elif (request.method == 'GET'):
            method_handler = get_endpoints
        elif (request.method == 'PUT'):
            method_handler = put_endpoints
        elif (request.method == 'DELETE'):
            method_handler = delete_endpoints

        try:
                handler = method_handler[request.path]
                handler(sock, request)
        except Exception, e:
                logging.exception("Failed to handle the request.")

        sock.close()
