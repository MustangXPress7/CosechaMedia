---
quick_id: 260906-epl
slug: bloque-1-extraer-los-4-di-logos-de-confi
title: "Bloque 1: extraer los 4 diálogos de configuración inline de MainWindow a ficheros propios"
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/ui/project_settings_dialog.py
  - app/ui/camera_overrides_dialog.py
  - app/ui/names_manager_dialog.py
  - app/ui/dump_locations_dialog.py
  - app/ui/main_window.py
requirements: [QUICK-260906-epl]
autonomous: true
---

# Quick Task: Extraer los 4 diálogos de configuración inline de MainWindow

## Why

`app/ui/main_window.py` (~4590 líneas) es el god object documentado en STATE.md
(v1.6.0, quick 260906-ci2 ya extrajo el flujo WiFi a `WifiMixin`, dejando el
fichero en ~4159 líneas). Los 4 diálogos de configuración inline
(`_show_metadata_dialog` 726-880, `_show_camera_overrides_dialog` 882-988,
`_show_names_manager` 990-1096, `_manage_dump_locations` 1119-1209) son
dominios autónomos de ~485 líneas que pueden vivir en clases `QDialog` propias
siguiendo el patrón `AboutDialog`/`FtpPickerDialog` (`app/ui/about_dialog.py`,
`app/ui/ftp_picker.py`). `_manage_footage_folders` (1098-1106) y
`_manage_containers` (1108-1117) son wrappers de `_show_names_manager` que se
convierten en wrappers directos de `NamesManagerDialog`.

**Contrato duro: refactor puro, CERO cambio de comportamiento.** La
construcción de UI y la lógica save/defaults/reorder se mueven VERBATIM a las
nuevas clases (solo cambia `self.` → `self.window.` para las referencias a
estado del proyecto, que sigue viviendo en `MainWindow`). Los 6 métodos de
`MainWindow` conservan sus nombres exactos como wrappers finos — la toolbar
(línea 330, cadena `"_show_metadata_dialog"`) y los menús (3446/3462/3468/3472)
siguen resolviendo sin tocar nada. Las escrituras a DB se mantienen
byte-equivalentes (mismo SQL, mismos argumentos, misma secuencia commit/close).

**Análisis previo (hecho para el ejecutor — no repetir):**

- `rg` en `tests/` de los 6 nombres → CERO referencias. Ningún test llama a
  estos métodos ni toca `_names_manager`. **No hay que modificar ni crear
  tests.** El patching de tests se mantiene porque cada módulo nuevo importa el
  singleton `from app.core.db import db` (patrón repo, igual que
  `ftp_picker.py:15`), de modo que un test futuro puede hacer
  `patch.object(modulo_dialogo, "db", ...)` igual que `test_add_source_dialog.py`
  hace con `patch.object(asd, "db", self.db)` (línea 800).
- Tras la extracción NO queda ningún import huérfano en `main_window.py`:
  contado por símbolo, todos los usados por los métodos extraídos
  (`QTableWidget`, `QListWidget`, `QDateEdit`, `QFormLayout`, `QGroupBox`,
  `QGridLayout`, `QInputDialog`, `QFileDialog`, `QCheckBox`, `QComboBox`,
  `QSpinBox`, `QHBoxLayout`, `QVBoxLayout`, `QDialog`, `QHeaderView`, `QSettings`,
  `QMessageBox`, `json`, `os`) tienen usos restantes fuera de las líneas
  726-1209. **No tocar el bloque de imports de QtWidgets/QtCore de
  `main_window.py`** — solo AÑADIR los 4 imports de los nuevos módulos.
- Sin strings nuevos: todos los `tr()` se mueven tal cual → **no hay que tocar
  `app/i18n/`** ni `.ts`/`.qm`.

## What

4 ficheros nuevos en `app/ui/` (clases `ProjectSettingsDialog`,
`CameraOverridesDialog`, `NamesManagerDialog`, `DumpLocationsDialog`) + 6
métodos de `main_window.py` convertidos en wrappers finos (~10 líneas c/u).

Cada clase nueva sigue el patrón `AboutDialog`:

- `class XDialog(QDialog)` con el wrapper `def tr(self, text, *args, **kwargs):
  return QtString(super().tr(text, *args, **kwargs))` (import
  `from app.core.translator import QtString`) — necesario para conservar
  `tr("...").arg(...)`.
- `from app.core.db import db` a nivel de módulo (singleton, patrón repo).
- Comentarios y docstrings en español, comillas simples, tipo de codificación
  utf-8 (los ficheros fuente tienen acentos). Docstring de módulo de una línea
  explicando el propósito (ej. `"""Dialogo de configuracion general del proyecto."""`).
