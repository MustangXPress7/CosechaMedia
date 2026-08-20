"""Recepción de clips por WiFi mediante un servidor HTTP embebido.

El móvil (Android o iOS) abre una URL/código QR en su navegador, sin instalar
nada, y sube los archivos. Cada envío cae en la caché local del remitente
(``data/inbox/<remitente>``), que se registra como un origen de ingesta normal
(una sesión por remitente, ``device_id = "wifi:pairdrop"``). El Ingestor se
encarga después de volcar los archivos al proyecto con copia verificada.

Cada persona tiene un remitente (tabla ``inbox_senders``) con su propio token;
el QR de cada remitente lleva ``?src=<nombre>&token=<token>`` para atribuir el
origen de cada archivo. Los envíos se escriben a un archivo ``.part`` y se
renombran al terminar para no ingerir archivos a medio bajar.

El modo carpeta (``folder_mode``) hace que la página ofrezca elegir una carpeta
entera (webkitdirectory); por defecto solo se envían archivos sueltos.
"""

import html
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional
from urllib.parse import parse_qs, urlsplit

from app.core.db import db as _default_db
from app.core.ftp import local_ip

# CSS de la página web de subida (B-07): se elige en _serve_page según el tema
# de la aplicación (claro/oscuro). El navegador del móvil no sabe nada de Qt.
_PAGE_CSS = {
    "dark": """<style>
  body { font-family: system-ui, -apple-system, sans-serif; background: #111;
         color: #eee; margin: 0 auto; padding: 24px; max-width: 560px; }
  h1 { font-size: 20px; margin: 0 0 6px; }
  .alias { color: #7ee787; font-weight: 700; }
  .sub { font-size: 12px; color: #888; }
  .card { background: #1c1c1c; border: 1px solid #333; border-radius: 12px;
          padding: 16px; margin: 16px 0; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn { background: #2ea043; color: #fff; border: 0; border-radius: 8px;
         padding: 12px 18px; font-size: 15px; cursor: pointer; }
  .btn:disabled { opacity: .5; cursor: default; }
  .btn.ghost { background: transparent; border: 1px solid #444;
               color: #bbb; }
  progress { width: 100%; margin: 8px 0; }
  #files { list-style: none; padding: 0; font-size: 13px; margin: 8px 0 0; }
  #files li { margin: 4px 0; }
  #files li.pending { color: #d0d7de; }
  #files li.ok { color: #7ee787; }
  #files li.err { color: #f85149; }
  #status { font-size: 13px; color: #bbb; min-height: 18px; }
  #status.ok { color: #7ee787; }
  #status.err { color: #f85149; }
  .sub strong { color: #eee; }
</style>""",
    "light": """<style>
  body { font-family: system-ui, -apple-system, sans-serif; background: #ffffff;
         color: #1f2328; margin: 0 auto; padding: 24px; max-width: 560px; }
  h1 { font-size: 20px; margin: 0 0 6px; }
  .alias { color: #1a7f37; font-weight: 700; }
  .sub { font-size: 12px; color: #59636e; }
  .card { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 12px;
          padding: 16px; margin: 16px 0; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn { background: #1f883d; color: #fff; border: 0; border-radius: 8px;
         padding: 12px 18px; font-size: 15px; cursor: pointer; }
  .btn:disabled { opacity: .5; cursor: default; }
  .btn.ghost { background: transparent; border: 1px solid #d0d7de;
               color: #59636e; }
  progress { width: 100%; margin: 8px 0; }
  #files { list-style: none; padding: 0; font-size: 13px; margin: 8px 0 0; }
  #files li { margin: 4px 0; }
  #files li.pending { color: #57606a; }
  #files li.ok { color: #1a7f37; }
  #files li.err { color: #cf222e; }
  #status { font-size: 13px; color: #59636e; min-height: 18px; }
  #status.ok { color: #1a7f37; }
  #status.err { color: #cf222e; }
  .sub strong { color: #1f2328; }
</style>""",
}

