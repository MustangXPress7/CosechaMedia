# UI Layout Fixes - Pending Changes

## Context
After applying the QSplitter, sess_post_row, and destination simplification changes, we identified 4 more pending changes plus a source bar fix.

## Changes

### 1. Source bar fix (collapsing issue)
- The fixed-width source bar prevents the splitter from collapsing
- The "+" button stretches instead of the bar being flexible
- Fix: Make source bar take minimum space, let "+" button shrink

### 2. Move "Generar Proxies" to project config
- Currently in left_col (ingest UI) with `chk_generate_proxies` and `proxy_resolution`
- Move to project settings dialog (metadata/config)
- Remove from main_window left panel

### 3. "Modo delicado" per device with toggle
- Currently `chk_session_delicate` in sessions QGroupBox
- Remove from sessions
- Associate delicate mode per device (not per session)
- Add a toggle with lightning (fast) / snail (delicate) icons where user switches modes

### 4. QR option in "Ruta de origen" column
- Currently QR is in "contenido" column
- Move to "ruta de origen" column
- "contenido" column stays as regular sources + selective dump option

### 5. Edit pencil + description box
- Move edit pencil to far right
- Box the description like sessions and post-ingest actions (QGroupBox)

### 6. WiFi content column: files/folders switch
- In the content column of the ingest table, when source is WiFi
- Instead of showing content_summary or a simple label
- Show a toggle switch: "Archivos" / "Carpetas" mode
- This selects whether the WiFi upload sends individual files or folder structure
- Lightens the QR window interface — mode selection happens in the table, not in the QR dialog
- Store per-session in DB (new column or use existing `content_filter` JSON)
- Style: same as delicate mode toggle (zap/snail pattern)

## Files
- `app/ui/main_window.py` - all UI changes
- `tests/test_source_content.py` - test updates
