import argparse
import json
import os
import os.path
from collections import defaultdict
from copy import deepcopy

import requests


def parse_args():
    parser = argparse.ArgumentParser('DoleadEntryPoint - Client generator')
    parser.add_argument('swagger')
    parser.add_argument('dst', default='.')
    return parser.parse_args()


def retrieve_swagger(swag):
    if swag.startswith('http'):
        print('assuming web swagger, retrieving it...', flush=True, end='')
        result = requests.get(swag).json()
        print('fetched !')
    else:
        print('assuming local file, opening it...', flush=True, end='')
        with open(os.path.expanduser(swag), 'r') as fd:
            result = json.load(fd)
        print('read !')
    return result


template_head = """from dolead_entry_points.client import (load_response,
                                        DoleadEntryPointClient)


class %(client_name)sClient(DoleadEntryPointClient):
"""

template_method = """
    @load_response
    def %(method_name)s(self%(space)s%(arguments)s):
        return self.call('%(path)s', '%(method_type)s'%(space)s%(arguments_proxied)s)
"""


def create_dirs(filename):
    dirname = os.path.dirname(filename)
    if not filename or not dirname or filename == dirname:
        return
    if os.path.exists(dirname):
        return
    create_dirs(os.path.dirname(dirname))
    os.mkdir(dirname)
    with open(os.path.join(dirname, '__init__.py'), 'w') as fd:
        fd.write('')


def main():
    args = parse_args()

    tags = defaultdict(list)
    for path, methods in retrieve_swagger(args.swagger)['paths'].items():
        for method, details in methods.items():
            if method not in {'get', 'delete', 'post', 'put'}:
                continue
            details = deepcopy(details)
            details['method'] = method
            details['path'] = path
            tags[tuple(details['tags'])].append(details)

    for tag in tags:
        filename = os.path.join(os.path.expanduser(args.dst),
                                f"{'/'.join(tag)}.py")
        create_dirs(filename)
        with open(filename, 'w') as fd:

            def iter_on_tag(tag_):
                for t in tag_:
                    yield from t.split('_')

            client_name = ''.join(map(str.capitalize, iter_on_tag(tag)))
            fd.write(template_head % ({'client_name': client_name}))
            for detail in tags[tag]:
                template_vars = {
                    'method_name': detail['operationId'],
                    'path': detail['path'],
                    'method_type': detail['method'],
                    'arguments': [],
                    'arguments_proxied': []}
                for param in sorted(detail.get('parameters') or (),
                                    key=lambda p: not p.get('required')):
                    if param.get('required'):
                        argument = f"{param['name']}"
                    elif param.get('type') == 'string':
                        argument = f"{param['name']}={param['default']!r}"
                    else:
                        argument = f"{param['name']}={param['default']}"
                    template_vars['arguments'].append(argument)
                    template_vars['arguments_proxied'].append(
                        f"{param['name']}={param['name']}")
                for key in 'arguments', 'arguments_proxied':
                    template_vars[key] = ', '.join(template_vars[key])
                template_vars['space'] = ', ' if template_vars['arguments'] else ''
                fd.write(template_method % template_vars)
