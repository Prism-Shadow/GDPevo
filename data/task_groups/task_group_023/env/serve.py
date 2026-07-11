#!/usr/bin/env python3
"""Serve the static public health portal from env/web."""

from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import sys
from pathlib import Path

from judge_api import judge_answer_request


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"


class StaticOnlyHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path.split("?", 1)[0].rstrip("/") != "/api/judge":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        status, payload = judge_answer_request(self.rfile.read(length))
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def copyfile(self, source, outputfile) -> None:  # type: ignore[no-untyped-def]
        try:
            shutil.copyfileobj(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"{self.client_address[0]} - - [{self.log_date_time_string()}] {fmt % args}\n")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = os.environ.get("TASK_ENV_HOST", "0.0.0.0")
    if not WEB.exists():
        raise SystemExit(f"Missing static web directory: {WEB}")
    handler = functools.partial(StaticOnlyHandler, directory=str(WEB))
    server = http.server.ThreadingHTTPServer((host, port), handler)
    print(f"Serving Public Health Evidence Portal at http://{host}:{port}/index.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.", flush=True)


if __name__ == "__main__":
    main()