- Los comentarios existentes dentro de los cuerpos se copian VERBATIM
  (p. ej. `# --- Grupo Configuración general ---`, `# Cámaras de sesiones activas`).

## Tasks

### Task 1 — Crear `ProjectSettingsDialog` y `CameraOverridesDialog`

**Files:**
- `app/ui/project_settings_dialog.py` (nuevo)
- `app/ui/camera_overrides_dialog.py` (nuevo)

**Action:**

**project_settings_dialog.py** — Clase `ProjectSettingsDialog(QDialog)`. Copiar
el cuerpo de `_show_metadata_dialog` (main_window.py 726-880) VERBATIM con
estas sustituciones mecánicas:

- Constructor: `def __init__(self, window, open_overrides_cb=None)` con
  `super().__init__(window)`, `self.window = window`,
  `self._open_overrides_cb = open_overrides_cb`. El cuerpo de construcción del
  diálogo va en `__init__` (mismo orden de widgets, layouts, grupos, botones y
  conexiones que el original). `self.tr(...)` se mantiene (wrapper de la clase).
- `db.` se mantiene (singleton importado a nivel de módulo).
- Sustituciones `self.` → `self.window.`: las 10 lecturas/escrituras de estado
  del proyecto (`project_folder_name`, `project_organization_type`,
  `project_date_mode`, `project_manual_date`, `project_date`,
  `project_camera_detection_mode`, `project_camera_detection_timeout`,
  `project_generate_proxies`, `project_proxy_resolution`,
  `project_camera_date_overrides`) y `current_project_id`. Consultar y asignar
  SIEMPRE `self.window.<attr>` (el estado sigue viviendo en MainWindow).
- `self._refresh_source_list()` (línea 853, dentro de `_save`) →
  `self.window._refresh_source_list()`.
- `self.ingest_status_label.setText(...)` (línea 867, dentro de `_set_defaults`)
  → `self.window.ingest_status_label.setText(...)`.
- La closure `_open_overrides` (760-762) pasa a método
  `def _open_overrides(self):` cuyo cuerpo es
  `if self._open_overrides_cb is not None: self._open_overrides_cb()`;
  el botón se conecta a `self._open_overrides`.
- Guardar el SQL de `_save` (840-852) Y la llamada `db.add_footage_folder`
  (837) VERBATIM (mismo SQL, mismos args, `conn.commit()` + `conn.close()`).
- `_set_defaults` conserva `QSettings("Audiovisual Production", "CosechaMedia")`
  y los 6 `settings.setValue(...)` VERBATIM.
- `btn_save.setObjectName("PrimaryAction")` (825) se conserva.
- Cerrar con `self.exec()` NO se llama dentro de la clase: el wrapper de
  MainWindow lo ejecuta. El método termina en el `main_layout.addLayout(btn_row)`
  (todos los widgets ya construidos; sin `exec()`).

Imports del módulo: `PySide6.QtCore.QSettings`, `PySide6.QtWidgets`
(QCheckBox, QComboBox, QDateEdit, QDialog, QFormLayout, QGridLayout, QGroupBox,
QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout),
`from app.core.db import db`, `from app.core.translator import QtString`.
NO se usa `theme` ni `os` en este diálogo — no importarlos.

**camera_overrides_dialog.py** — Clase `CameraOverridesDialog(QDialog)`. Copiar
el cuerpo 882-979 (construcción del diálogo, tabla, filas por cámara activa,
closure `save`) VERBATIM con estas sustituciones:

- Constructor: `def __init__(self, window)` con `super().__init__(window)` y
  `self.window = window`; cuerpo de construcción en `__init__`.
- Imports locales del método original (883-885: `import json`,
  `from PySide6.QtWidgets import QHeaderView`,
  `from PySide6.QtCore import QDate, Qt`) suben al top del módulo
  (junto a QComboBox, QDateEdit, QDialog, QHBoxLayout, QLabel, QPushButton,
  QTableWidget, QTableWidgetItem, QVBoxLayout, `db`, `QtString`).
- `self.tr(...)` se mantiene; `self.project_camera_date_overrides` (lecturas
  904, 958) y `self.current_project_id` (898, 901) → `self.window.` para ambos.
