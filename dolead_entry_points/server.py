import collections
import json
import logging
from functools import wraps
from gzip import GzipFile
from io import BytesIO

from flasgger import Swagger, swag_from
from flask import request as flask_request
from werkzeug.exceptions import ExpectationFailed
from dolead_entry_points import utils, swagger

logger = logging.getLogger(__name__)


def set_default_app(**kwargs):
    utils.DEFAULTS.update(kwargs)
    if 'flask_app' in kwargs:
        Swagger(kwargs['flask_app'])


def map_in_celery(func, qualname, **kwargs):
    "Will map a standard method to a task in celery"
    celery_kwargs = {'name': qualname}
    celery_kwargs.update(kwargs)
    celery_app = utils.kwargs_or_defaults('celery_app', kwargs)
    if celery_app is None:
        logger.debug('No celery_app provided, no celery for %s', qualname)
        return

    @celery_app.task(bind=True, **celery_kwargs)
    @wraps(func)
    def celery_wrapper(self, *args, **kwargs):
        CodeExecCtxCls = utils.kwargs_or_defaults('celery_code_exec_ctx_cls',
                                                  kwargs)
        formatter = utils.kwargs_or_defaults('celery_formatter', kwargs)
        with CodeExecCtxCls(self.request):
            result = formatter(func(*args, **kwargs))
        return result
    return celery_wrapper


def map_in_flask(func, name, qualname, method, **kwargs):
    "Will map a standard method to a name and the according route in flask"
    if not utils.DEFAULTS.get('flask_app'):
        logger.debug('No flask_app provided, no flask for %s', name)
        return

    @wraps(func)
    def flask_wrapper():
        if flask_request.content_encoding == 'gzip':
            bytesio = BytesIO()
            bytesio.write(flask_request.data)
            bytesio.seek(0)
            with GzipFile(fileobj=bytesio, mode='r') as gzipfile:
                flask_request.data = gzipfile.read()
        if flask_request.content_type == 'application/json':
            if isinstance(flask_request.data, bytes):
                flask_request.data = flask_request.data.decode('utf8')
            try:
                flask_request.data = json.loads(flask_request.data)
            except ValueError:
                logger.exception('an error occured while deserializing')
                flask_request.data = {}

        CodeExecCtxCls = utils.kwargs_or_defaults(
            'flask_code_exec_ctx_cls', kwargs)
        if not flask_request.data:
            flask_request.data = {}
        formatter = utils.kwargs_or_defaults('flask_formatter', kwargs)
        try:
            with CodeExecCtxCls(flask_request):
                return formatter(func(**flask_request.data))
        except TypeError as error:
            logger.exception("something went wrong when executing %r %r %r %r",
                             func, name, qualname, method)
            raise ExpectationFailed(*error.args) from error

    flask_app = utils.kwargs_or_defaults('flask_app', kwargs)
    flask_app.add_url_rule(utils.to_http_path(name), qualname,
                           flask_wrapper, methods=[method])


def serv(prefix, route='', method='get', **kwargs):
    """A decorator for serving service methods"""

    def metawrapper(func):
        path = utils.gen_path(prefix=prefix, route=route)
        qualname = utils.gen_qn(prefix=prefix, route=route, method=method,
                                **kwargs)

        map_in_celery(func, qualname, **kwargs)

        func, specs = swagger.process_prototype(prefix, func)
        func = swag_from(specs=specs)(func)

        map_in_flask(func, path, qualname, method, **kwargs)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return metawrapper


__all__ = ['serv']
