import json
import logging
from io import BytesIO
from gzip import GzipFile
from functools import wraps
from dolead_entry_points.utils import get_unique_name, kwargs_or_defaults

logger = logging.getLogger(__name__)


def _map_in_celery(func, qualname, **kwargs):
    "Will map a standard method to a task in celery"
    celery_kwargs = {'name': qualname}
    celery_kwargs.update(kwargs)
    celery_app = kwargs_or_defaults('celery_app', kwargs)
    if celery_app is None:
        logger.debug('No celery_app provided, no celery for %s', qualname)
        return

    @celery_app.task(bind=True, **celery_kwargs)
    @wraps(func)
    def celery_wrapper(self, *args, **kwargs):
        CodeExecCtxCls = kwargs_or_defaults('celery_code_exec_ctx_cls', kwargs)
        formatter = kwargs_or_defaults('celery_formatter', kwargs)
        with CodeExecCtxCls(self.request):
            result = formatter(func(*args, **kwargs))
        return result
    return celery_wrapper


def _map_in_flask(func, path, qualname, method, **kwargs):
    "Will map a standard method to a name and the according route in flask"
    if not kwargs_or_defaults('flask_app', kwargs):
        logger.debug('No flask_app provided, no flask for %s', path)
        return

    def flask_wrapper():
        from flask import request
        if request.content_encoding == 'gzip':
            bytesio = BytesIO()
            bytesio.write(request.data)
            bytesio.seek(0)
            with GzipFile(fileobj=bytesio, mode='r') as gzipfile:
                request.data = gzipfile.read()
        if request.content_type == 'application/json':
            if isinstance(request.data, bytes):
                request.data = request.data.decode('utf8')
            try:
                request.data = json.loads(request.data)
            except ValueError:
                logger.exception('an error occured while deserializing')
                request.data = {}

        CodeExecCtxCls = kwargs_or_defaults('flask_code_exec_ctx_cls', kwargs)
        if not request.data:
            request.data = {}
        formatter = kwargs_or_defaults('flask_formatter', kwargs)
        try:
            with CodeExecCtxCls(request):
                return formatter(func(**request.data))
        except TypeError as error:
            logger.exception("something went wrong when executing %r %r %r %r",
                             func, path, qualname, method)
            from werkzeug.exceptions import ExpectationFailed
            raise ExpectationFailed(*error.args)

    flask_app = kwargs_or_defaults('flask_app', kwargs)
    flask_app.add_url_rule(path, qualname, flask_wrapper, methods=[method])


def serv(*args, method='get', **kwargs):
    """A decorator for serving service methods"""

    def metawrapper(func):
        _, qualname, path, method = get_unique_name(*args,
            method=method, kwargs=kwargs)

        _map_in_celery(func, qualname, **kwargs)
        _map_in_flask(func, path, qualname, method, **kwargs)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return metawrapper