- `save()` (955-976) pasa a método privado `_save` (misma lógica de merge
  VERBATIM, incluido el `try/except Exception` de 961-962). La asignación final
  `self.project_camera_date_overrides = json.dumps(merged)` (975) →
  `self.window.project_camera_date_overrides = json.dumps(merged)`, y cierra
  con `self.accept()` (no `dialog.accept()`).
- `btn_cancel.clicked.connect(dialog.reject)` (979) → `self.reject`.
- Lo que NO entra en la clase: el bloque 980-988 (`if dialog.exec():` +
  persistencia SQL de `camera_date_overrides`). Ese bloque se queda en el
  wrapper de MainWindow (Task 3), que es quien ejecuta `exec()`.
- La clase NO llama a `exec()`.

**Verify:**
- `python -m compileall -q app/ui/project_settings_dialog.py app/ui/camera_overrides_dialog.py` (sin errores)
- Smoke offscreen: `$env:QT_QPA_PLATFORM='offscreen'; python -c "from app.ui.project_settings_dialog import ProjectSettingsDialog; from app.ui.camera_overrides_dialog import CameraOverridesDialog; print('ok')"` (sin ImportError; los dos módulos importan)
- La suite completa NO se toca en esta tarea (los módulos aún no se referencian desde main_window) — se corre en Task 3.

**Done:** Existen los dos ficheros con las clases completas; la lógica
save/merge/update de ambos es byte-equivalente a la original (consultable con
`git diff` previo vs nuevo módulo); `main_window.py` intacto.

### Task 2 — Crear `NamesManagerDialog` y `DumpLocationsDialog`

**Files:**
- `app/ui/names_manager_dialog.py` (nuevo)
- `app/ui/dump_locations_dialog.py` (nuevo)

**Action:**

**names_manager_dialog.py** — Clase `NamesManagerDialog(QDialog)`. Copiar el
cuerpo de `_show_names_manager` (990-1096) VERBATIM con estas sustituciones:

- Constructor: `def __init__(self, parent=None, title="", getter=None,
  add_cb=None, rename_cb=None, delete_cb=None, duplicate_cb=None)` — firmado
  así para que los wrappers de MainWindow pasen los argumentos exactos que hoy
  recibe `_show_names_manager`. Almacenar `self._getter`, `self._add_cb`,
  `self._rename_cb`, `self._delete_cb`, `self._duplicate_cb` y aplicar
  `setWindowTitle(title)`, `setMinimumWidth(380)`, `setMinimumHeight(360)`.
- `self._names_manager = {"filter": "", "items": []}` (1014) pasa a atributo de
  instancia del diálogo con el MISMO nombre (verificado: nada externo lee esa
  atributo ni en `main_window.py` ni en `tests/`). Dentro de la clase,
  `self._names_manager["filter"]` / `["items"]` se mantienen tal cual pero
  referidos al diálogo (es decir, `self._names_manager[...]` sigue siendo el
  mismo código, ahora sobre la instancia del diálogo).
- Las closures pasan a métodos privados con la misma lógica VERBATIM:
  `_refresh` (1016-1025), `_on_search` (1027-1029, conecta `search.textChanged`),
  `_selected` (1034-1036), `_add` (1038-1043), `_dup` (1045-1050),
  `_ren` (1052-1060), `_del` (1062-1073). Llamadas internas `refresh()` →
  `self._refresh()`. Los callbacks se invocan como `self._add_cb(name)`,
  `self._rename_cb(name, new_name)`, `self._delete_cb(name)`,
  `self._duplicate_cb(name)` — exactamente igual que el original invocaba
  `add_cb`/`rename_cb`/etc.
- `QInputDialog.getText(dialog, ...)` (1039, 1056) y
  `QMessageBox.question(dialog, ...)` (1066-1069) → `... (self, ...)`.
- `btn_close.clicked.connect(dialog.accept)` (1095) → `self.accept`.
- `hint.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 10px;")`
  (1004) se conserva → import `from app.ui import theme`.
- Sin `exec()` dentro de la clase (lo ejecuta el wrapper).
- Imports: `PySide6.QtWidgets` (QDialog, QHBoxLayout, QInputDialog, QLabel,
  QLineEdit, QListWidget, QMessageBox, QPushButton, QVBoxLayout), `theme`,
  `QtString`.

**dump_locations_dialog.py** — Clase `DumpLocationsDialog(QDialog)`. Copiar el
cuerpo 1123-1209 (construcción del diálogo, `refresh`, `_add`, `_del`, `_move`,
botones) VERBATIM con estas sustituciones:

- Constructor: `def __init__(self, window)` con `super().__init__(window)` y
  `self.window = window`; cuerpo de construcción en `__init__`; terminar
  `__init__` con `self._refresh()` (llamada inicial que el original hace en
  1208 antes de `exec()`).
