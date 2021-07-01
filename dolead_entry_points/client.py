import requests
from io import BytesIO
from gzip import GzipFile
from copy import deepcopy
import json
import aiohttp
from dolead_entry_points.utils.json import default_handler


def request_http(method, url, payload, headers=None, gzip=True):
    method = getattr(requests, method)
    data = json.dumps(payload, default=default_handler)
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    if gzip:
        headers['Content-Encoding'] = 'gzip'
        stringio = BytesIO()
        gzip_file = GzipFile(fileobj=stringio, mode='w')
        gzip_file.write(data.encode('utf8'))
        gzip_file.close()
        data = stringio.getvalue()
    return method(url, headers=headers, data=data)


async def request_http_async(method, url, payload, headers=None, gzip=True):
    async with aiohttp.ClientSession() as session:
        method = getattr(session, method)
        data = json.dumps(payload, default=default_handler)
        if headers is None:
            headers = {}
        headers['Content-Type'] = 'application/json'
        if gzip:
            headers['Content-Encoding'] = 'gzip'
            stringio = BytesIO()
            gzip_file = GzipFile(fileobj=stringio, mode='w')
            gzip_file.write(data.encode('utf8'))
            gzip_file.close()
            data = stringio.getvalue()
        return await method(url, headers=headers, data=data)


def _import_object(name):
    if '.' not in name:
        return __import__(name)

    parts = name.split('.')
    obj = __import__('.'.join(parts[:-1]), None, None, [parts[-1]], 0)
    return getattr(obj, parts[-1])


def request_celery(config_path, worker, method, urn, uris_parts, payload,
                   headers=None, sync_result=True):
    from celery import Celery
    if headers is None:
        headers = {}
    config_source = _import_object(config_path)
    name = '.'.join([el for el in (worker, urn, uris_parts, method) if el]
                    ).replace('/', '.')
    with Celery(config_source=config_source,
                set_as_current=False) as celery:
        with celery.connection():
            @celery.task(name=name)
            def lambda_task(**kwargs):
                pass
            async_result = lambda_task.apply_async(kwargs=payload,
                                                   headers=headers)
            if not sync_result:
                return async_result
            else:
                # FIXME: This doesn't seem right
                r = async_result.get(**self.transport_options)
                result = deepcopy(r)
                try:
                    async_result.forget()
                except Exception:
                    pass
                return result
