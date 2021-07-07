from flask import jsonify


class DefaultCodeExecContext:

    def __init__(self, request):
        self.request = request

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


# this is for the main script to leave a reference to the app in
DEFAULTS = {'flask_app': None,
            'flask_formatter': jsonify,
            'flask_code_exec_ctx_cls': DefaultCodeExecContext,
            'task_prefix': 'dolead-entry-points',
            'celery_app': None,
            'celery_formatter': lambda x: x,
            'celery_code_exec_ctx_cls': DefaultCodeExecContext,
            'client_json_default': None}


def kwargs_or_defaults(key, kwargs):
    if key in kwargs:
        return kwargs[key]
    return DEFAULTS[key]


def gen_path(prefix, route='', **kwargs):
    "Generate a path (aimed at flask, path may not be unique"
    return ("%s.%s" % (prefix, route or '')).strip('.')


def gen_qn(*args, **kw):
    "Generate a qualname, should be unique"
    task_prefix = kwargs_or_defaults('task_prefix', kw)
    if len(set(['prefix', 'method']).intersection(kw)) == 2:
        return "%s.%s.%s" % (task_prefix, gen_path(**kw), kw['method'])
    return ".".join([task_prefix] + list(args))


def to_http_path(name):
    name = ("/%s" % name).replace('.', '/').replace(' ', '-').replace('_', '-')
    name = name.rstrip('/')
    if not name.startswith('/'):
        return f"/{name}"
    return name
