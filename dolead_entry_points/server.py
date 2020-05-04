import json
import logging
import collections
from io import BytesIO
from gzip import GzipFile
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


class CodeExecContext():

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
             'restx_api': None,
             'task_prefix': 'core',
             'celery_app': None,
             'celery_formatter': lambda x: x,
             'celery_code_exec_ctx_cls': CodeExecContext}

NAMESPACES = {}


def kwargs_or_defaults(key, kwargs):
    if key in kwargs:
        return kwargs[key]
    return _DEFAULTS[key]


def set_default_app(**kwargs):
    _DEFAULTS.update(kwargs)


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
                             func, name, qualname, method)
            from werkzeug.exceptions import ExpectationFailed
            raise ExpectationFailed(*error.args)

    name = ("/%s" % name).replace('.', '/')
    flask_app = kwargs_or_defaults('flask_app', kwargs)
    flask_app.add_url_rule(name, qualname, flask_wrapper, methods=[method])
    if not name.endswith('/'):
        flask_app.add_url_rule(name + "/", qualname,
                               flask_wrapper, methods=[method])


def map_in_restx(func, prefix, route, method, **kwargs):
    # import Resource, manage namespaces
    from flask_restx import Resource
    restx_api = _DEFAULTS.get('restx_api')
    prefix = prefix or 'api'
    if prefix not in NAMESPACES:
        NAMESPACES[prefix] = restx_api.namespace(prefix)
    namespace = NAMESPACES[prefix]

    # generate a new resource
    @wraps(func)
    def wfunc(self, *args, **kwargs):
        # need to wrap to get rid of 'self'
        # need @wraps to keep docstrings
        return func(*args, **kwargs)
    Res = type('Resource_' + func.__name__, (Resource,),
               {method: wfunc})
    res = Res()
    res.__name__ = res.__class__.__name__

    # register resource
    path = "/" + _gen_path(prefix='', route=route)
    namespace.add_resource(res, path)
    return res


def serv(prefix, route='', method='get', **kwargs):
    """A decorator for serving service methods"""

    def metawrapper(func):
        path = _gen_path(prefix=prefix, route=route)
        qualname = _gen_qn(prefix=prefix, route=route, method=method, **kwargs)

        map_in_celery(func, qualname, **kwargs)
        if _DEFAULTS.get('restx_api', None) is not None:
            map_in_restx(func, prefix, route, method, **kwargs)
            return func
        else:
            map_in_flask(func, path, qualname, method, **kwargs)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper
    return metawrapper