- `self.tr(...)` se mantiene; `self.current_project_id` → `self.window.current_project_id`
  (usos en `refresh` 1142, `_add` 1169, `_del` 1176-1177, `_move` 1184-1190);
  `self.dest_root` (1163) → `self.window.dest_root`.
- `db.dump_locations(...)`, `db.add_dump_location(...)`,
  `db.delete_dump_location(...)`, `db.reorder_dump_locations(...)` se mantienen
  (singleton `db` importado a nivel de módulo).
- Closures → métodos privados: `_refresh` (1140-1149), `_add` (1161-1169),
  `_del` (1171-1178), `_move(delta)` (1180-1193). `refresh()` interno →
  `self._refresh()`. Conexiones de botones (1195-1198) idénticas
  (`btn_up.clicked.connect(lambda: self._move(-1))` etc.).
- `QFileDialog.getExistingDirectory(dialog, ...)` (1162-1163) y
  `QInputDialog.getText(dialog, ...)` (1167) → `... (self, ...)`.
- `btn_close.setObjectName("PrimaryAction")` (1201) se conserva;
  `btn_close.clicked.connect(dialog.accept)` (1205) → `self.accept`.
- El guard del inicio (`if self.current_project_id is None: QMessageBox.information...`)
  (1120-1122) NO entra en la clase — se queda en el wrapper de MainWindow.
- Imports: `os`, `PySide6.QtWidgets` (QDialog, QFileDialog, QHBoxLayout,
  QInputDialog, QLabel, QListWidget, QPushButton, QVBoxLayout), `theme`,
  `db`, `QtString`. (QMessageBox no se usa dentro — el guard queda fuera.)

**Verify:**
- `python -m compileall -q app/ui/names_manager_dialog.py app/ui/dump_locations_dialog.py`
- Smoke offscreen: `$env:QT_QPA_PLATFORM='offscreen'; python -c "from app.ui.names_manager_dialog import NamesManagerDialog; from app.ui.dump_locations_dialog import DumpLocationsDialog; print('ok')"`

**Done:** Existen los dos ficheros; la lógica reorder/refresh de
DumpLocationsDialog y refresh/add/dup/ren/del de NamesManagerDialog es
byte-equivalente a la original; `main_window.py` intacto.

### Task 3 — Reconvertir los 6 métodos de MainWindow en wrappers finos + suite

**Files:**
- `app/ui/main_window.py`

**Action:**

1. **Añadir imports** (junto a los imports de diálogos existentes, línea 28-30
   zona de `app.ui.*`):
   ```python
   from app.ui.project_settings_dialog import ProjectSettingsDialog
   from app.ui.camera_overrides_dialog import CameraOverridesDialog
   from app.ui.names_manager_dialog import NamesManagerDialog
   from app.ui.dump_locations_dialog import DumpLocationsDialog
   ```
   NO tocar nada más del bloque de imports (verificado: ningún símbolo queda
   huérfano tras la extracción).

2. **Reemplazar el cuerpo** de las líneas 726-1209 (los 6 métodos
   `_show_metadata_dialog` … `_manage_dump_locations`) por estos wrappers finos
   (los nombres de método se conservan EXACTOS):

   ```python
   def _show_metadata_dialog(self):
       ProjectSettingsDialog(self, open_overrides_cb=self._show_camera_overrides_dialog).exec()

   def _show_camera_overrides_dialog(self):
       dialog = CameraOverridesDialog(self)
       if dialog.exec():
           # Persistir al proyecto
           if self.current_project_id is not None:
               conn = db.get_connection()
               cursor = conn.cursor()
               cursor.execute('UPDATE projects SET camera_date_overrides=? WHERE id=?',
                              (self.project_camera_date_overrides, self.current_project_id))
               conn.commit()
               conn.close()

   def _manage_footage_folders(self):
       NamesManagerDialog(self, self.tr("Personalizar carpeta de footage"),
                          db.get_footage_folders, db.add_footage_folder,
                          db.rename_footage_folder, db.delete_footage_folder,
                          db.duplicate_footage_folder).exec()

   def _manage_containers(self):
       NamesManagerDialog(self, self.tr("Personalizar contenedores de archivos"),
                          db.get_containers, db.add_container, db.rename_container,
                          db.delete_container, None).exec()
       metadata_engine.refresh_file_types()

   def _manage_dump_locations(self):
       if self.current_project_id is None:
           QMessageBox.information(self, self.tr("Sin proyecto"), self.tr("Selecciona un proyecto primero."))
           return
       DumpLocationsDialog(self).exec()
   ```

   Detalles que garantizan comportamiento idéntico:

   - El bloque persist de `camera_date_overrides` (SQL + commit + close) es el
     mismo del original 980-988, que vivía tras `if dialog.exec():` — se
     conserva VERBATIM en el wrapper.
   - El guard de `_manage_dump_locations` es el original 1120-1122 VERBATIM
     (mismos texts de `tr`, mismo `return`).
   - `_manage_footage_folders`/`_manage_containers` pasan al diálogo los MISMO
     callbacks bound de `db` que hoy recibe `_show_names_manager`
     (get_footage_folders/add_footage_folder/rename/delete/duplicate, y
     get_containers/add_container/rename_container/delete_container + `None`
     para duplicate). `_manage_containers` conserva la llamada
     `metadata_engine.refresh_file_types()` tras el `exec()`.
   - `_show_names_manager` desaparece de MainWindow (nada más la llama; verificado).
   - El cierre `exec()` de cada wrapper replica el del original (`dialog.exec()`
     sin usar el valor de retorno, salvo el `if dialog.exec():` de overrides).

