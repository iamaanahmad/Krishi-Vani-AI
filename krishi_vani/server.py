from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import (
    InputError,
    SUPPORTED_AUDIO_TYPES,
    SUPPORTED_IMAGE_TYPES,
    build_pipeline,
    decode_upload,
    normalise_event_name,
)


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "app"
EVENTS: list[dict[str, object]] = []
EVENTS_LOCK = threading.Lock()


class AppHandler(BaseHTTPRequestHandler):
    server_version = "KrishiVani/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "mode": "offline-demo",
                    "llm": self.server.pipeline.generator.name,  # type: ignore[attr-defined]
                },
            )
            return
        if parsed.path == "/api/events":
            run = parse_qs(parsed.query).get("run", [""])[0]
            with EVENTS_LOCK:
                events = [event for event in EVENTS if not run or event.get("e2e_run") == run]
            self._json(HTTPStatus.OK, {"events": events})
            return
        if parsed.path == "/robots.txt":
            self._robots()
            return
        if parsed.path == "/sitemap.xml":
            self._sitemap()
            return
        if parsed.path == "/llms.txt":
            self._llms()
            return
        self._static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/triage":
            self._triage()
            return
        if self.path == "/api/events":
            self._event()
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} [{self.log_date_time_string()}] {format % args}")

    def _read_json(self) -> dict[str, object]:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise InputError("Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise InputError("Invalid Content-Length") from exc
        if length <= 0 or length > 18 * 1024 * 1024:
            raise InputError("Request body is empty or too large")
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as exc:
            raise InputError("Request body is not valid JSON") from exc
        if not isinstance(value, dict):
            raise InputError("Request body must be an object")
        return value

    def _triage(self) -> None:
        try:
            payload = self._read_json()
            audio = decode_upload(payload, "audio", SUPPORTED_AUDIO_TYPES)
            image = decode_upload(payload, "image", SUPPORTED_IMAGE_TYPES)
            result = self.server.pipeline.triage(audio, image)  # type: ignore[attr-defined]
            self._json(HTTPStatus.OK, result)
        except InputError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # keep the local demo useful while returning a safe error
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Triage failed safely", "detail": str(exc)})

    def _event(self) -> None:
        try:
            payload = self._read_json()
            name = normalise_event_name(str(payload.get("event", "")))
            event = {
                "event": name,
                "e2e_run": str(payload.get("e2e_run", ""))[:80],
                "is_e2e_test": bool(payload.get("is_e2e_test", False)),
                "status": str(payload.get("status", ""))[:40],
                "timestamp": time.time(),
            }
            with EVENTS_LOCK:
                EVENTS.append(event)
                del EVENTS[:-200]
            self._json(HTTPStatus.ACCEPTED, {"accepted": True})
        except InputError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _static(self, path: str) -> None:
        if path.startswith("/fixtures/"):
            base = ROOT / "fixtures"
            relative = path.removeprefix("/fixtures/")
        else:
            base = PUBLIC
            relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (base / relative).resolve()
        if base.resolve() not in target.parents or not target.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        content = target.read_bytes()
        if target == PUBLIC / "index.html":
            public_origin = self._public_origin()
            canonical_url = html.escape(f"{public_origin}/", quote=True)
            content = content.replace(b"__CANONICAL_URL__", canonical_url.encode("utf-8"))
            content = content.replace(
                b"__STRUCTURED_DATA__",
                self._structured_data(public_origin).encode("utf-8"),
            )
        mime_type, _ = mimetypes.guess_type(target.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def _public_origin(self) -> str:
        configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        if configured:
            parsed = urlparse(configured)
            if (
                parsed.scheme in {"http", "https"}
                and parsed.netloc
                and not parsed.path
                and not parsed.params
                and not parsed.query
                and not parsed.fragment
                and parsed.username is None
                and parsed.password is None
            ):
                return configured

        forwarded_proto = self.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip()
        scheme = forwarded_proto if forwarded_proto in {"http", "https"} else "http"
        forwarded_host = self.headers.get("X-Forwarded-Host", "").split(",", 1)[0].strip()
        host = forwarded_host or self.headers.get("Host", "127.0.0.1").strip()
        parsed = urlparse(f"{scheme}://{host}")
        if (
            parsed.netloc
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and parsed.path == ""
        ):
            return f"{scheme}://{parsed.netloc}"
        return "http://127.0.0.1"

    def _robots(self) -> None:
        content = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /api/\n"
            f"Sitemap: {self._public_origin()}/sitemap.xml\n"
        ).encode("utf-8")
        self._text(HTTPStatus.OK, "text/plain; charset=utf-8", content)

    def _sitemap(self) -> None:
        canonical_url = html.escape(f"{self._public_origin()}/")
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{canonical_url}</loc></url>\n"
            "</urlset>\n"
        ).encode("utf-8")
        self._text(HTTPStatus.OK, "application/xml; charset=utf-8", content)

    def _llms(self) -> None:
        content = (
            "# Krishi-Vani AI\n\n"
            "> Open-source, offline-capable challenge prototype for Odia rice triage "
            "using two labelled demo fixture pairs.\n\n"
            f"- Canonical demo: {self._public_origin()}/\n"
            "- Source code: https://github.com/iamaanahmad/Krishi-Vani-AI\n\n"
            "## Verified demo behavior\n\n"
            "- Recognizes only the two bundled labelled audio-and-leaf fixture pairs.\n"
            "- Returns one cited, non-chemical next step when curated evidence matches.\n"
            "- Stops and recommends KVK or agricultural extension review when evidence is weak.\n\n"
            "## Boundaries\n\n"
            "- Does not interpret arbitrary farmer recordings or photographs.\n"
            "- Does not provide a confirmed diagnosis or pesticide or fungicide instructions.\n"
            "- AIKosh, AI4Bharat/Bhashini, messaging, mandi, and subsidy integrations are not connected.\n"
        ).encode("utf-8")
        self._text(HTTPStatus.OK, "text/plain; charset=utf-8", content)

    @staticmethod
    def _structured_data(public_origin: str) -> str:
        canonical_url = f"{public_origin}/"
        repository_url = "https://github.com/iamaanahmad/Krishi-Vani-AI"
        data = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Organization",
                    "@id": f"{canonical_url}#organization",
                    "name": "Krishi-Vani AI project",
                    "alternateName": "Krishi-Vani AI",
                    "url": canonical_url,
                    "sameAs": [repository_url],
                    "description": "Open-source challenge prototype project for transparent Odia rice triage.",
                },
                {
                    "@type": "SoftwareApplication",
                    "@id": f"{canonical_url}#software",
                    "name": "Krishi-Vani AI",
                    "url": canonical_url,
                    "applicationCategory": "EducationalApplication",
                    "operatingSystem": "Python 3.11+ and a modern browser",
                    "inLanguage": ["or", "en"],
                    "description": (
                        "Open-source labelled-fixture demonstration of Odia rice triage "
                        "with cited guidance and safe escalation."
                    ),
                    "sameAs": [repository_url],
                    "license": "https://opensource.org/license/mit",
                    "isAccessibleForFree": True,
                    "author": {"@id": f"{canonical_url}#organization"},
                    "featureList": [
                        "Two bundled labelled audio-and-leaf fixture scenarios",
                        "Cited non-chemical next step when curated evidence matches",
                        "Confidence-aware KVK or agricultural extension escalation",
                    ],
                },
                {
                    "@type": "FAQPage",
                    "@id": f"{canonical_url}#faq",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": "Can it interpret farmer media?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": (
                                    "No. Farmer media is not interpreted yet; "
                                    "only two bundled fixtures are recognized."
                                ),
                            },
                        },
                        {
                            "@type": "Question",
                            "name": "Does it diagnose or prescribe chemicals?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": (
                                    "No. It returns one non-chemical step or stops "
                                    "for KVK/extension review."
                                ),
                            },
                        },
                    ],
                },
            ],
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

    def _text(self, status: HTTPStatus, content_type: str, content: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def _json(self, status: HTTPStatus, payload: object) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), AppHandler)
    server.pipeline = build_pipeline()  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Krishi-Vani AI local rice triage demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    args = parser.parse_args()
    server = make_server(args.host, args.port)
    print(f"Krishi-Vani AI ready at http://{args.host}:{args.port}")
    print(f"Generator: {server.pipeline.generator.name}")  # type: ignore[attr-defined]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
