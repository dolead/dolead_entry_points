import inspect
from enum import Enum
from functools import wraps
from typing import Dict, List, get_type_hints


FLASK_TO_SWAGGER = {
    int: "integer",
    str: "string",
    bool: "boolean",
    dict: "object",
    Dict: "object",
    float: "number",
    list: "array",
    List: "array",
    None: "null",
}


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


def process_prototype(prefix, func):
    fas = inspect.getfullargspec(func)
    type_hints = get_type_hints(func)
    specs = {'description': func.__doc__ or func.__qualname__,
             'tags': [prefix], 'parameters': []}
    default_offset = len(fas.args) - len(fas.defaults or [])
    for param_name in set(fas.args).union(type_hints):
        if param_name == 'return':
            continue
        parameter = {'name': param_name}
        if param_name in type_hints:
            parameter['type'] = _to_swagger_type(type_hints[param_name])
        specs['parameters'].append(parameter)
        if not fas.defaults:
            parameter["required"] = True
            continue
        fas_index = fas.args.index(param_name)
        if fas_index != -1 and fas_index > default_offset:
            default = fas.defaults[fas_index - default_offset]
            parameter["required"] = False
            parameter["default"] = default
        else:
            parameter["required"] = True
    if 'return' in type_hints:
        swagger_type = _to_swagger_type(type_hints['return'])
        specs['responses'] = {'200': {'schema': {'type': swagger_type}}}
    if inspect.ismethod(func):
        @wraps(func)
        def to_func(*args, **kwargs):
            return func(*args, **kwargs)
        return to_func, specs
    return func, specs