_PAGE_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enviar a CosechaMedia</title>
{style}
</head>
<body>
<h1>Enviar a CosechaMedia</h1>
<p>Estás enviando desde: <span class="alias">{alias}</span></p>
<p class="sub">Destino: CosechaMedia en <strong>{host}</strong>. Este móvil y el
ordenador deben estar conectados a la misma red WiFi.</p>
<div class="card">
  <label for="pick">{pick_label}</label>
  <input id="pick" type="file" {pick_attr}>
  <div class="row">
    <button id="send" class="btn" disabled>Enviar</button>
    <button id="cancel" class="btn ghost" hidden>Cancelar</button>
  </div>
  <progress id="bar" value="0" max="100" hidden></progress>
  <p id="status"></p>
  <ul id="files"></ul>
</div>
<script>
  const q = new URLSearchParams(location.search);
  const src = q.get("src");
  const token = q.get("token");
  let pending = [];
  let sent = [];
  let lastFiles = [];
  let sending = false;
  let cancel = false;
  const input = document.getElementById("pick");
  const list = document.getElementById("files");
  const sendBtn = document.getElementById("send");
  const cancelBtn = document.getElementById("cancel");
  const bar = document.getElementById("bar");
  const statusEl = document.getElementById("status");

  input.addEventListener("change", function () {{
    lastFiles = Array.from(input.files);
    pending = lastFiles.slice();
    sent = [];
    cancel = false;
    input.value = "";
    update();
  }});

  function fmt(n) {{
    if (typeof n !== "number" || !isFinite(n)) return "";
    if (n >= 1024 * 1024 * 1024) return (n / 1024 / 1024 / 1024).toFixed(1) + " GB";
    if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB";
    if (n >= 1024) return (n / 1024).toFixed(1) + " KB";
    return n + " B";
  }}

  function renderList() {{
    list.innerHTML = "";
    pending.forEach(function (f, i) {{
      const li = document.createElement("li");
      li.className = "pending";
      li.textContent = (i + 1) + ". " + f.name + " (" + fmt(f.size) + ")";
      list.appendChild(li);
    }});
    sent.forEach(function (s) {{
      const li = document.createElement("li");
      li.className = s.ok ? "ok" : "err";
      let txt = (s.ok ? "✓ " : "✗ ") + (s.name || "") + " (" + fmt(s.size) + ")";
      if (s.error) txt = txt + " — " + s.error;
      li.textContent = txt;
      list.appendChild(li);
    }});
  }}

  function failedFiles() {{
    const out = [];
    sent.forEach(function (s) {{ if (!s.ok) out.push(s.file); }});
    return out;
  }}

  function update() {{
    renderList();
    bar.hidden = !sending;
    if (sending) {{
      sendBtn.disabled = true;
      sendBtn.textContent = "Enviando…";
      cancelBtn.hidden = false;
      statusEl.className = "";
    }} else {{
      cancelBtn.hidden = true;
      const fails = failedFiles();
      const attempted = sent.length;
      if (pending.length > 0) {{
        sendBtn.disabled = false;
        sendBtn.textContent = "Enviar";
      }} else if (attempted > 0) {{
        sendBtn.disabled = false;
        sendBtn.textContent = fails.length > 0
            ? "Reintentar (" + fails.length + ")"
            : "Volver a enviar";
        const ok = attempted - fails.length;
        statusEl.textContent = fails.length > 0
            ? "Listo: " + ok + "/" + attempted + " enviados. "
              + fails.length + " con error."
            : "Listo: " + attempted + "/" + attempted + " enviados.";
        statusEl.className = fails.length > 0 ? "err" : "ok";
      }} else {{
        sendBtn.disabled = true;
        sendBtn.textContent = "Enviar";
        statusEl.textContent = "";
        statusEl.className = "";
      }}
    }}
  }}

  function sendOne(file) {{
    return new Promise(function (resolve, reject) {{
      const xhr = new XMLHttpRequest();
      const url = "/upload?src=" + encodeURIComponent(src) +
                  "&token=" + encodeURIComponent(token) +
                  "&name=" + encodeURIComponent({fname_expr});
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

  async function run() {{
    sending = true;
    cancel = false;
    update();
    const total = pending.length;
    while (pending.length > 0 && !cancel) {{
      const file = pending[0];
      const idx = total - pending.length + 1;
      statusEl.className = "";
      statusEl.textContent = "Enviando " + idx + "/" + total + ": " + file.name;
      bar.value = 0;
      try {{
        await sendOne(file);
        sent.push({{file: file, ok: true, error: "",
                    name: file.name, size: file.size}});
      }} catch (e) {{
        sent.push({{file: file, ok: false, error: e.message,
                    name: file.name, size: file.size}});
      }}
      pending.shift();
      update();
    }}
    if (cancel) statusEl.textContent = "Envío cancelado.";
    sending = false;
    update();
  }}

  sendBtn.addEventListener("click", async function () {{
    if (sending) return;
    if (pending.length === 0) {{
      const fails = failedFiles();
      pending = fails.length > 0 ? fails : lastFiles.slice();
      sent = [];
      if (pending.length === 0) return;
    }}
    await run();
  }});

  cancelBtn.addEventListener("click", function () {{ cancel = true; }});
</script>
</body>
</html>
"""


def inbox_root(db=None) -> str:
    """Carpeta raíz del buzón (``data/inbox``), junto a la base de datos."""
    db = db or _default_db
    return os.path.join(os.path.dirname(db.db_path), "inbox")


def wifi_cache_dir(sender_name: str, db=None) -> str:
    """Carpeta de caché local de un remitente (``data/inbox/<alias>``).

    Se usa como ``source_path`` de la sesión/origen WiFi correspondiente, de
    modo que la ingesta posterior funciona igual que con una tarjeta SD.
    """
    return os.path.join(inbox_root(db), sanitize_alias(sender_name))


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

    def handle(self):
        """Atiende la petición sin propagar errores de conexión del cliente.

        Un navegador que cancela la subida o cierra la conexión a mitad de un
        request dispara ``ConnectionResetError``/``BrokenPipeError`` dentro de
        ``http.server``. Son inofensivos, pero sin este override se imprimen
        como tracebacks de "Exception occurred during processing of request".
        """
        try:
            super().handle()
        except (ConnectionError, socket.timeout, TimeoutError):
            pass

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
        folder_mode = bool(getattr(self.server.owner, "folder_mode", False))
        page_dark = bool(getattr(self.server.owner, "page_dark", True))
        style = _PAGE_CSS["dark" if page_dark else "light"]
        page = _PAGE_TEMPLATE.format(
            style=style,
            alias=alias,
            host=f"{(local_ip() or '127.0.0.1')}:{self.server.owner.port}",
            pick_label=("Selecciona la carpeta que quieres enviar"
                        if folder_mode else
                        "Selecciona los archivos que quieres enviar"),
            pick_attr=("multiple webkitdirectory" if folder_mode else "multiple"),
            fname_expr=("file.webkitRelativePath || file.name"
                        if folder_mode else "file.name"),
        )
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

        target_dir = wifi_cache_dir(src, self.server.db)
        os.makedirs(target_dir, exist_ok=True)
        final = _unique_path(os.path.join(target_dir, rel))
        part = final + ".part"
        received = 0
        try:
            os.makedirs(os.path.dirname(part), exist_ok=True)
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
                 host: str = "0.0.0.0", port: int = 0,
                 folder_mode: bool = False, page_dark: bool = True):
        self.root = root or inbox_root(db)
        self.db = db or _default_db
        self.on_file_received = on_file_received
        self.host = host
        self.port = port
        self.folder_mode = folder_mode
        # La página de subida se sirve en oscuro o claro según el tema de la app.
        self.page_dark = page_dark
        self._httpd = None
        self._thread = None

    def start(self):
        if self._httpd is not None:
            return
        os.makedirs(self.root, exist_ok=True)
        httpd = ThreadingHTTPServer((self.host, self.port), _UploadHandler)
        httpd.root = self.root
        httpd.db = self.db
        httpd.senders = lambda: self.db.list_inbox_senders()
        httpd.owner = self
        httpd.callback = self._dispatch_file_received
        self._httpd = httpd
        self.port = httpd.server_address[1]
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()

    def _dispatch_file_received(self, alias: str, path: str, size: int):
        """Reenvía cada archivo recibido al callback actual.

        Se lee ``self.on_file_received`` en el momento de la llamada (no al
        arrancar), de modo que la ventana principal puede registrarse después
        de ``start()`` y seguir recibiendo los envíos en vivo.
        """
        callback = self.on_file_received
        if callback is not None:
            callback(alias, path, size)

    def _find_sender(self, src: str):
        for s in self.server.senders():
            if sanitize_alias(s["name"]) == src:
                return s
        return None


    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        self._thread = None

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def base_dir(self) -> str:
        """Carpeta base de la caché de recepción WiFi (``data/inbox``)."""
        return self.root

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
