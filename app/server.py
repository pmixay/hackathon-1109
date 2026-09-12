"""Локальный сервер интерфейса: статика + JSON API. Только стандартная библиотека.

    python app/server.py            # http://127.0.0.1:8765
    python app/server.py --port 8000

API
    GET  /api/dashboard?selected=<id>   пересобрать dashboard.json для выбранной комбинации
         &gates=filter|off              проверки команды (S2) как фильтр ранжирования / только диагностика (по умолчанию — как в config/weights.json)
    POST /api/export                    записать results/ движком kosmo для выбранной комбинации ({"selected": id})
    GET  /api/data                      активный набор данных (файлы, хэши, версия)
    POST /api/data                      {"files": {"lots.csv": "...", ...}, "apply": true} — проверить, сохранить, применить
    POST /api/data/reset                вернуть файлы организаторов
Ошибки API всегда отдаются JSON: 400 — неверный запрос (ValueError), 404 — нет такого пути, 500 — остальное.
Без сервера интерфейс тоже работает: `python app/build.py` и любой статический
хостинг папки app/static (например, `python -m http.server -d app/static`).
"""
from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import ingest, payload  # noqa: E402

APP = Path(__file__).resolve().parent
STATIC = APP / "static"
RESULTS = APP.parent / "results"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        """JSON-тело POST; не объект или не JSON → ValueError → 400."""
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")  # JSONDecodeError — подкласс ValueError
        if not isinstance(body, dict):
            raise ValueError("тело запроса должно быть JSON-объектом")
        return body

    def _api(self, fn, url):
        # Ошибки API всегда отдаём JSON: иначе соединение рвётся без ответа, и интерфейс молча уходит в статический режим.
        try:
            return fn(url)
        except ValueError as e:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        except Exception as e:  # noqa: BLE001 — сообщить клиенту, а не уронить поток сервера
            return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"{type(e).__name__}: {e}"})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            return self._api(self._get_api, url)
        if url.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def _get_api(self, url):
        if url.path == "/api/dashboard":
            query = parse_qs(url.query)
            selected = query.get("selected", [None])[0]
            gates = {"filter": True, "off": False}.get(query.get("gates", [""])[0])
            return self._json(HTTPStatus.OK, payload.build_dashboard(selected, gates_filter=gates))
        if url.path == "/api/data":
            return self._json(HTTPStatus.OK, ingest.describe())
        return self._json(HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})

    def do_POST(self):
        return self._api(self._post_api, urlparse(self.path))

    def _post_api(self, url):
        if url.path == "/api/export":
            dash = payload.build_dashboard(self._body().get("selected"))
            written = sorted(Path(p).relative_to(RESULTS.parent).as_posix() for p in payload.export_results(dash, RESULTS).values())
            return self._json(HTTPStatus.OK, {"written": written, "dir": written[0].rsplit("/", 1)[0], "selected": dash["selected"]})
        if url.path == "/api/data":
            body = self._body()
            files = {k: v for k, v in (body.get("files") or {}).items() if k in ingest.FILES and isinstance(v, str)}
            if not files:
                return self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "нет файлов", "report": {}})
            report = ingest.validate(files)
            if not all(r["ok"] for r in report.values()):
                return self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"ok": False, "error": "набор не прошёл проверку", "report": report})
            root = ingest.store(files)
            applied = False
            if body.get("apply", True):
                ingest.apply_dataset(root)
                payload.reset_cache()
                try:
                    payload.build_dashboard()
                except Exception as e:  # набор структурно верен, но расчёт на нём не сходится
                    ingest.reset(); payload.reset_cache()
                    return self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"ok": False, "error": f"расчёт на новом наборе не удался: {e}", "report": report, "stored": str(root)})
                applied = True
            return self._json(HTTPStatus.OK, {"ok": True, "report": report, "stored": str(root), "applied": applied, "dataset": ingest.describe()})
        if url.path == "/api/data/reset":
            ingest.reset(); payload.reset_cache()
            return self._json(HTTPStatus.OK, {"ok": True, "dataset": ingest.describe()})
        return self._json(HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})

    def log_message(self, fmt, *args):  # тише
        if "/api/" in str(args[0] if args else ""):
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    payload.build_dashboard()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Космо-портфель: http://{args.host}:{args.port}  (Ctrl+C — стоп)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
