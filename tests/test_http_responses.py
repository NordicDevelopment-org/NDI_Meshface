import io
import json

from meshdash.http_responses import write_html_response, write_json_response, write_text_response


class _FakeHandler:
    def __init__(self):
        self.wfile = io.BytesIO()
        self.status = None
        self.headers = []
        self.ended = False

    def send_response(self, status_code):
        self.status = status_code

    def send_header(self, key, value):
        self.headers.append((key, value))

    def end_headers(self):
        self.ended = True


def test_write_json_response_sets_headers_and_payload():
    handler = _FakeHandler()
    write_json_response(handler, status_code=200, payload_obj={"ok": True}, no_store=True)

    assert handler.status == 200
    assert ("Content-Type", "application/json; charset=utf-8") in handler.headers
    assert ("Cache-Control", "no-store") in handler.headers
    assert handler.ended is True
    assert json.loads(handler.wfile.getvalue().decode("utf-8")) == {"ok": True}


def test_write_html_response_sets_headers_and_payload():
    handler = _FakeHandler()
    write_html_response(handler, html_text="<html>ok</html>")

    assert handler.status == 200
    assert ("Content-Type", "text/html; charset=utf-8") in handler.headers
    assert handler.wfile.getvalue() == b"<html>ok</html>"


def test_write_text_response_sets_headers_and_payload():
    handler = _FakeHandler()
    write_text_response(handler, status_code=404, text="Not Found")

    assert handler.status == 404
    assert ("Content-Type", "text/plain; charset=utf-8") in handler.headers
    assert handler.wfile.getvalue() == b"Not Found"
