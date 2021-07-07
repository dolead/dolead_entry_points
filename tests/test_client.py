import pytest
import asyncio
from time import time

from tests.base import TestCase

from dolead_entry_points.client import (request_http,
                                        request_celery,
                                        request_http_async)

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

class TestClientSync(TestCase):
    def test_sync_get(self):
        example = request_http("get", "https://httpbin.org/get", {},
                               headers=HEADERS, gzip=False)
        assert example.status_code == 200

    def test_sync_get_gzipped(self):
        example = request_http("get", "https://httpbin.org/get", {},
                               headers=HEADERS, gzip=True)
        assert example.status_code == 200


class TestClientAsync(TestCase):
    @pytest.mark.asyncio
    async def test_async_get(self):
        loop = asyncio.get_event_loop()
        example = await request_http_async("get", "https://httpbin.org/get", {},
                                           headers=HEADERS, gzip=False)
        assert example.status == 200
        return example

    @pytest.mark.asyncio
    async def test_async_get_gzipped(self):
        example = await request_http_async("get", "https://httpbin.org/get", {},
                                           headers=HEADERS, gzip=True)
        assert example.status == 200
        out = await example.text()
        return example

    @pytest.mark.asyncio
    async def test_concurrency(self):
        start = time()
        gather = await asyncio.gather(
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers=HEADERS)
        )
        end = time()
        total_run_time = end - start
        assert 2.0 > total_run_time
        assert gather
        assert len(gather)
        for e in gather:
            text = await e.text()
            assert e
            assert text

    @pytest.mark.asyncio
    async def test_run_one_by_one(self):
        start = time()
        await self.test_async_get()
        await self.test_async_get()
        await self.test_async_get()
        await self.test_async_get_gzipped()
        await self.test_async_get_gzipped()
        await self.test_async_get_gzipped()
        await self.test_async_get()
        await self.test_async_get()
        await self.test_async_get()
        await self.test_async_get_gzipped()
        await self.test_async_get_gzipped()
        await self.test_async_get_gzipped()
        end = time()
        total_run_time = end - start
        assert 2.0 < total_run_time
