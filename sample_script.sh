#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

python3 $DIR/server.py &
SERVERPID=$!
sleep 0.2
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


echo
echo
echo
echo "##### Testing endpoint: http://localhost:2501/test ######"
curl -v -X POST http://localhost:2501/test -d "firstpostparam=myvalue1&secondpostparam=myvalue2"
echo
echo "##### Web service simulator initiated. ######"
read  -n 1 -p "Press any key to close..."
# Kill spawned python
kill $SERVERPID


