import argparse
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class SpaRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format, *args):
        return

    def do_GET(self):
        request_path = self.path.split('?', 1)[0].split('#', 1)[0]
        relative_path = request_path.lstrip('/')
        candidate = Path(self.directory, relative_path)
        if request_path in ('', '/'):
            self.path = '/index.html'
        elif candidate.is_dir() and Path(candidate, 'index.html').exists():
            self.path = f'/{relative_path.rstrip("/")}/index.html'
        elif not candidate.exists() or candidate.is_dir():
            if '.' not in Path(relative_path).name:
                self.path = '/index.html'
        return super().do_GET()

    def end_headers(self):
        if self.path.endswith('.js'):
            self.send_header('Content-Type', mimetypes.guess_type('app.js')[0] or 'application/javascript')
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description='Serve the CRA production build with SPA fallback.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=3000)
    parser.add_argument('--dir', default='build')
    args = parser.parse_args()

    build_dir = Path(args.dir).resolve()
    if not build_dir.exists():
        raise SystemExit(f'Build directory not found: {build_dir}')

    handler = lambda *handler_args, **handler_kwargs: SpaRequestHandler(
        *handler_args,
        directory=str(build_dir),
        **handler_kwargs,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
