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


def _is_enum(value):
    return isinstance(value, type) and issubclass(value, Enum)


def _to_swagger_type(type_hint):
    if type_hint in FLASK_TO_SWAGGER:
        return FLASK_TO_SWAGGER[type_hint]
    if _is_enum(type_hint):
        if len({type(e.value) for e in type_hint}) == 1:
            return FLASK_TO_SWAGGER[type(list(type_hint)[0].value)]
        return
    try:
        return type_hint.__name__
    except AttributeError:
        return str(type_hint).lower()


def process_prototype(prefix, func):
    fas = inspect.getfullargspec(func)
    type_hints = get_type_hints(func)
    qualname = func.__qualname__
    if '.' in func.__qualname__:
        qualname = func.__qualname__.split('.')[-1]
    specs = {'description': func.__doc__ or qualname,
             'operationId': qualname,
             'tags': prefix.split('.'), 'parameters': []}
    default_offset = len(fas.args) - len(fas.defaults or [])
    for param_name in set(fas.args).union(type_hints):
        if param_name == 'return':
            continue
        parameter = {'name': param_name}
        if param_name in type_hints:
            parameter['type'] = _to_swagger_type(type_hints[param_name])
            if _is_enum(type_hints[param_name]):
                parameter['enum'] = [th.value
                                     for th in type_hints[param_name]]
        specs['parameters'].append(parameter)
        if not fas.defaults:
            parameter["required"] = True
            continue
        fas_index = fas.args.index(param_name)
        if fas_index != -1 and fas_index >= default_offset:
            default = fas.defaults[fas_index - default_offset]
            parameter["required"] = False
            if isinstance(default, Enum):
                parameter["default"] = default.value
            else:
                parameter["default"] = default
            if "type" not in parameter \
                    and type(parameter["default"]) in FLASK_TO_SWAGGER:
                parameter["type"] = FLASK_TO_SWAGGER[
                    type(parameter["default"])]
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
