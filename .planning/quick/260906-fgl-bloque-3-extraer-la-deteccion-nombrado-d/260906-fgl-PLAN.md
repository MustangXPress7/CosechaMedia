---
phase: quick-260906-fgl
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/ui/mixins/camera_mixin.py          # NUEVO — 16 métodos de cámara/SD verbatim
  - app/ui/main_window.py                  # −16 métodos, composición (WifiMixin, CameraMixin), −get_mounted_drives
  - tests/test_main_window.py              # +camera_mixin_module.db en setUps/tearDowns que construyen MainWindow
  - tests/test_source_content.py           # ídem
  - tests/test_e2e.py                      # ídem
  - tests/test_wifi_source.py              # ídem (ya tiene wifi_mixin_module.db)
  - tests/test_session_content_modes.py    # ídem (solo el setUp con MainWindow)
autonomous: true
requirements: [QUICK-260906-fgl]
user_setup: []

estimate:
  tokens: 30000
  raw_tokens: 15000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Los 16 métodos de cámara/SD son invocables sobre una instancia de MainWindow tras la refactorización (composición por MRO): _on_camera_rename_needed, _post_ingest_rename_dialog, _prompt_rename_camera, _drive_label, _find_smallest_media, _set_camera_cell_text, _camera_for_path, _detect_camera_for_session, _prompt_nombre_dispositivo, _detect_camera_for_source, _persist_camera_mapping, _on_camera_cell_edited, _on_dialog_camera_name_changed, _detect_sd_card, _on_auto_detect_toggled, _auto_detect_removable_drives"
    - "MainWindow ya NO define los 16 métodos (resuelven por MRO desde CameraMixin)"
    - "Cero cambio de comportamiento: los cuerpos son VERBATIM salvo el hoisting de `import threading`/`import uuid` a nivel de módulo; un script de equivalencia contra `git show HEAD` lo verifica"
    - "La clase declara `class MainWindow(QMainWindow, WifiMixin, CameraMixin):` y CameraMixin NO define `__init__` ni `super().__init__()` (precedente WifiMixin)"
    - "`eventFilter` sigue existiendo una única vez en el MRO (solo el de main_window.py:2497; ninguno de los 16 métodos define eventFilter)"
    - "Los tests reasignan `camera_mixin_module.db = self.db` en paralelo a `mw.db = self.db` (namespace del singleton): la suite completa pasa con la única falla pre-existente order-dependent de test_mtp"
  artifacts:
    - "app/ui/mixins/camera_mixin.py existe con los 16 métodos y los imports de módulo: os, threading, uuid, QTimer/QDate/QSettings (QtCore), QInputDialog/QMessageBox (QtWidgets), db (app.core.db), sd_reader (app.core.sd_reader), metadata_engine (app.core.metadata_engine), get_mounted_drives (app.core.utils)"
    - "app/ui/main_window.py sin los 16 métodos, con import CameraMixin y sin get_mounted_drives en el import de app.core.utils (quedó huérfano)"
    - "Los 5 ficheros de test adaptados con el parche paralelo del singleton"
  key_links:
    - "Namespace del singleton: los métodos movidos resuelven `db` desde app.ui.mixins.camera_mixin — los tests que reasignan `mw.db = self.db` y construyen MainWindow DEBEN reasignar también `camera_mixin_module.db = self.db` (15 setUps en 5 ficheros)"
    - "Resolución cruzada por MRO: wifi_mixin.py:345 (`ing.camera_rename_needed.connect(self._on_camera_rename_needed)`) y las llamadas `self._drive_label`/`self._detect_camera_for_session`/`self._on_dialog_camera_name_changed` desde métodos NO movidos (líneas 2051, 2596-2597, 3390, 3426, 3569, 1349, 2066, 2568, 3204-3206, 3405, 3430, 3634, 4068, 705, 2988, 2992) siguen resolviendo por MRO — la composición debe añadir CameraMixin al MRO antes de QMainWindow"
    - "_drive_label es @staticmethod y se usa desde métodos NO movidos (_format_sources, sesiones, dispositivos): al moverlo a CameraMixin, `self._drive_label` resuelve por MRO sin cambios en los call sites"