3. **Comprobación de diffs:** tras editar, verificar con `git diff` que las
   únicas líneas eliminadas son las de los 6 cuerpos (726-1209) y que los 6
   nombres de método siguen presentes como wrappers.

**Verify:**
- `$env:QT_QPA_PLATFORM='offscreen'; python -c "import app.ui.main_window; print('ok')"` (importa sin error)
- Suite completa: `python -m pytest tests/ -q` (runner pytest sobre suites unittest; si pytest no está, `python -m unittest discover -s tests -q`). Debe pasar sin modificaciones de tests.
- `git diff --stat app/ui/main_window.py` muestra ~-440 líneas netas en el fichero (484 eliminadas − ~45 de wrappers e imports).

**Done:** Los 6 métodos son wrappers finos; `main_window.py` reduce su tamaño en
~440 líneas; los 4 módulos nuevos existen y son 100% funcionales; la suite
completa pasa; `git diff` no muestra ningún cambio de lógica (solo movimiento +
sustitución `self.`→`self.window.`).

## Acceptance Criteria

- [ ] La app arranca (`python main.py` o import de `main_window`) sin errores.
- [ ] Los 4 diálogos se abren desde sus entradas (botón Configuración línea 330,
      menús 3446/3462/3468/3472, botón «Gestionar overrides…» dentro del de
      configuración) y se comportan igual: guardar persiste en DB, «Establecer
      como predeterminado» escribe QSettings + mensaje de estado, reordenar
      destinos persiste el orden, cerrar cancela.
- [ ] `python -m pytest tests/ -q` verde (sin cambios de tests).
- [ ] `main_window.py` ha bajado de ~4590 a ~4150 líneas.
- [ ] Ningún import roto ni huérfano en `main_window.py` (bloque de imports de
      QtWidgets/QtCore intacto salvo los 4 imports añadidos).
- [ ] Strings de traducción intactos (ningún `tr()` nuevo/modificado; sin tocar
      `app/i18n/`).

## Verification

Orden: Task 1 → Task 2 → Task 3 (Task 3 depende de que existan los 4 módulos).
Cada tarea tiene su verify local; el gate global es la suite completa de Task 3.
Como refactor puro sin superficie nueva, el `git diff` es la herramienta de
revisión: no debe haber ninguna línea de lógica alterada, solo movimiento +
sustituciones mecánicas documentadas.

## Threat Model

Sin nuevas trust boundaries: refactor local de UI, sin red, sin I/O nuevo, sin
dependencias nuevas (no aplica package-legitimacy gate). Único riesgo: regresión
de comportamiento por errores de copia.

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260906-epl-01 | Tampering (self) | Los 4 diálogos extraídos vs. original inline | medium | mitigate | Copia VERBATIM con sustituciones mecánicas documentadas; `git diff` revisado línea a línea; suite completa (`pytest tests/`) como gate |
| T-260906-epl-02 | Spoofing | `window` references (self. → self.window.) | low | mitigate | Solo las 13 referencias de estado de proyecto documentadas cambian de prefijo; el resto de `self.` queda en la clase del diálogo; verify de import + arranque |

## Output

Commit único al terminar las 3 tareas:
`refactor(ui): extraer los 4 diálogos de configuración de MainWindow a app/ui/`
con los 5 ficheros (4 nuevos + main_window.py).