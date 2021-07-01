import pytest
import asyncio
from time import time

from tests.base import TestCase

from dolead_entry_points.client import (request_http,
                                        request_celery,
                                        request_http_async)


class TestClientSync(TestCase):
    def test_sync_get(self):
        example = request_http("get", "https://httpbin.org/get", {},
                               headers={}, gzip=False)
        assert example.status_code == 200

    def test_sync_get_gzipped(self):
        example = request_http("get", "https://httpbin.org/get", {},
                               headers={}, gzip=True)
        assert example.status_code == 200


class TestClientAsync(TestCase):
    @pytest.mark.asyncio
    async def test_async_get(self):
        loop = asyncio.get_event_loop()
        example = await request_http_async("get", "https://httpbin.org/get", {},
                                           headers={}, gzip=False)
        assert example.status == 200
        return example

    @pytest.mark.asyncio
    async def test_async_get_gzipped(self):
        example = await request_http_async("get", "https://httpbin.org/get", {},
                                           headers={}, gzip=True)
        assert example.status == 200
        out = await example.text()
        return example

    @pytest.mark.asyncio
    async def test_concurrency(self):
        start = time()
        gather = await asyncio.gather(
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={}),
            request_http_async(
                "get", "https://httpbin.org/get", {}, headers={})
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