---

<objective>
Extraer la detección/nombrado de cámara y la lectura de tarjeta SD de `MainWindow` a un nuevo mixin `app/ui/mixins/camera_mixin.py`, siguiendo el patrón canónico ya validado por `WifiMixin` (quick 260906-ci2): métodos movidos VERBATIM, composición por herencia múltiple `class MainWindow(QMainWindow, WifiMixin, CameraMixin):`, singletons importados a nivel de módulo del mixin, y test patching adaptado al namespace nuevo (`camera_mixin_module.db`).

Purpose: Continuar la reducción del god object `MainWindow` (roadmap 2026-09-06, Bloque 3). Es refactor PURO: cero cambio de comportamiento, cero strings nuevos de traducción, cero cambios en `app/core/`. `main_window.py` baja de 4141 → ~3790 líneas.

Output:
- `app/ui/mixins/camera_mixin.py` (nuevo, ~360 líneas) — 16 métodos + imports de módulo.
- `app/ui/main_window.py` — los 16 métodos eliminados; `class MainWindow(QMainWindow, WifiMixin, CameraMixin):`; `get_mounted_drives` retirado del import de `app.core.utils` (huérfano tras el movimiento).
- 5 ficheros de test con el parche paralelo `camera_mixin_module.db = self.db`.

## Alcance exacto del movimiento (16 métodos; verificado en vivo a 2026-09-06)

| Método | Línea HEAD | Rol |
|---|---|---|
| `_on_camera_rename_needed` | 1719 | señal `camera_rename_needed` del Ingestor |
| `_post_ingest_rename_dialog` | 1811 | renombrado post-ingesta de desconocidos |
| `_prompt_rename_camera` | 1881 | rename por doble clic en columna cámara |
| `_drive_label` | 2203 | `@staticmethod` helper de etiqueta de unidad |
| `_find_smallest_media` | 2208 | archivo media más pequeño (solo usado por 2321/2391, ambos movidos) |
| `_set_camera_cell_text` | 2226 | escritura celda cámara en source_list |
| `_camera_for_path` | 2236 | lookup de cámara por path en `_current_camera_map` |
| `_detect_camera_for_session` | 2246 | flujo I-03/I-14: conocido → auto → prompt |
| `_prompt_nombre_dispositivo` | 2341 | prompt manual de nombre |
| `_detect_camera_for_source` | 2365 | D-08/D-09, worker off-thread para AddSourceDialog |
| `_persist_camera_mapping` | 2402 | persistencia sd_cards/device_settings/known_devices |
| `_on_camera_cell_edited` | 2423 | edición por itemChanged |
| `_on_dialog_camera_name_changed` | 2439 | B-20 callback AddSourceDialog |
| `_detect_sd_card` | 4001 | info de tarjeta SD (QMessageBox) |
| `_on_auto_detect_toggled` | 4026 | toggle QSettings autoDetectDrives |
| `_auto_detect_removable_drives` | 4032 | auto-detección de unidades extraíbles |

Unión de las dos fuentes: la lista del planning context (13) + las que solo estaban en el roadmap note (`_post_ingest_rename_dialog`, `_find_smallest_media`) + `_drive_label`. Los 16 son autocontenidos y NO definen `eventFilter`.

## Requisitos previos verificados (no re-verificar, ya comprobados en el análisis)

