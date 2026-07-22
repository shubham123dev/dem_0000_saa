import urllib.request
import json

def test():
    req1 = urllib.request.Request(
        'http://127.0.0.1:8043/auth/login',
        data=json.dumps({'email': 'test@gmail.com'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    res1 = urllib.request.urlopen(req1)
    cookie = res1.headers.get('Set-Cookie')

    req2 = urllib.request.Request(
        'http://127.0.0.1:8043/workplace/organizations/org_sandbox_001/agent/runs',
        data=json.dumps({'query': 'Summarize this workspace', 'client_request_id': 'req_123456789'}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Cookie': cookie}
    )
    try:
        res2 = urllib.request.urlopen(req2)
        print('STATUS:', res2.status)
        print('BODY:', res2.read().decode())
    except urllib.error.HTTPError as e:
        print('HTTP ERROR CODE:', e.code)
        print('HTTP ERROR BODY:', e.read().decode())

if __name__ == '__main__':
    test()
