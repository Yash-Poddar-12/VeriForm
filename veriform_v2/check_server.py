import urllib.request, urllib.error
try:
    urllib.request.urlopen('http://127.0.0.1:8000/trigger_400')
except urllib.error.HTTPError as e:
    print('Status:', e.code)
except Exception as ex:
    print('Error:', ex)