- **Símbolos de ámbito de módulo usados por los cuerpos movidos:** `os`, `QTimer`, `QDate`, `QSettings`, `QInputDialog`, `QMessageBox`, `db`, `sd_reader`, `metadata_engine`, `get_mounted_drives`. NO usan `theme`, `translator`, `QtString`, `WIFI_DEVICE_ID`, `QColor`, `Qt`, `QTableWidgetItem`, `is_removable_drive` → no se importan en el mixin.
- **Imports locales dentro de métodos:** solo `import threading` y `import uuid` (líneas 2284-2285 de `_detect_camera_for_session`) → pasan a nivel de módulo del mixin por orden del plan (constraint b).
- **`get_mounted_drives` queda huérfano en main_window** (2 hits: import línea 21 + uso 4034, ambos movidos) → retirarlo de la línea 21. `sd_reader` (3838) y `metadata_engine` (755/1441/3311) SIGUEN en uso en main_window → sus imports permanecen.
- **Precedente WifiMixin:** no define `__init__` ni `super().__init__()` (verificado); CameraMixin tampoco.
- **Test namespace:** los tests de cámara actuales reasignan `mw.db = self.db` y parchean métodos sobre el singleton COMPARTIDO (`patch.object(sd_reader, ...)`, `patch.object(me_module.metadata_engine, ...)` — esos parches siguen funcionando porque el mixin referencia el MISMO objeto singleton). Lo único que cambia de namespace es `db` (reasignación de nombre de módulo) → requiere el parche paralelo en los 5 ficheros de test.
- **Archivos de test que construyen `mw.MainWindow()` con `mw.db` reasignado** (los 15 setUps a adaptar): test_main_window.py (12 bloques: clases en líneas 30, 105, 212, 273, 361, 462, 590, 741, 1037, 1142, 1197, 1242, 1338 — 12 que patchean mw.db; los bloques 673 (TestRenameCamera), 903 (TestFreeSpace), 915 (TestIntegrityReport), 975 (TestCardContentReport) NO construyen MainWindow → NO requieren parche), test_source_content.py (43-48/78-80), test_e2e.py (43-51/94-96), test_wifi_source.py (39-46/94-96), test_session_content_modes.py (151-156/184-185, solo el segundo setUp).

</objective>

<execution_context>
La ejecución sigue el patrón documentado del roadmap 2026-09-06 (Bloque 3, «Fricción de tests por bloque») y el precedente del quick 260906-ci2 (WifiMixin): método por método, VERBATIM, con commits atómicos por tarea.
</execution_context>

<context>
@.planning/notes/2026-09-06-roadmap-reduccion-mainwindow.md
@.planning/quick/260906-epl-bloque-1-extraer-los-4-di-logos-de-confi/260906-epl-SUMMARY.md
@app/ui/mixins/wifi_mixin.py
@app/ui/main_window.py
@tests/test_main_window.py
@tests/test_wifi_source.py
@tests/test_source_content.py
@tests/test_e2e.py
@tests/test_session_content_modes.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Crear app/ui/mixins/camera_mixin.py con los 16 métodos VERBATIM</name>
  <files>app/ui/mixins/camera_mixin.py</files>
  <action>Crear `app/ui/mixins/camera_mixin.py` siguiendo exactamente la forma de `app/ui/mixins/wifi_mixin.py` (quick 260906-ci2): clase `CameraMixin:` sin `__init__`, sin `super().__init__()`, docstring de clase en español (ej. «Métodos de detección/nombrado de cámara y lectura de tarjeta SD extraídos de MainWindow (quick 260906-fgl).»).

IMPORTS a nivel de módulo (solo estos; NINGÚN otro símbolo de main_window):
- stdlib: `import os`, `import threading`, `import uuid`
- `from PySide6.QtCore import QTimer, QDate, QSettings`
- `from PySide6.QtWidgets import QInputDialog, QMessageBox`
- `from app.core.db import db`
- `from app.core.sd_reader import sd_reader`
- `from app.core.metadata_engine import metadata_engine`
- `from app.core.utils import get_mounted_drives`

