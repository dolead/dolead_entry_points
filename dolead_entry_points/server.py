import collections
import inspect
import json
import logging
from enum import Enum
from functools import wraps
from gzip import GzipFile
from io import BytesIO
from typing import Dict, List, get_type_hints

from flasgger import Swagger, swag_from
from flask import jsonify
from flask import request as flask_request
from werkzeug.exceptions import ExpectationFailed

logger = logging.getLogger(__name__)

FLASK_TO_SWAGGER = {
    int: "integer",
    str: "string",
    bool: "boolean",
    dict: "object",
    Dict: "object",
    float: "number",
    list: "array",
    List: "array",
}


class CodeExecContext:

    def __init__(self, request):
        self.request = request

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


# this is for the main script to leave a reference to the app in
_DEFAULTS = {'flask_app': None,
             'flask_formatter': jsonify,
             'flask_code_exec_ctx_cls': CodeExecContext,
             'task_prefix': 'dolead-entry-points',
             'celery_app': None,
             'celery_formatter': lambda x: x,
             'celery_code_exec_ctx_cls': CodeExecContext}


def kwargs_or_defaults(key, kwargs):
    if key in kwargs:
        return kwargs[key]
    return _DEFAULTS[key]


def set_default_app(**kwargs):
    _DEFAULTS.update(kwargs)
    if 'flask_app' in kwargs:
        Swagger(kwargs['flask_app'])


def _gen_path(prefix, route='', **kwargs):
    "Generate a path (aimed at flask, path may not be unique"
    return ("%s.%s" % (prefix, route or '')).strip('.')


def _gen_qn(*args, **kw):
    "Generate a qualname, should be unique"
    task_prefix = kwargs_or_defaults('task_prefix', kw)
    if len(set(['prefix', 'method']).intersection(kw)) == 2:
        return "%s.%s.%s" % (task_prefix, _gen_path(**kw), kw['method'])
    return ".".join([task_prefix] + list(args))


def map_in_celery(func, qualname, **kwargs):
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


def generic_task(*decorator_args, **decorator_kwargs):
    def metawrapper(func):
        return map_in_celery(func, _gen_qn(func.__name__, **decorator_kwargs),
                             **decorator_kwargs)

    if len(decorator_args) == 1 \
            and not decorator_kwargs \
            and isinstance(decorator_args[0], collections.Callable):
        return metawrapper(decorator_args[0])

    return metawrapper


def map_in_flask(func, name, qualname, method, **kwargs):
    "Will map a standard method to a name and the according route in flask"
    if not _DEFAULTS.get('flask_app'):
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

        CodeExecCtxCls = kwargs_or_defaults('flask_code_exec_ctx_cls', kwargs)
        if not flask_request.data:
            flask_request.data = {}
        formatter = kwargs_or_defaults('flask_formatter', kwargs)
        try:
            with CodeExecCtxCls(flask_request):
                return formatter(func(**flask_request.data))
        except TypeError as error:
            logger.exception("something went wrong when executing %r %r %r %r",
                             func, name, qualname, method)
            raise ExpectationFailed(*error.args) from error

    name = ("/%s" % name).replace('.', '/')
    flask_app = kwargs_or_defaults('flask_app', kwargs)
    flask_app.add_url_rule(name, qualname, flask_wrapper, methods=[method])
    if not name.endswith('/'):
        flask_app.add_url_rule(name + "/", qualname,
                               flask_wrapper, methods=[method])


def _to_swagger_type(type_hint):
    if type_hint in FLASK_TO_SWAGGER:
        return FLASK_TO_SWAGGER[type_hint]
    if isinstance(type_hint, Enum):
        enum_types = [type(e.value) for e in type_hint]
        return FLASK_TO_SWAGGER[list(enum_types)[0]]
    try:
        return type_hint.__name__
    except AttributeError:
        return str(type_hint).lower()


def swag_specs_from_func(prefix, func):
    type_hints = get_type_hints(func)
    specs = {'description': func.__doc__ or func.__qualname__,
             'tags': [prefix], 'parameters': []}
    for param_name, type_hint in type_hints.items():
        if param_name == 'return':
            continue
        specs['parameters'].append({'name': param_name,
                                    'type': _to_swagger_type(type_hint)})
    if 'return' in type_hints:
        swagger_type = _to_swagger_type(type_hints['return'])
        specs['responses'] = {'200': {'schema': {'type': swagger_type}}}
    if inspect.ismethod(func):
        @wraps(func)
        def to_func(*args, **kwargs):
            return func(*args, **kwargs)
        return to_func, specs
    return func, specs


def serv(prefix, route='', method='get', **kwargs):
    """A decorator for serving service methods"""

    def metawrapper(func):
        path = _gen_path(prefix=prefix, route=route)
        qualname = _gen_qn(prefix=prefix, route=route, method=method, **kwargs)

        map_in_celery(func, qualname, **kwargs)

        func, specs = swag_specs_from_func(prefix, func)
        func = swag_from(specs=specs)(func)

        map_in_flask(func, path, qualname, method, **kwargs)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return metawrapper
