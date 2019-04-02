from flask import jsonify

COMMON_HTTP_METHODS = {'get', 'delete', 'post', 'put', 'head'}

# this is for the main script to leave a reference to the app in
_DEFAULTS = {'flask_app': None,
             'flask_formatter': jsonify,
             'task_prefix': '',
             'celery_app': None,
             'celery_formatter': lambda x: x,
             }


def kwargs_or_defaults(key, kwargs):
    if key in kwargs:
        return kwargs[key]
    return _DEFAULTS[key]


def set_default_app(**kwargs):
    _DEFAULTS.update(kwargs)


def get_unique_name(*args, method='get', kwargs=None):
    assert not kwargs or 'route' not in kwargs, ('route is not supported when '
        'declarating endpoints anymore. Please do serv("path", "to", "resource'
        '", method="get")')
    assert all(isinstance(elem, str) for elem in args)
    if args[-1] in COMMON_HTTP_METHODS:
        method = args[-1]
        args = args[:-1]
    task_prefix = kwargs_or_defaults('task_prefix', kwargs or {})
    celery_name = '.'.join([task_prefix] + list(args) + [method])
    flask_path = '/'.join(list(args))
    return task_prefix, celery_name, flask_path, method
