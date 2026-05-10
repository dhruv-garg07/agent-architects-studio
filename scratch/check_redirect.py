import requests
r = requests.get('https://themanhattanproject.ai', allow_redirects=False)
print(f"Status: {r.status_code}")
print(f"Headers: {r.headers}")
if 'Location' in r.headers:
    print(f"Redirects to: {r.headers['Location']}")