Cuerpos de métodos (en este orden, para diffabilidad): `_on_camera_rename_needed`, `_post_ingest_rename_dialog`, `_prompt_rename_camera`, `_drive_label` (mantener `@staticmethod`), `_find_smallest_media`, `_set_camera_cell_text`, `_camera_for_path`, `_detect_camera_for_session`, `_prompt_nombre_dispositivo`, `_detect_camera_for_source`, `_persist_camera_mapping`, `_on_camera_cell_edited`, `_on_dialog_camera_name_changed`, `_detect_sd_card`, `_on_auto_detect_toggled`, `_auto_detect_removable_drives`.

REGLAS del movimiento (contrato duro, cero cambio de comportamiento):
- Copiar cada cuerpo ABSOLUTAMENTE VERBATIM desde main_window.py (los cuerpos ya están a indentación 4 — la misma que requieren los métodos de la clase del mixin; la indentación no cambia). Docstrings, comentarios en español, `self.tr(...)`, llamadas `self.<método>` (`_refresh_source_list`, `_refresh_sessions_combo`, `update_start_button_state`, `_set_camera_cell_text`, `_persist_camera_mapping`, `_prompt_nombre_dispositivo`, `_find_smallest_media`, `_drive_label`) se mantienen IGUAL porque `self` ES la instancia de MainWindow en runtime y todo se resuelve por MRO.
- ÚNICA sustitución permitida: ELIMINAR las dos líneas `import threading` e `import uuid` del interior de `_detect_camera_for_session` (líneas 2284-2285 de HEAD) porque pasan a nivel de módulo. Nada más cambia: ni nombres, ni orden de parámetros, ni literales `tr()`, ni lógica, ni closures (`_apply_detection`, `scan`, `on_timeout` quedan idénticas).
- Las referencias a estado de instancia (`self._unknown_cameras`, `self._cam_detection_id`, `self._cam_timer`, `self._cam_scan_scheduled`, `self._cam_detected`, `self._current_camera_map`, `self._source_paths`, `self.ingest_status_label`, `self.project_camera_detection_mode`, `self.project_camera_detection_timeout`, `self.table`, `self._ingestors`, `self.isVisible`, `self.raise_`/`self.activateWindow`) se quedan como `self.<nombre>` SIN tocar: el mixin se compone EN MainWindow y esos atributos los inicializa `MainWindow.__init__` (verificado: 160-166, 190-191, 627-628, 1176).
- Comillas simples y estilo PEP 8 informal del repo (seguir el fichero wifi_mixin.py como plantilla de forma).

Qué NO hacer: no tocar ningún otro método de main_window, no renombrar/reordenar, no formatear el resto, no añadir logging, no cambiar `tr()` ni `translate()` por ningún otro mecanismo, no añadir `__init__` ni `super()` al mixin.</action>
  <verify>
    <automated>python -X utf8 -c "
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
new = open('app/ui/mixins/camera_mixin.py', encoding='utf-8').read()
old = __import__('subprocess').run(['git','show','HEAD:app/ui/main_window.py'], capture_output=True, encoding='utf-8').stdout
names = ['_on_camera_rename_needed','_post_ingest_rename_dialog','_prompt_rename_camera','_drive_label','_find_smallest_media','_set_camera_cell_text','_camera_for_path','_detect_camera_for_session','_prompt_nombre_dispositivo','_detect_camera_for_source','_persist_camera_mapping','_on_camera_cell_edited','_on_dialog_camera_name_changed','_detect_sd_card','_on_auto_detect_toggled','_auto_detect_removable_drives']
old_lines = old.split(chr(10)); new_lines = new.split(chr(10))
def body(lines, name):
    i = next(j for j,l in enumerate(lines) if l.startswith('    def '+name+'(') or l.startswith('    @staticmethod') and lines[j+1].startswith('    def '+name+'('))
    # para @staticmethod, i apunta al decorador
    if lines[i].startswith('    @staticmethod'): i += 1
    start = i
    j = i+1
    while j < len(lines) and (lines[j].startswith('    ') and not lines[j].startswith('    def ') and not lines[j].startswith('    @') or lines[j].strip()==''):
        j += 1
    return start, j
