import requests

resp = requests.get('https://2ch.hk/b/threads.json').json()
print(resp['threads'][0]['num'])
