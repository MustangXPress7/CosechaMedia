---
title: Exploración — Reorganizar footage, notificadores, WiFi por SSID/contraseña
date: 2026-08-29
context: Sesión /gsd-explore iniciada con 3 features + revisión awesome-python. Definiciones acordadas con el operador y hallazgos de investigación con disposición (admit/refute/abstain).
---

# Exploración 2026-08-29: reordenar footage, notificaciones, WiFi por SSID

Tres features exploradas. Las definiciones acordadas alimentan REQ-06/07/08 en
`.planning/REQUIREMENTS.md`. La revisión de awesome-python queda como todo
`.planning/todos/pending/revisar-awesome-python.md`.

## 1. Reorganizar footage (REQ-06)

Problema real: los volcados **a mano fuera de la app** (estructura `DCIM/...`
o carpetas sueltas) quedan sin procesar en la maestra.

Decisiones acordadas:

- **Acción integrada de la app** (no runner de scripts externos): botón
  "Reorganizar footage..." con su diálogo.
- **Selector de carpeta** por el operador (dondequiera que viva el volcado);
  el reordenador solo toca esa carpeta (nada del árbol ya organizado).
- **Mover en sitio** (rename/move atómico, sin recopiar y sin MD5): se asume
  que el volcado a mano ya es la copia íntegra; no hay tarjeta contra la que
  verificar.
- Clasificación reutilizando `metadata_engine` (ffprobe) →
  `Footage/<Cámara>/<Fecha>`.
- No clasificables → `Footage/_SinClasificar/` + reporte de movimientos.
- Colisión de nombre en destino → pregunta por archivo con capa "aplicar a todas".
- Nada se borra jamás.

## 2. Notificadores inteligentes (REQ-07)

Destinatario: **el productor/cliente** (informe de estado externo, no
recordatorio personal). Tensión con la filosofía "sin nube" reconocida y
aceptada: es salida de red puntual y configurada, no almacenamiento en nube.

Decisiones acordadas:

- **Interfaz de notificadores** configurable por proyecto, con varios backends.
- Backends mínimo: **email SMTP** y **Telegram**. Bonus laterales: ntfy/Pushover.
- Disparo **por sesión al terminar** con su resumen (archivos, GB, cámaras,
  verificación MD5 ok/fallos, ruta destino). Los errores de ingesta también
  deben poder notificarse (pendiente de fijar por defecto).
- Credenciales guardadas sin exponer (revisar patrón actual de DB plaintext).

## 3. WiFi por SSID+contraseña para cámaras (REQ-08)

Topología acordada: **la app se une a una red existente** (SSID+contraseña
tecleados) y el servidor de recepción se ancla a esa interfaz. No hospeda su
propio AP.

**Implicación arquitectónica clave (investigación):** las cámaras NO suben a
un endpoint HTTP arbitrario — FTP/SFTP/FTPS es el protocolo universal de
servidor. ShootInbox (HTTP) sirve para móviles; para cámaras hace falta un
**servidor FTP embebido** nuevo (el `ftp.py` actual es cliente, tira de
servidores FTP del móvil). HTTP en cámaras solo aparece como pull/control
(Sony PTP/IP) o endpoint fijo (Frame.io C2C).

## Hallazgos de investigación (disposición, tier sonnet)

**Admitidos (con fuente):**

- Email: stdlib `smtplib` (`SMTP_SSL`, `starttls`, `login`, `send_message`,
  SMTPUTF8) — mantenido y sin dependencias, por encima de tercera parte [docs.python.org/3/library/smtplib.html].
- Telegram: `python-telegram-bot` v22.8 (2026-06), mantenimiento
  "Healthy", 29.3k ⭐, Python ≥3.10 [PyPI / docs.python-telegram-bot.org].
- awesome-python no tiene sección WiFi; lo más cercano son `asyncio`
  (stdlib), `websockets` y `scapy` [vinta/awesome-python].
- EXIF de foto: Pillow 12.3.0 `Image.getexif()` + `PIL.ExifTags.TAGS/
  GPSTAGS` para JPEG/TIFF; ffprobe cubre video [pillow.readthedocs.io].
- Unirse a red Windows: `netsh wlan add profile` (XML WPA2PSK) requiere
  elevación; `netsh wlan connect name=<profile>` sin elevación. Hack
  `netsh wlan hostednetwork` deprecado (Win10) y eliminado (Win11) [Microsoft Learn].
- macOS: `networksetup -setairportnetwork <if> <ssid> <pass>` canónico y
  requiere admin/root [man(8) networksetup].
- Linux: `nmcli device wifi connect <ssid> password <pw>` estándar con polkit;
  el usuario de escritorio normalmente conecta sin sudo [networkmanager.dev].
- Cámaras — FTP directo por WiFi sin app del fabricante es estándar en Canon
  EOS R5/R6 (FTP/FTPS/SFTP, WPS a AP existente), Sony α7 III/α1/α9 III/FX3
  (FTP Transfer Func), Fuji GFX100 II (sin accesorio) [manuales Canon/Sony/Fujifilm].
- Modo infraestructura (la cámara se une a un router/WLAN existente) estaría
  ampliamente soportado: Canon WPS, Nikon "station mode", Sony access point [manuales].
- Panasonic: pro/P2 camcorders (AJ-PX, VariCam) sí exponen servicio cliente
  FTP por WiFi; las Lumix consumer no (solo tether + Frame.io C2C a endpoint
  fijo) [manuales pro + guía Frame.io].

**Corregido (fuente primaria en contra de la creencia):**

- Nikon NO es "FTP solo por cable": D780 y D6 hacen FTP WiFi integrado
  (AP e infraestructura, FTP/SFTP/FTPS). D850, D750, D500 y D7200 no — requieren
  el transmisor WT-7 (Ethernet o WiFi) [Nikon Wireless Transmitter Utility + manual D780].

**Ledger unresolved (no se afirma como hecho):**

- `yagmail`: release PyPI 2026-05 pero último commit GitHub 2022 y Snyk
  "Inactive"; señales contradictorias — [conflicto fuente-vs-prior]. Se omite
  como recomendación; usar stdlib `smtplib`.
- Ninguna cámara soporta HTTP POST arbitrario: afirmación no verificable de
  forma directa (falta de soporte documentado en los 5 manuales revisados) —
  [abstain: no hay fuente primaria que documente el extremo opuesto]. Se usa
  FTP como supuesto de diseño para REQ-08.
- Credenciales WiFi persistidas por el SO: Windows perfil cifrado (machine
  key), macOS keychain (recuperable por `security`), Linux `/etc/NetworkManager/
  system-connections/` plaintext 0600 — superficie de fuga real a tratar en
  diseño (aviso al usuario + mínimo almacenaje).
- `pyftpdlib` como servidor FTP embebido: candidato conocido, NO verificado en
  esta pasada — pasa a RQ de viabilidad.

## Rutas

- REQ-06/07 → candidatas a fase v2 (no bloqueadas).
- REQ-08 → **depende de spike/viabilidad**: servidor FTP embebido + unirse a
  red por OS + cámaras reales del operador (ver research questions 2026-08-29).
- Review de awesome-python completa → todo `revisar-awesome-python.md`.