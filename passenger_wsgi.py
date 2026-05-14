import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

errors = []


def error_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    error_html = "<br>".join(str(e).replace("<", "&lt;") for e in errors)
    body = f"""
    <html>
    <head><title>Debug - AutoContent Panel</title></head>
    <body style="background:#1a1a2e;color:#e94560;font-family:monospace;padding:30px;">
        <h1 style="color:#fff;">AutoContent Panel - Debug Mode</h1>
        <h2>Errors found:</h2>
        <pre style="color:#feca57;background:#16213e;padding:20px;border-radius:10px;white-space:pre-wrap;">{error_html}</pre>
        <h3 style="color:#fff;">Python Info:</h3>
        <pre style="color:#00d2d3;background:#16213e;padding:20px;border-radius:10px;">
Python: {sys.version}
Path: {os.path.dirname(os.path.abspath(__file__))}
CWD: {os.getcwd()}
sys.path: {chr(10).join(sys.path[:5])}
        </pre>
    </body>
    </html>
    """.encode('utf-8')
    return [body]


try:
    from a2wsgi import ASGIMiddleware
except ImportError as e:
    errors.append(f"a2wsgi import failed: {e}")
    try:
        import asyncio

        class SimpleASGItoWSGI:
            def __init__(self, asgi_app):
                self.asgi_app = asgi_app

            def __call__(self, environ, start_response):
                import io

                path = environ.get('PATH_INFO', '/')
                method = environ.get('REQUEST_METHOD', 'GET')
                query = environ.get('QUERY_STRING', '')
                content_length = int(environ.get('CONTENT_LENGTH', 0) or 0)
                body = environ['wsgi.input'].read(content_length) if content_length else b''

                headers_list = []
                for key, value in environ.items():
                    if key.startswith('HTTP_'):
                        header_name = key[5:].lower().replace('_', '-')
                        headers_list.append([header_name.encode(), value.encode()])

                if environ.get('CONTENT_TYPE'):
                    headers_list.append([b'content-type', environ['CONTENT_TYPE'].encode()])

                scope = {
                    'type': 'http',
                    'asgi': {'version': '3.0'},
                    'http_version': '1.1',
                    'method': method,
                    'path': path,
                    'query_string': query.encode(),
                    'headers': headers_list,
                    'server': (environ.get('SERVER_NAME', 'localhost'), int(environ.get('SERVER_PORT', 80))),
                }

                status_code = 200
                response_headers = []
                body_parts = []

                async def receive():
                    return {'type': 'http.request', 'body': body}

                async def send(message):
                    nonlocal status_code, response_headers
                    if message['type'] == 'http.response.start':
                        status_code = message['status']
                        response_headers = [
                            (h[0].decode() if isinstance(h[0], bytes) else h[0],
                             h[1].decode() if isinstance(h[1], bytes) else h[1])
                            for h in message.get('headers', [])
                        ]
                    elif message['type'] == 'http.response.body':
                        body_parts.append(message.get('body', b''))

                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(self.asgi_app(scope, receive, send))
                finally:
                    loop.close()

                status_str = f"{status_code} OK"
                start_response(status_str, response_headers)
                return body_parts

        ASGIMiddleware = SimpleASGItoWSGI
        errors.pop()
        errors.append("a2wsgi not available, using builtin ASGI-to-WSGI wrapper")
    except Exception as e2:
        errors.append(f"Fallback WSGI wrapper also failed: {e2}")

try:
    import asyncio as _asyncio
    from app.database import init_db as _init_db
    _loop = _asyncio.new_event_loop()
    _loop.run_until_complete(_init_db())
    _loop.close()
except Exception as e:
    errors.append(f"DB init failed: {e}")

try:
    from app.main import app as fastapi_app
    if 'ASGIMiddleware' in dir():
        application = ASGIMiddleware(fastapi_app)
    else:
        application = error_app
except Exception as e:
    errors.append(f"App import failed: {e}\n{traceback.format_exc()}")
    application = error_app

if errors and application != error_app:
    pass
elif errors:
    application = error_app
