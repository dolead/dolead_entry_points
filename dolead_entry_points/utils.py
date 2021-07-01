def to_http_path(name):
    name = ("/%s" % name).replace('.', '/').replace(' ', '-').replace('_', '-')
    name = name.rstrip('/')
    if not name.startswith('/'):
        return f"/{name}"
    return name


class DefaultCodeExecContext:

    def __init__(self, request):
        self.request = request

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass
