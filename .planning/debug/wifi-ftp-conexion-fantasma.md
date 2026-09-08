---
status: investigating
slug: wifi-ftp-conexion-fantasma
goal: find_and_fix
active: true
created: 2026-09-07
updated: 2026-09-07
trigger: >-
  Feedback del usuario tras el quick 260907-p7b:
  1. Ni el Wifi ni el FTP siguen funcionando, siguen teniendo el mismo
  comportamiento de conexión. En versiones anteriores funcionaba pero ya dejó de
  hacerlo en un punto concreto. El feature de Wifi está basado en Pairdrop; el
  FTP lo inventó el desarrollo.
  2. Se ha arreglado el crash de detectar, pero se sospecha que vuelve a crashear
  cuando cierras la ventana y la vuelves a abrir, porque esos dispositivos no se
  guardan.
  3. Al añadir un dispositivo a través de "examinar", el dispositivo primero se
  añade correctamente, pero se añade como "desconectado". Luego al abrir la
  ventana de añadir origen, aparece un dispositivo MTP fantasma referenciando F
  que marca desconectado.
  4. No se crean sesiones al hacer click en +.
---

# Debug Session: wifi-ftp-conexion-fantasma

## Symptoms (respuestas precisadas por el usuario)

- **1a — WiFi (PairDrop):** el QR muestra una IP inalcanzable para el móvil
  (`err_address_unreachable`). Si el usuario accede al enlace desde el NAVEGADOR
  DEL PROPIO PC, la interfaz carga correctamente (el servidor está vivo y el
  bind funciona localmente). Fallo = la IP/host que se imprime en el QR no es
  alcanzable desde el teléfono.
- **1b — FTP:** no conecta al móvil (timeout/refused). Servidor FTP corre en el
  teléfono; el PC es cliente. Sospecha: IP del perfil/subred equivocada o
  escaneo sin resultados.
- **1c — Timeline:** el usuario cree que es problema de su máquina de testing;
  no puede precisar el commit exacto en que dejó de funcionar. Curiosidad: la
  interfaz WEB del WiFi sí es visible localmente (localhost), solo falla el
  acceso desde el móvil.
- **2 — Crash «Detectar»:** con el fix de ayer (84b0ebc) el crash al pulsar
  Detectar desapareció, pero se sospecha un nuevo crash al CERRAR la ventana de
  Añadir origen y VOLVERLA a ABRIR, porque "esos dispositivos no se guardan".
  Reproducción pendiente de confirmar (sospecha, no verificado).
- **3 — Añadir vía «examinar»:** el dispositivo/carpeta se añade correctamente
  pero queda marcado como «desconectado». Al reabrir la ventana de Añadir
  origen aparece además un dispositivo MTP fantasma «referenciando F» marcado
  desconectado.
- **4 — Sesiones «+»:** en el Panel Sesiones (combo + botón +), pulsar «+» NO
  crea/guarda la sesión.

## Contexto de sesiones de debug previas (antes de empezar)

- `.planning/debug/session-origen-dispositivo-mtp-fantasma.md` → RESOLVED.
  Root cause: `WpdBackend.list_devices()` enumeraba almacenamiento masivo USB
  (ids `usbstor`) como MTP fantasma además de unidades USB; se filtró `usbstor`
  en `list_devices` y se añadió `_repair_folder_device_id`. Afectaba a E:/F:.
- `.planning/debug/origenes-usb-e-f-fantasma.md` → IN_PROGRESS pero con notas de
  cierre en el archivo: root cause usb no-removibles E:/F: colando por
  `GetDriveTypeW()==2`; hardening aplicado y COMMITEADO (e71b6e9):
  `is_removable_drive()` exige `FILE_REMOVABLE_MEDIA` (kernel32.GetVolumeInformationW,
  utils.py:152) y `_refresh_physical_section` recuperó el escaneo USB sin gate
  `_explicit_mtp`. Estado del archivo: aún `active: true`; actualizar/cerrar si
  aplica.
- Previo fix p7b T5: `delete_known_devices_by_type("folder")` purga carpetas del
  registro known_devices.

## Evidence inicial para el debugger

- `app/ui/mixins/sources_mixin.py:548`:
  `mtp.WpdBackend().list_devices()` se llama en CADA `_pick_source_entry` en el
  hilo main UI — pista para issue 2 (crash al reabrir) y issue 3 (device MTP
  fantasma puede venir de known_devices o de list_devices no filtrado en la
  máquina de testing).
- `app/core/ftp.py`: `local_ip()` reescrito en p7b (10fc7e3:
  `_default_route_ip()` → `local_ips()[0]`) — investigar por qué sigue
  imprimiéndose una IP inalcanzable para el móvil pese a que el server local
  funciona (bounds vs host anunciado; posible NIC virtual/VPN primero, o
  `local_ip()` devuelve None → fallback 127.0.0.1).
- `app/core/shoot_inbox.py`: `base_url()`/`_serve_page` — cómo se construye la
  URL del QR (host impreso). Verificar cacheado del host en el sender config /
  alias sanitizado.
- QSS/Panel WiFi: QR generado por wifi_panel (`app/ui/wifi_panel.py`, qrcode).
- Sesiones «+»: revisar `sessions_mixin._add_manual_session` (line 287) y cómo
  el panel Sesiones conecta el botón +; verificar que `_refresh_sessions_combo`
  / inserción en DB de verdad persiste. Issue introducido quizá en el refactor
  i6a (260906) o en p7b (T5 tocó db.delete_known_devices_by_type; T4 tocó
  _pick_source_entry).
- Issue 3 «añadido como desconectado»: revisar lo que se añade al devolver
  `dialog.result_sources()` en `_pick_source_entry` → `_add_source_entry`
  (sources_mixin:474) y cómo se determina `connected` para `source_list`;
  comparar la fila de carpeta/encontrar con el source en sessions/known_devices.

## Evidence

- timestamp: 2026-09-07 (sesión-manager, arranque)
  - Issue 4 CONFIRMADO (definitivo): `app/ui/mixins/sessions_mixin.py:4` importa SOLO
    `QSettings` de `PySide6.QtCore`, pero `_add_manual_session` (línea 300) llama
    `QDate.currentDate()`. Verificado con AST: `QDate imported? False`. Al pulsar «+»
    e introducir nombre → `NameError: name 'QDate' is not defined` dentro del slot →
    la sesión nunca se crea y no hay feedback. Regresión del refactor i6a (260906)
    que extrajo SessionsMixin de MainWindow (main_window.py:399 conecta
    `btn_new_session.clicked` → `_add_manual_session`; no hay shadowing).
  - Issue 3 CONFIRMADO (cadena completa):
    - `devices_mixin.py:160-161` `_assign_folder_source` usa `is_removable_drive(path)`
      CRUDO (GetDriveTypeW==2) SIN el filtro `_is_false_positive_drive` que sí aplica
      `_windows_mounted_drives` (utils.py:65). Una unidad falsa positiva (E:/F: disco
      de sistema que reporta type 2) añadida por «Examinar» recibe
      `device_id = "usb:F:\"` en la sesión.
    - Columna Estado del origen: `_build_status_label` (sources_mixin.py:122-143) lee
      `self._connectivity`, que solo se alimenta con ids PnP MTP + `ftp:` desde el poll
      (main_window.py:721-726). `usb:*` nunca está → la fila se muestra SIEMPRE
      «Desconectado».
    - Al reabrir Añadir origen, `_disconnected_devices()` (devices_mixin.py:77-82)
      incluye device_ids `usb:F:\` de sesiones; el diálogo los renderiza como
      `kind="device"` con etiqueta «[MTP]» (add_source_dialog.py:236-243) → «MTP
      fantasma referenciando F marcado desconectado».
  - Issue 1a CONFIRMADO (mecanismo): `base_url()` (shoot_inbox.py:539-541) y
    `_serve_page` (línea 352) anuncian `local_ip()` (ftp.py:126-133) =
    `_default_route_ip() or local_ips()[0]`. `local_ips()` (ftp.py:105-123) =
    `getaddrinfo(gethostname())` ∪ ruta por defecto — incluye IPs de adaptadores
    virtuales (VMware/Hyper-V/WSL/VPN/TAP) y ordena lexicográficamente; sin ruta por
    defecto (OSError) cae al primer IP local alfabético → IP de adaptador virtual →
    móvil `err_address_unreachable`. El navegador del PC carga la URL porque la IP es
    local al PC (consistente con el síntoma). El server escucha en 0.0.0.0; solo el
    host ANUNCIADO falla.
  - Issue 1b CONFIRMADO (mismo root que 1a): `scan_network_ftp` →
    `local_subnet_ips()` (ftp.py:136-144) deriva subredes de `local_ips()` → si las
    IPs son de adaptador virtual, el escaneo cubre la subred EQUIVOCADA → el servidor
    FTP del móvil nunca aparece (timeout/refused). El fix p7b (10fc7e3) redujo el
    fallback a loopback pero no excluyó adaptadores virtuales.
  - Issue 2 SOSPECHA (no verificado): `_pick_source_entry` (sources_mixin.py:548)
    llama `WpdBackend().list_devices()` en el hilo UI en CADA apertura +
    `_disconnected_devices()` (devices_mixin.py:72) hace otra + el auto-sync poll
    (main_window.py:711-713, cada 5 s) hace una tercera en hilo de fondo. Churn
    CoInitialize/CoUninitialize + reset del manager en el hilo UI alrededor del
    diálogo nativo (QFileDialog «Examinar…» también usa COM) → riesgo de apartamento
    desbalanceado → crash plausible al cerrar/reabrir. Fix 84b0ebc cubrió el reuse
    de managers de apartamentos cerrados, no este churn.

## Current Focus

- hypothesis: 4 issues con raíces confirmadas (issues 1, 3, 4) + 1 sospecha (issue 2)
- test: N/A
- expecting: Decisión del usuario: aplicar fixes ahora vs planificar
- next_action: presentar checkpoint de root causes y opciones de fix al usuario