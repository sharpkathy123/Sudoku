"""Shared helpers for the browser-driven regression tests in this directory.

These tests exercise things the in-page `?test` suite (see index.html)
can't: real rendered pixels, real offline network conditions, and
multi-step UI interaction sequences. Each test file is a standalone
script — run it directly with `python3 tests/test_whatever.py`.
"""
import contextlib
import functools
import http.server
import os
import socket
import threading

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def serve_repo():
    """Serve the repo root over plain HTTP on a free local port for the
    duration of the `with` block, and yield its base URL."""
    port = _free_port()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=REPO_ROOT)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def launch_browser(playwright):
    """Launch Chromium, using a pre-installed browser if one is present
    (as in Claude Code's sandboxed environments) and falling back to
    Playwright's normal browser resolution otherwise."""
    custom_path = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH", "/opt/pw-browsers/chromium")
    if os.path.exists(custom_path):
        return playwright.chromium.launch(executable_path=custom_path)
    return playwright.chromium.launch()