ok = True
for n in names:
    sb, eb = body(old_lines, n)
    ob = '\n'.join(old_lines[sb:eb])
    if n == '_detect_camera_for_session':
        ob = '\n'.join(l for l in ob.split('\n') if 'import threading' not in l and 'import uuid' not in l)
    if ob not in new:
        print('MISSING/ALTERED:', n); ok = False
print('VERBATIM-CHECK:', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
"
  </automated>
  <done>app/ui/mixins/camera_mixin.py existe con los 16 métodos en orden canónico; `python -m compileall -q app/ui/mixins/camera_mixin.py` pasa; import offscreen (`from app.ui.mixins.camera_mixin import CameraMixin`) pasa; el script VERBATIM-CHECK emite `VERBATIM-CHECK: PASS` (cuerpos idénticos a `git show HEAD:app/ui/main_window.py`; única diferencias permitidas: ausencia de `import threading`/`import uuid` dentro de `_detect_camera_for_session`).</done>
</task>

<task type="auto">
  <name>Task 2: Componer CameraMixin en MainWindow y eliminar los 16 métodos</name>
  <files>app/ui/main_window.py</files>
  <action>Cirugía quirúrgica en `app/ui/main_window.py` (cero reformateo del resto):

1. AÑADIR import junto a la línea 43: `from app.ui.mixins.camera_mixin import CameraMixin`.
2. CAMBIAR la declaración de clase (línea 127) a: `class MainWindow(QMainWindow, WifiMixin, CameraMixin):` — este orden MRO es el canónico del roadmap (WifiMixin primero; sin colisiones de nombres entre ambos mixins, verificado). Los mixins NO definen `__init__`, así que `MainWindow.__init__` sigue llamando directamente a `super().__init__()` → `QMainWindow.__init__`.
3. ELIMINAR los 5 bloques de métodos movidos, en sus ubicaciones exactas de HEAD (los cuerpos ya viven en camera_mixin.py desde Task 1; NO recortarlos aquí):
   - Líneas 1719–1722: `_on_camera_rename_needed`
   - Líneas 1811–1838: `_post_ingest_rename_dialog`
   - Líneas 1881–1900: `_prompt_rename_camera`
   - Líneas 2202–2466: bloque contiguo `_drive_label` (y su `@staticmethod`) + `_find_smallest_media` + `_set_camera_cell_text` + `_camera_for_path` + `_detect_camera_for_session` + `_prompt_nombre_dispositivo` + `_detect_camera_for_source` + `_persist_camera_mapping` + `_on_camera_cell_edited` + `_on_dialog_camera_name_changed`
   - Líneas 4001–4075: bloque contiguo `_detect_sd_card` + `_on_auto_detect_toggled` + `_auto_detect_removable_drives`
   Higiene de líneas en blanco: los borrados dejan exactamente DOS líneas en blanco antes de cada método vecino (`_show_table_context_menu` 1724, `_on_source_double_clicked` 1840, `_refresh_source_list` 1902, `_show_source_context_menu` 2468, `_reorganize_by_metadata` 4077) — verificar visualmente que no queden 3+ ni 0.
4. AJUSTAR el import de la línea 21: `from app.core.utils import create_folder_structure, get_mounted_drives, is_removable_drive, resource_path` → quitar `get_mounted_drives, ` (queda huérfano: sus 2 únicas apariciones, import + uso en `_auto_detect_removable_drives`, han sido movidas). Conservar `is_removable_drive` (usado en 1588/3399/3445), `create_folder_structure` y `resource_path`.
5. NO tocar nada más: los imports `db`, `sd_reader` (3838), `metadata_engine` (755/1441/3311) siguen en uso y PERMANECEN. No retirar `WIFI_DEVICE_ID`, ni imports de Qt, ni reformatear el resto del fichero. Todos los call sites externos de los métodos movidos (705, 1273, 1349, 1500, 1844, 2051, 2568, 2596-2597, 2988, 2992, 3204-3206, 3390, 3405, 3426, 3430, 3569, 3634, 4068) son `self.<método>` o `.connect(self.<método>)` → resuelven por MRO sin tocar nada.</action>
  <verify>
    <automated>python -X utf8 -c "
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
src = open('app/ui/main_window.py', encoding='utf-8').read()
names = ['_on_camera_rename_needed','_post_ingest_rename_dialog','_prompt_rename_camera','_drive_label','_find_smallest_media','_set_camera_cell_text','_camera_for_path','_detect_camera_for_session','_prompt_nombre_dispositivo','_detect_camera_for_source','_persist_camera_mapping','_on_camera_cell_edited','_on_dialog_camera_name_changed','_detect_sd_card','_on_auto_detect_toggled','_auto_detect_removable_drives']
bad = [n for n in names if re.search(r'\n    def '+n+r'\(', src)]
print('DEFS-REMAINING:', bad if bad else 'NONE')
assert not bad, 'method defs still in main_window'
print('COMPOSITION:', 'PASS' if 'class MainWindow(QMainWindow, WifiMixin, CameraMixin):' in src else 'FAIL')
assert 'class MainWindow(QMainWindow, WifiMixin, CameraMixin):' in src
print('GET_MOUNTED:', 'PASS' if 'get_mounted_drives' not in src else 'FAIL')
assert 'get_mounted_drives' not in src
print('MRO-IMPORT:', 'PASS' if 'from app.ui.mixins.camera_mixin import CameraMixin' in src else 'FAIL')
assert 'from app.ui.mixins.camera_mixin import CameraMixin' in src
# todos los usos restantes de los 16 nombres deben ser self.<name> (o .connect(self.<name>))
for n in names:
    for m in re.finditer(r'\b'+n+r'\b', src):
        ctx = src[max(0,m.start()-80):m.start()]
        assert ('self.' in ctx) or ('.connect(self.' in ctx), (n, ctx[-35:])
print('CALLSITES-MRO:', 'PASS')
"; if ($?) { python -m compileall -q app/ui/main_window.py; if ($?) { python -X utf8 -c "import os; os.environ.setdefault('QT_QPA_PLATFORM','offscreen'); import app.ui.main_window; print('IMPORT-MW: PASS')" } }
  </automated>
  <done>main_window.py compila, importa offscreen sin errores, declara `class MainWindow(QMainWindow, WifiMixin, CameraMixin):`, ya NO define ninguno de los 16 métodos, `get_mounted_drives` ha desaparecido del import de app.core.utils, y el script de verificación emite `DEFS-REMAINING: NONE`, `COMPOSITION: PASS`, `GET_MOUNTED: PASS`, `MRO-IMPORT: PASS`, `CALLSITES-MRO: PASS`. `python -m unittest tests.test_wifi_source -q` pasa (la línea 345 de wifi_mixin referencia `self._on_camera_rename_needed`, que ahora resuelve por MRO vía CameraMixin).</done>
</task>

<task type="auto">
  <name>Task 3: Adaptar el patching del singleton `db` en los 5 ficheros de test</name>
  <files>tests/test_main_window.py, tests/test_source_content.py, tests/test_e2e.py, tests/test_wifi_source.py, tests/test_session_content_modes.py</files>
  <action>Ajústese SOLO el patching de singletons (regla del roadmap: «Los tests NO se reescriben, solo se ajusta el patching»). NO se añaden ni cambian aserciones.

POR QUÉ: los 16 métodos movidos resuelven `db` desde el namespace de `app.ui.mixins.camera_mixin` (import a nivel de módulo). Los tests reasignan el nombre `mw.db = self.db` — eso ya NO alcanza a los métodos movidos; sin el parche paralelo escribirían en la BD real `data/sd_import.db` (contaminación y fallos enmascarados). En cambio `metadata_engine` y `sd_reader` NO necesitan ningún parche nuevo: los tests los parchean con `patch.object(<singleton>.get_video_metadata / get_volume_serial, ...)` sobre el MISMO objeto instancia que el mixin referencia → el parche se ve desde ambos namespaces.

CAMBIOS por fichero:
1. Añadir el import del módulo mixin junto al `import app.ui.main_window as mw` existente: `import app.ui.mixins.camera_mixin as camera_mixin_module`.
2. En CADA setUp que contenga `mw.db = self.db`: añadir `self._orig_cam_db = camera_mixin_module.db` (junto a `self._orig_db = mw.db`) y `camera_mixin_module.db = self.db` (inmediatamente después de `mw.db = self.db`). En el tearDown emparejado: añadir `camera_mixin_module.db = self._orig_cam_db` (junto a `mw.db = self._orig_db`).

REGLA DETERMINISTA (aplicar por grep, no por memoria): todo setUp con `mw.db = self.db` recibe el parche, tenga o no MainWindow — es inerte si ningún método de cámara se ejecuta y protector si alguno se ejecuta indirectamente.

SetUps exactos a tocar (líneas HEAD de `mw.db = self.db`):
- `tests/test_main_window.py` — TODOS los 14: 43, 120, 226, 286, 376, 476, 603, 755, 924, 1050, 1154, 1210, 1255, 1351 (+ sus 14 tearDowns).
- `tests/test_source_content.py` — 1: setUp líneas ~43-48 (añadir `_orig_cam_db` y `camera_mixin_module.db = self.db`), tearDown ~78-80.
- `tests/test_e2e.py` — 1: setUp ~43-51, tearDown ~94-96.
- `tests/test_wifi_source.py` — 1: setUp ~39-46 (ya tiene el patrón `wifi_mixin_module.db`, añadir el de cámara al lado), tearDown ~94-96.
- `tests/test_session_content_modes.py` — 1: SOLO el setUp que contiene `mw.db = self.db` (~151-156) + su tearDown (~184-185). El primer setUp (~51) patchea `ingestor_module.db` y no construye MainWindow → NO tocarlo.

IMPORTANTE: no reescribir asserts, no renombrar, no tocar `test_device_registry.py` (sus tests de `_on_dialog_camera_name_changed` simulan el flujo con `self.db` directamente, sin MainWindow; el string-check de la línea 253 sigue verde porque `_auto_detect_removable_drives` ya no está en main_window).</action>
  <verify>
    <automated>python -m unittest tests.test_main_window tests.test_source_content tests.test_e2e tests.test_wifi_source tests.test_session_content_modes -v</automated>
  </verify>
  <done>Los 5 ficheros de test pasan 100% en aislamiento (unittest -v, sin fallos ni errores). Suite completa: `python -m pytest tests/ -q` → exactamente el baseline documentado en el quick 260906-epl (393 passed, 5 skipped, 28 subtests) con la ÚNICA falla conocida pre-existente order-dependent `tests/test_mtp.py::TestThreadLocalManager::test_wpd_session_devicename_no_duplicate` — si aparece CUALQUIER otra falla, es un defecto de este refactor y debe corregirse antes de commitear.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| singleton module-namespace ↔ tests | Los tests reasignan nombres de módulo (`mw.db`, `camera_mixin_module.db`) — el namespace donde un método resuelve su singleton decide qué BD usa en runtime |
| MainWindow ↔ mixins (MRO) | Métodos de wifi_mixin/main_window invocan métodos de cámara por `self.` — la resolución depende del orden de composición |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fgl-01 | Tampering | app/ui/mixins/camera_mixin.py | medium | mitigate | Script VERBATIM-CHECK del Task 1 (cuerpos byte-idénticos contra `git show HEAD:app/ui/main_window.py`, única diffs permitida: hoisting de `import threading`/`import uuid`) + gate de suite completa del Task 3 |
| T-fgl-02 | Spoofing | resolución de `db` en los 16 métodos movidos | high | mitigate | Parche paralelo `camera_mixin_module.db = self.db` en los 18 setUps que reasignan `mw.db` (14 en test_main_window + 1 por cada source_content/e2e/wifi_source/session_content_modes) — sin él los métodos movidos escribirían en la BD real del desarrollador durante los tests |
| T-fgl-03 | Denial of Service | tests/test_mtp.py (falla order-dependent) | low | accept | Falla pre-existente documentada en el quick 260906-epl, ajena a app/ui/; baseline verificado con worktree en HEAD sin cambios; se registra y no se repara aquí |
| T-fgl-04 | Elevation of Privilege | `_drive_label` @staticmethod expuesto via MRO a métodos NO movidos (2051, 2596-2597, 3390, 3426, 3569) | low | accept | Comportamiento idéntico al previo: antes era método estático de MainWindow, ahora lo es de CameraMixin; la resolución por MRO es 1:1 con el acceso `MainWindow._drive_label` previo |
</threat_model>

<verification>
1. **Equivalencia de método (= verificación de cero cambio de comportamiento):** script VERBATIM-CHECK del Task 1 emite PASS — cada uno de los 16 cuerpos en camera_mixin.py es idéntico a su homólogo de HEAD salvo las 2 líneas de imports hoisted.
2. **Composición y limpieza:** script del Task 2 emite los 5 PASS (DEFS-REMAINING NONE, COMPOSITION, GET_MOUNTED, MRO-IMPORT, CALLSITES-MRO); `compileall` de ambos ficheros sin errores; `import app.ui.main_window` offscreen sin errores.
3. **Cobertura de namespaces de test:** `rg "mw\.db = self\.db" tests/` y verificación manual de que cada setUp listado en Task 3 tiene su `camera_mixin_module.db = self.db` emparejado (18 setUps). El patching de `metadata_engine`/`sd_reader` permanece 100% sobre el singleton compartido (patch.object) — sin cambios.
4. **Gates de suite:** los 5 ficheros adaptados pasan aislados; `python -m pytest tests/ -q` reproducen el baseline conocido (393 passed, 5 skipped, 28 subtests, única falla pre-existente test_mtp order-dependent).
5. **Líneas:** `main_window.py` pasa de 4141 → ~3790 (-350 del Bloque 3 del roadmap).
</verification>

<success_criteria>
- Los 16 métodos de detección/nombrado de cámara y lectura SD residen en `app/ui/mixins/camera_mixin.py` y son invocables sobre MainWindow por composición (MRO `MainWindow(QMainWindow, WifiMixin, CameraMixin)`).
- Cero cambio de comportamiento: cuerpos verbatim verificados por script; `tr()`/SQL/estado intactos; sin strings de traducción nuevos; `app/core/` intocado.
- Los tests pasan respecto al baseline (5 ficheros aislados al 100%; suite completa sin fallas NUEVAS).
- No se introducen imports huérfanos en main_window.py (get_mounted_drives movido; sd_reader/metadata_engine siguen usados).
- `eventFilter` único en el MRO (main_window.py:2497) — ninguno de los 16 métodos lo define.
- Commit atómico único con los 7 ficheros del refactor.
</success_criteria>

<output>
Tras el Task 3: commit atómico único con los 7 ficheros (1 nuevo + 6 modificados):
`git add app/ui/mixins/camera_mixin.py app/ui/main_window.py tests/test_main_window.py tests/test_source_content.py tests/test_e2e.py tests/test_wifi_source.py tests/test_session_content_modes.py`
`git commit -m "refactor(ui): extraer deteccion/nombrado de camara y lectura SD de MainWindow a CameraMixin"`

Crear `.planning/quick/260906-fgl-bloque-3-extraer-la-deteccion-nombrado-d/260906-fgl-SUMMARY.md` al terminar (patrón del quick 260906-epl: dependencia graph, tech tracking, cobertura por tarea, decisiones, deviations, métricas, self-check). El commit de docs (PLAN/SUMMARY/STATE) lo gestiona el orquestador.
</output>