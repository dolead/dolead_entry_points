from time import time

from tests.base import TestCase

from dolead_entry_points.client import DoleadEntryPointClient, Transport


HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;"
              "q=0.9,image/avif,image/webp,image/apng,*/*;"
    "q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
    "Dnt": "1",
    "Host": "httpbin.org",
    "Sec-Ch-Ua": "\" Not;A Brand\";v=\"99\", \"Google Chrome\";"
                 "v=\"91\", \"Chromium\";v=\"91\"",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
}


class TestClientSync():
    def test_sync_get(self):
        client = DoleadEntryPointClient(Transport.HTTP)
        example = client.call("https://httpbin.org/get", "get",
                              headers=HEADERS)
        assert example.status_code == 200

    def test_sync_get_gzipped(self):
        client = DoleadEntryPointClient(Transport.HTTP, gzip=True)
        example = client.call("https://httpbin.org/get", "get",
                              headers=HEADERS)
        assert example.status_code == 200
