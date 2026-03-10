from __future__ import annotations

import json
import os
import secrets
from datetime import datetime
from http import cookies
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")
PORT = int(os.getenv("PORT", "5000"))

SESSIONS: dict[str, str] = {}


def agentic_response(message: str) -> str:
    lowered = message.strip().lower()
    if not lowered:
        return "Please type a message so I can help."

    if "date" in lowered or "time" in lowered:
        return f"[tool:clock] The current server time is {datetime.now():%Y-%m-%d %H:%M:%S}."

    if lowered.startswith("calc "):
        expression = message[5:].strip()
        try:
            safe_expression = expression.replace("**", "")
            result = eval(safe_expression, {"__builtins__": {}}, {})
            return f"[tool:calculator] {expression} = {result}"
        except Exception:
            return "[tool:calculator] I couldn't evaluate that expression."

    if "help" in lowered:
        return "Try: `calc 21 * 2`, ask for `time`, or send any prompt."

    return "Basic agentic starter: tool routing is active; integrate your LLM here."


def render_template(name: str, **values: str) -> bytes:
    content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace(f"{{{{ {key} }}}}", str(value))
    return content.encode("utf-8")


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.redirect("/dashboard" if self.current_user() else "/login")
            return

        if path == "/login":
            self.send_html(render_template("login.html", error=""))
            return

        if path == "/dashboard":
            user = self.current_user()
            if not user:
                self.redirect("/login")
                return
            self.send_html(render_template("dashboard.html", user=user))
            return

        if path.startswith("/static/"):
            self.serve_static(path)
            return

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/login":
            length = int(self.headers.get("Content-Length", "0"))
            form_data = parse_qs(self.rfile.read(length).decode("utf-8"))
            username = form_data.get("username", [""])[0].strip()
            password = form_data.get("password", [""])[0].strip()
            if username == DEMO_USERNAME and password == DEMO_PASSWORD:
                session_id = secrets.token_hex(16)
                SESSIONS[session_id] = username
                self.send_response(302)
                self.send_header("Location", "/dashboard")
                self.send_header("Set-Cookie", f"session_id={session_id}; HttpOnly; Path=/")
                self.end_headers()
                return
            self.send_html(render_template("login.html", error="Invalid username or password"))
            return

        if path == "/logout":
            sid = self.session_id()
            if sid:
                SESSIONS.pop(sid, None)
            self.send_response(302)
            self.send_header("Location", "/login")
            self.send_header("Set-Cookie", "session_id=deleted; Path=/; Max-Age=0")
            self.end_headers()
            return

        if path == "/api/chat":
            if not self.current_user():
                self.send_json({"error": "unauthorized"}, code=401)
                return
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            reply = agentic_response(str(data.get("message", "")))
            self.send_json({"reply": reply})
            return

        self.send_error(404)

    def serve_static(self, path: str):
        rel = path.replace("/static/", "", 1)
        file_path = STATIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        content_type = "text/plain"
        if file_path.suffix == ".css":
            content_type = "text/css"
        elif file_path.suffix == ".js":
            content_type = "application/javascript"

        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, body: bytes, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, code: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location: str):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def session_id(self) -> str | None:
        raw_cookie = self.headers.get("Cookie", "")
        if not raw_cookie:
            return None
        jar = cookies.SimpleCookie(raw_cookie)
        return jar.get("session_id").value if jar.get("session_id") else None

    def current_user(self) -> str | None:
        sid = self.session_id()
        if not sid:
            return None
        return SESSIONS.get(sid)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), AppHandler)
    print(f"Server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
