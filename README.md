This is a port written in python for a web service simulator that was original written in javascript by Aron Racho. This version is a full rewrite with several extra features:

    Supports plain text responses (you can return a web page, or even test invalid JSON objects). The original tool was used to reply json only.
    You can specify the return header to simulate parameters and return codes like 200, 401, 403, etc etc .
    You can specify dynamic replies based on post parameters, random numbers, UUIDs or counters
    You can write your own python code and send it in the registration post to modify the replies dynamically, connect to a database, or whatever you want. There is no limit.


The server is attached. Just run python server.py

It runs on port 2501 (you can easily change this).
It logs requests and responses to ./ws_simulator.log

# Basic usage:

## Simulating HTTP errors:

### Gateway timeout:
     curl -X POST -H'Content-Type: application/json' -d'{
                "endpoint": "/timeout",
                "method": "get",
                "header":"HTTP/1.1 504 Gateway Timeout\nDate: Fri, 20 June 2008 20:40:34 GMT\nServer:SING\nX-Powered-By: emilio\nConnection:close\nContent-Type: text/plain\n"
            }' http://localhost:2501/register
### Redirect:
Encode the response (not the header, just the body)
    python server.py "The URL has moved <a href=\"http://www.example.com\">"
the command returns the encoded base64 string: VGhlIFVSTCBoYXMgbW92ZWQgPGEgaHJlZj0iaHR0cDovL3d3dy5leGFtcGxlLmNvbSI+

    curl -X POST -H'Content-Type: application/json' -d'{
                "endpoint": "/example",
                "method": "get",
                "header":"HTTP/1.1 302 Found\nDate: Fri, 20 June 2008 20:40:34 GMT\nServer:SING\nX-Powered-By: emilio\nLocation: http://www.example.com\nConnection:close\nContent-Type: text/plain\n",
                "response":"VGhlIFVSTCBoYXMgbW92ZWQgPGEgaHJlZj0iaHR0cDovL3d3dy5leGFtcGxlLmNvbSI+"
            }' http://localhost:2501/register
 
1) post to register a new web service specifying the new endpoint and response
2) use the new endpoint as a real web service

# Advanced usage:
## Replace Keys
Dynamic replies are supported by specifying replaceKeys. Valid replaceKeys:
#### postParam:
replaces the key by the specified post parameter
#### counter:
initializes an internal counter (you can initialize as many as you want), replaces the key by the current value, and increases the internal counter by one
#### randomInt:
replaces the key by a random integer in the "X-Y" range. ie: "4-25" to return a random integer between 4 and 25
#### randomUUID:
replaces the key by a newly generated UUID
#### custom:
executes the python code sent. You can basically do anything you want here. The code MUST be encoded in base64. You can store global variables in the "variables" map. The endpoint response is available in the "response" variable as string. ie:

## Examples

The script supports two modes:
#### Plain text: We send the response as a base64 encoded string.
#### JSON: We send the response directly as a JSON object

## Echo service
The first example is in Plain Text mode, let's create a custom code to process a reply that simply returns the request data:

    echo 'variables["sample_var1"] = str(request.header_string) + "\n\n" + str(request.content)
    data=data.replace("{1}",variables["sample_var1"])' | base64 -w0

The output is:

    dmFyaWFibGVzWyJzYW1wbGVfdmFyMSJdID0gc3RyKHJlcXVlc3QuaGVhZGVyX3N0cmluZykgKyAiXG5cbiIgKyBzdHIocmVxdWVzdC5jb250ZW50KQpkYXRhPWRhdGEucmVwbGFjZSgiezF9Iix2YXJpYWJsZXNbInNhbXBsZV92YXIxIl0pCg==

Since this is a plain response, and not a json response, we need the output from the base64 command for the response. In this example our response is all that the custom code generates for the key {1}. Which means our entire response is actually {1}.
Lets encode it:

    echo '{1}' | base64 -w0
    ezF9Cg==



The final step is to register an endpoint with our code that uses custom code to replace '{1}' from our plain text response:

    curl -X POST -H'Content-Type: application/json' -d'
    {
    "endpoint": "/echo",
    "method": "post",
    "header":"HTTP/1.1 200 OK\nDate: Fri, 20 June 2008 20:40:34 GMT\nServer:SING\nX-Powered-By: emilio\nConnection:close\n",
    "replaceKeys":[{"key":"1","type":"custom","value":"dmFyaWFibGVzWyJzYW1wbGVfdmFyMSJdID0gc3RyKHJlcXVlc3QuaGVhZGVyX3N0cmluZykgKyAiXG5cbiIgKyBzdHIocmVxdWVzdC5jb250ZW50KQpkYXRhPWRhdGEucmVwbGFjZSgiezF9Iix2YXJpYWJsZXNbInNhbXBsZV92YXIxIl0pCg=="}],
    "response": "ezF9Cg=="
    }' http://localhost:2501/register

Lets test it:

    curl -X POST -H'Content-Type: application/json' -d'Hola mundo' http://localhost:2501/echo

## JSON keys replacement
In this example we will use all possible key replacements:

    curl -X POST -H'Content-Type: application/json' -d'
            {
                "endpoint": "/test",
                "method": "post",
                "header":"HTTP/1.1 200 OK\nDate: Fri, 20 June 2008 20:40:34 GMT\nServer:SING\nX-Powered-By: emilio\nConnection:close\nContent-Type: application/json\n",
                "replaceKeys":[{"key":"1","type":"postParam","value":"firstpostparam"},
                               {"key":"2","type":"postParam","value":"secondpostparam"},
                               {"key":"3","type":"counter","value":"internalCounter1"},
                               {"key":"4","type":"randomInt","value":"0-65535"},
                               {"key":"5","type":"randomUUID","value":""},
                               {"key":"6","type":"custom","value":"dmFyaWFibGVzWyJoZWxsbyJdPSJIZWxsbyBXb3JsZCIKZGF0YT1kYXRhLnJlcGxhY2UoIns2fSIsdmFyaWFibGVzWyJoZWxsbyJdKQo="}],
                "response": {
                    "firstPostParam": "{1}",
                    "secondPostParam": "{2}",
                    "myCounter": "{3}",
                    "firstPostAgain": "{1}",
                    "randomInteger":"{4}",
                    "randomUUID":"{5}",
                    "customCode":"{6}"
                }
            }' http://localhost:2501/register


Now that you have configured an endpoint, test if it works:

    curl -v -X POST http://localhost:2501/test -d "firstpostparam=myvalue1&secondpostparam=myvalue2"

it should return the response with the parameters {x} replaced by the replace keys.




# Final notes
## VERY IMPORTANT:
1. Plain text responses MUST be encoded in base64. Read the "Redirect" example to see the fastest way to do it (the script already includes code to encode strings).
2. replaceKeys is NOT required. If you don't specify it, the server will always return the static response you sent.
3. response is NOT required. If you don't specify it the header will be returned.
4. Be careful when you write your own response parser, you may break the reply. Try to double check your python code.

## Custom code details:
1. The "custom" code is run after applying all other key replacements to the response.
2. You can get URL params by accessing "request.params" inside your custom code
3. You can share variables between each request, just store them in the dictionary "globalVars"
4. Headers are stored in request.headers, and a plain text version is easily accesible with request.header_string
5. The original contents of the request can be accessed with request.content

Copyright 2018 Emilio Moretti <emilio.morettiATgmailDOTcom>
This program is distributed under the terms of the GNU Lesser General Public License.
