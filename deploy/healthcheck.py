from urllib.request import Request, urlopen

request = Request(
    "http://127.0.0.1:8000/",
    headers={"X-Forwarded-Proto": "https"},
    method="HEAD",
)
with urlopen(request, timeout=3) as response:
    if response.status != 200:
        raise SystemExit(1)
