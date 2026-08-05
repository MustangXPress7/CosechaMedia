"""Recepción de clips por WiFi mediante un servidor HTTP embebido.

El móvil (Android o iOS) abre una URL/código QR en su navegador, sin instalar
nada, y sube los archivos a ``inbox/<persona>/<fecha>/``. No hace falta un
servidor FTP en el dispositivo: el servidor lo monta CosechaMedia.

Cada persona tiene un remitente (tabla ``inbox_senders``) con su propio token;
el QR de cada remitente lleva ``?src=<nombre>&token=<token>`` para atribuir el
origen de cada archivo. Los envíos se escriben a un archivo ``.part`` y se
renombran al terminar para no ingerir archivos a medio bajar.
"""

import html
import json
import os
import re
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional
from urllib.parse import parse_qs, urlsplit

from app.core.db import db as _default_db
from app.core.ftp import local_ip

_PAGE_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enviar a CosechaMedia</title>
<style>
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #111;
         color: #eee; margin: 0; padding: 24px; }}
  h1 {{ font-size: 20px; margin: 0 0 6px; }}
  .alias {{ color: #7ee787; font-weight: 700; }}
  .card {{ background: #1c1c1c; border: 1px solid #333; border-radius: 12px;
          padding: 16px; margin: 16px 0; }}
  .btn {{ background: #2ea043; color: #fff; border: 0; border-radius: 8px;
         padding: 12px 18px; font-size: 15px; }}
  .btn:disabled {{ opacity: .5; }}
  progress {{ width: 100%; margin: 8px 0; }}
  #files {{ list-style: none; padding: 0; font-size: 13px; }}
  #files li {{ margin: 4px 0; }}
  #status {{ font-size: 13px; color: #bbb; }}
</style>
</head>
<body>
<h1>Enviar a CosechaMedia</h1>
<p>Estás enviando a: <span class="alias">{alias}</span></p>
<div class="card">
  <label>Selecciona los archivos que quieres enviar</label>
  <input id="pick" type="file" multiple>
  <ul id="files"></ul>
  <button id="send" class="btn" disabled>Enviar</button>
  <progress id="bar" value="0" max="100" hidden></progress>
  <p id="status"></p>
</div>
<script>
  const q = new URLSearchParams(location.search);
  const src = q.get("src");
  const token = q.get("token");
  let queue = [];
  const input = document.getElementById("pick");
  const list = document.getElementById("files");
  const sendBtn = document.getElementById("send");
  const bar = document.getElementById("bar");
  const statusEl = document.getElementById("status");
  input.addEventListener("change", function () {{
    queue = Array.from(input.files);
    render();
  }});
  function fmt(n) {{
    if (n >= 1024 * 1024 * 1024) return (n / 1024 / 1024 / 1024).toFixed(1) + " GB";
    if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB";
    if (n >= 1024) return (n / 1024).toFixed(1) + " KB";
    return n + " B";
  }}
  function render() {{
    list.innerHTML = "";
    queue.forEach(function (f, i) {{
      const li = document.createElement("li");
      li.textContent = (i + 1) + ". " + f.name + " (" + fmt(f.size) + ")";
      list.appendChild(li);
    }});
    sendBtn.disabled = queue.length === 0;
  }}
  function sendOne(file) {{
    return new Promise(function (resolve, reject) {{
      const xhr = new XMLHttpRequest();
      const url = "/upload?src=" + encodeURIComponent(src) +
                  "&token=" + encodeURIComponent(token) +
                  "&name=" + encodeURIComponent(file.name);
      xhr.open("POST", url);
      xhr.responseType = "json";
      xhr.upload.onprogress = function (e) {{
        if (e.lengthComputable) bar.value = e.loaded / e.total * 100;
      }};
      xhr.onload = function () {{
        const r = xhr.response;
        if (xhr.status === 200 && r && r.ok) resolve(r);
        else reject(new Error((r && r.error) || "Error " + xhr.status));
      }};
      xhr.onerror = function () {{ reject(new Error("Error de red")); }};
      xhr.send(file);
    }});
  }}
  sendBtn.addEventListener("click", async function () {{
    sendBtn.disabled = true;
    bar.hidden = false;
    bar.value = 0;
    let ok = 0;
    for (let i = 0; i < queue.length; i++) {{
      statusEl.textContent = "Enviando " + (i + 1) + "/" + queue.length +
                             ": " + queue[i].name;
      try {{
        await sendOne(queue[i]);
        ok++;
      }} catch (e) {{
        statusEl.textContent = "Error en " + queue[i].name + ": " + e.message;
      }}
    }}
    statusEl.textContent = "Listo: " + ok + "/" + queue.length + " enviados.";
    sendBtn.disabled = false;
  }});
</script>
</body>
</html>
"""


def inbox_root(db=None) -> str:
    """Carpeta raíz del buzón (``data/inbox``), junto a la base de datos."""
    db = db or _default_db
    return os.path.join(os.path.dirname(db.db_path), "inbox")


def sanitize_alias(name: str) -> str:
    """Alias de remitente seguro para usar como nombre de carpeta."""
    if not name:
        return "desconocido"
    cleaned = re.sub(r"[^A-Za-z0-9 _\-áéíóúüñÁÉÍÓÚÜÑ]", "", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "desconocido"


def sanitize_relative_path(name: str) -> str:
    """Normaliza un nombre enviado (posiblemente con ruta) a un relativo seguro."""
    name = name.replace("\\", "/")
    parts = []
    for raw in name.split("/"):
        part = os.path.basename(raw)
        if part in ("", "."):
            continue
        if part == "..":
            continue
        parts.append(part)
    if not parts:
        return ""
    return "/".join(parts)


def _unique_path(dest: str) -> str:
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(dest)
    n = 1
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


class _UploadHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send_json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _serve_page(self):
        alias = html.escape(sanitize_alias(self._query().get("src", [""])[0]))
        page = _PAGE_TEMPLATE.format(alias=alias)
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _query(self):
        return parse_qs(urlsplit(self.path).query)

    def do_GET(self):
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path == "/":
            self._serve_page()
        elif path == "/health":
            self._send_json(200, {"ok": True})
        else:
            self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path != "/upload":
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        self._handle_upload()

    def _handle_upload(self):
        q = self._query()
        src = sanitize_alias(q.get("src", [""])[0])
        token = q.get("token", [""])[0]
        raw_name = q.get("name", [""])[0]
        sender = self._find_sender(src)
        if sender is None or sender["token"] != token:
            self._send_json(403, {"ok": False, "error": "no autorizado"})
            return
        rel = sanitize_relative_path(raw_name)
        if not rel:
            self._send_json(400, {"ok": False, "error": "nombre inválido"})
            return
        length = 0
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            self._send_json(400, {"ok": False, "error": "sin contenido"})
            return

        date_dir = datetime.now().strftime("%Y-%m-%d")
        target_dir = os.path.join(self.server.root, src, date_dir)
        os.makedirs(target_dir, exist_ok=True)
        final = _unique_path(os.path.join(target_dir, rel))
        part = final + ".part"
        received = 0
        try:
            with open(part, "wb") as f:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    remaining -= len(chunk)
            if received != length:
                try:
                    os.remove(part)
                except OSError:
                    pass
                self._send_json(400, {"ok": False, "error": "transferencia incompleta"})
                return
            os.replace(part, final)
        except OSError as e:
            try:
                os.remove(part)
            except OSError:
                pass
            self._send_json(500, {"ok": False, "error": str(e)})
            return
        if self.server.callback is not None:
            try:
                self.server.callback(src, final, received)
            except Exception:
                pass
        self._send_json(200, {"ok": True, "path": rel, "size": received})

    def _find_sender(self, src: str):
        for s in self.server.senders():
            if sanitize_alias(s["name"]) == src:
                return s
        return None


class ShootInboxServer:
    """Servidor HTTP de subida para el buzón WiFi.

    Corre en un hilo propio (daemon). ``on_file_received(alias, path, size)`` se
    invoca desde el hilo del servidor al completar cada archivo.
    """

    def __init__(self, root: Optional[str] = None, db=None,
                 on_file_received: Optional[Callable[[str, str, int], None]] = None,
                 host: str = "0.0.0.0", port: int = 0):
        self.root = root or inbox_root(db)
        self.db = db or _default_db
        self.on_file_received = on_file_received
        self.host = host
        self.port = port
        self._httpd = None
        self._thread = None

    def start(self):
        if self._httpd is not None:
            return
        os.makedirs(self.root, exist_ok=True)
        httpd = ThreadingHTTPServer((self.host, self.port), _UploadHandler)
        httpd.root = self.root
        httpd.senders = lambda: self.db.list_inbox_senders()
        httpd.callback = self.on_file_received
        self._httpd = httpd
        self.port = httpd.server_address[1]
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def base_url(self) -> str:
        ip = local_ip() or "127.0.0.1"
        return f"http://{ip}:{self.port}"

    def url_for_sender(self, name: str) -> str:
        sender = next(
            (s for s in self.db.list_inbox_senders() if s["name"] == name), None)
        if sender is None:
            return self.base_url()
        from urllib.parse import urlencode
        return self.base_url() + "/?" + urlencode(
            {"src": sanitize_alias(sender["name"]), "token": sender["token"]})
