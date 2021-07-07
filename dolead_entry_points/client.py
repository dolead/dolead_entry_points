from dolead_entry_points.utils.json import default_handler
import json
import logging
import requests
from enum import Enum
from typing import Optional, Dict, List, Union
from io import BytesIO
from gzip import GzipFile
from copy import deepcopy
from aiohttp import ClientSession
from celery import Celery

from dolead_entry_points import utils


logger = logging.getLogger('dolead_entry_points')


class Transport(Enum):
    HTTP = 'HTTP'
    ASYNCIO = 'ASYNCIO'
    CELERY = 'CELERY'


class DoleadEntryPointClient:
    prefix = 'dop_'
    default_celery_config = {'countdown': 0, 'ignore_result': False}

    def __init__(self, transport: Transport = Transport.HTTP,
                 gzip: bool = True,
                 celery_config: Dict = None):
        self._transport = transport
        self._celery_config = celery_config or self.default_celery_config
        self.gzip = gzip
        self._depth: int = 0  # couting imbricated with on celery clients
        self.celery = None  # current live instance of celery
        self._celery_async_results: List = []

    def __enter__(self):
        """
        If an instance of celery is already present, will count one depth and
        do nothing.
        If celery absent, will instantiate it with the current key.
        return: the client instance
        """
        if self._transport is not Transport.CELERY:
            return self
        if self.celery:
            self._depth += 1
            return self
        celery_config = deepcopy(self._celery_config)
        celery_config['set_as_current'] = False
        self.celery = Celery(**celery_config)
        return self

    def __exit__(self, rtype, rvalue, traceback):
        """If we're back at the 0 depth, will close the current client and
        delete celery.
        """
        if self._transport is not Transport.CELERY:
            return
        if self._depth <= 0:
            for celery_async_result in self._celery_async_results:
                try:
                    celery_async_result.forget()
                except Exception:
                    logger.warning('something wrong happened trying to forget '
                                   'about %r', celery_async_result.id)
            try:
                # fix for a known leak of redis connection by celery
                # See : https://github.com/celery/celery/issues/4465
                self.celery.backend.client.connection_pool.disconnect()
            except Exception:
                logger.warning('%r pool cleaning went wrong', self)

            try:
                self.celery.backend.result_consumer.stop()
            except Exception:
                logger.warning('%r consumer cleaning went wrong', self)
            self.celery.close()
            del self.celery
            self.celery = None
        else:
            self._depth -= 1

    def _call_with_http(self, path: str, method: str, headers: dict, kwargs: dict):
        method = getattr(requests, method)
        data: Optional[Union[bytes, str]] = None
        if kwargs:
            data = json.dumps(
                kwargs, default={})
            headers['Content-Type'] = 'application/json'
            if self.gzip:
                headers['Content-Encoding'] = 'gzip'
                stringio = BytesIO()
                gzip_file = GzipFile(fileobj=stringio, mode='w')
                gzip_file.write(data.encode('utf8'))
                gzip_file.close()
                data = stringio.getvalue()
        return method(path, headers=headers, data=data)

    def _call_with_async_http(self, path: str, method: str, headers: dict, kwargs: dict):
        async def wrapper(path, method, headers, kwargs, gzip):
            async with ClientSession() as session:
                method = getattr(session, method)
                data: Optional[Union[bytes, str]] = None
                if kwargs:
                    data = json.dumps(
                        kwargs, default={})
                    headers['Content-Type'] = 'application/json'
                    if gzip:
                        headers['Content-Encoding'] = 'gzip'
                        stringio = BytesIO()
                        gzip_file = GzipFile(fileobj=stringio, mode='w')
                        gzip_file.write(data.encode('utf8'))
                        gzip_file.close()
                        data = stringio.getvalue()
            return await method(path, headers=headers, data=data)
        return wrapper(path, method, headers, kwargs, self.gzip)



    def _call_with_celery(self, uris_parts, method,
                          headers: dict, kwargs: dict):
        name = '.'.join([el for el in (self.worker, self.urn, uris_parts,
                                       method) if el]).replace('/', '.')

        @self.celery.task(name=name,
                          ignore_result=self._celery_ignore_result)
        def lambda_task(**kwargs):
            pass
        # trick to handle both celery 3 and 4
        headers = dict(headers=headers, **headers)

        async_result = lambda_task.apply_async(
            kwargs=kwargs, headers=headers,
            countdown=self._celery_countdown)
        if self._celery_ignore_result:
            # no forget for ignored result as it might try to reconnect
            return None
        self._celery_async_results.append(async_result)
        if 'async' in self._transport_method:
            return async_result
        return async_result.get(**self._transport_options)

    def call(self, path, method, custom_key=None, **kwargs):
        method = method.strip().lower()
        headers = {}
        context = {}
        try:
            from dolead_common.context import DoleadContext
            context.update(DoleadContext.get_current_context())
        except ImportError:
            pass
        try:
            from threaded_context import get_current_context
            context.update(get_current_context())
        except ImportError:
            pass
        if context:
            headers['DoleadContext'] = json.dumps(
                context, default={})
        if self._transport is Transport.HTTP:
            return self._call_with_http(path, method, headers, kwargs)
        elif self._transport is Transport.ASYNCIO:
            return self._call_with_async_http(path, method, headers, kwargs)
        elif self._transport is Transport.CELERY:
            # `custom_key` is an override of the "normal one", to allow context
            # management and still process the `custom_key`, we instantiate
            # another client and use it to perform the `custom_key` request
            if custom_key and self.key != custom_key:
                client = self.__class__(
                        transport=self._transport,
                        ignore_result=self._celery_ignore_result,
                        load_response_to_boiler=self.load_response_to_boiler,
                        countdown=self._celery_countdown,
                        **self._transport_options)
                client.key = custom_key
            else:
                client = self
            with client:
                return client._call_with_celery(path, method,
                                                headers, kwargs)
        else:
            raise NotImplementedError('Unknown transport %r'
                                      % self._transport_method)
