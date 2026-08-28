# Research Questions

Preguntas abiertas que necesitan investigación más profunda. Añadir entradas con fecha y contexto.

---

## 2026-08-22 — Estado de SHA-256 en la spec ASC MHL

**Pregunta:** ¿La especificación ASC MHL contempla `sha256` como hashFormat (aunque la implementación de referencia v1.2 no lo soporte)? ¿Existe intención upstream (`ascmitc/mhl`) de añadirlo?

**Contexto:** Durante el diseño de la fase XXH64+ASC MHL se verificó que el paquete oficial implementa `md5, sha1, xxh32, xxh64, xxh3, xxh128, c4` pero no SHA-256. El nivel "Máxima" de CosechaMedia usa sidecars `.sha256` propios fuera del estándar como workaround. La respuesta determina si ese workaround es temporal (contribución upstream viable, ver seed) o permanente.

**Impacto si la respuesta es favorable:** manifiestos de archivado 100% estándar, se eliminan los sidecars paralelos.

---

## 2026-08-29 — Viabilidad de las 3 features exploradas (reordenar, notificadores, WiFi SSID)

Origen: sesión `/gsd-explore` (`.planning/notes/exploracion-reordenar-notificaciones-wifi-ssid.md`, REQ-06/07/08 en `.planning/REQUIREMENTS.md`).

### RQ-2 — Cámaras reales de los operadores con FTP-over-WiFi

**Pregunta:** ¿Qué modelos de cámara usan realmente los operadores del proyecto y cuáles de ellos soportan FTP-over-WiFi servible (Canon R5/R6, Sony α7 III/α1/α9 III/FX3, Fuji GFX100 II, Nikon D780/D6)? ¿Alguno usa tarjetas WiFi (Eye-Fi/ProGrade)?

**Contexto:** La investigación confirmó FTP directo sin app del fabricante como estándar en esos modelos, pero el alcance de REQ-08 debe delimitarse por hardware real.

**Impacto si la respuesta es favorable:** alcance realista de REQ-08 y elección de backlog de cámaras para el spike.

### RQ-3 — Servidor FTP embebido para la app

**Pregunta:** ¿`pyftpdlib` (o alternativa) es robusto y seguro como servidor FTP embebido en una app PySide6 multiplataforma? ¿Soporta escritura atómica/`.part`, FTPS, credenciales por dispositivo y correr en un hilo/QThread sin romper el hilo de UI?

**Contexto:** De la investigación: las cámaras suben por FTP/SFTP/FTPS (no HTTP); la app hoy solo tiene cliente FTP (`ftp.py`). REQ-08 necesita el lado servidor. `pyftpdlib` es candidato conocido pero NO verificado en la pasada de investigación.

**Impacto si la respuesta es favorable:** desbloquea el spike/hito de REQ-08; si no, evaluación de FTPS/SFTP propio o reencuadre del alcance.

### RQ-4 — Almacenaje seguro de credenciales (notificaciones y WiFi)

**Pregunta:** ¿Cómo se almacenan de forma segura en los 3 SO las credenciales de notificadores (SMTP, token Telegram) y de red (SSID/contraseña) sin un keyring adicional? ¿Patrón Windows Credential Manager (win32crypt/DPAPI), macOS Keychain (`security`), Linux `secret-tool`/libsecret o SQLite cifrada con clave derivada?

**Contexto:** Hoy la DB guarda FTP passwords y tokens inbox en plaintext (CONCERNS.md). Las credenciales WiFi persisten del lado SO de forma distinta por plataforma (perfil cifrado Win, keychain macOS, `/etc/NetworkManager` plaintext 0600 root-only), lo que exige aviso al usuario y mínimo almacenaje.

**Impacto si la respuesta es favorable:** diseño de almacenaje para REQ-07 y REQ-08 alineado con el patrón cross-platform sin romper compatibilidad.
