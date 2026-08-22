---
phase: 260822-ive
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - LICENSE
  - README.md
  - main.py
  - .github/workflows/build.yml
  - docs/SIGNING.md
autonomous: true
requirements: []

estimate:
  tokens: 50000
  raw_tokens: 25000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "El estado legal del repo es inequívoco: LICENSE contiene el texto canónico GPLv3, ambas mitades del README declaran GPL-3.0-or-later, y main.py lleva el aviso de copyright/licencia."
    - "No queda ninguna referencia a la licencia no comercial anterior fuera de .planning/."
    - "El zip de macOS publicado está firmado ad-hoc ANTES de comprimirse y de calcular su sidecar SHA-256 (el hash publicado corresponde al artefacto firmado)."
    - "Un mantenedor puede seguir docs/SIGNING.md para solicitar firma vía SignPath Foundation y saber qué paso de CI añadir cuando lleguen las credenciales; un usuario de macOS tiene instrucciones de primera apertura enlazadas desde ambas mitades del README."
  artifacts:
    - "LICENSE — texto canónico GPLv3 descargado de gnu.org (verificado por marcadores estructurales, nunca escrito de memoria)"
    - "README.md — secciones License/Licencia simétricas EN/ES + un enlace a docs/SIGNING.md en cada mitad (Download/Descarga)"
    - "main.py — cabecera de aviso GPL añadida"
    - ".github/workflows/build.yml — paso de firma ad-hoc macOS dentro del job existente"
    - "docs/SIGNING.md — hoja de ruta de firma en español (estado actual, SignPath Foundation, workaround Gatekeeper, Linux)"
  key_links:
    - "README License EN ↔ ES (párrafos espejo, mismo SPDX GPL-3.0-or-later)"
    - "LICENSE (GPLv3) ↔ declaración SPDX de ambas mitades del README"
    - "build.yml job macOS: orden plist → codesign → ditto → sha256sum (sidecar calculado sobre el zip ya firmado)"
    - "README Download EN/ES ↔ docs/SIGNING.md (un enlace por mitad)"
---

<objective>
Cambiar la licencia del proyecto a GPL-3.0-or-later (texto canónico + README bilingüe + cabecera en main.py) y preparar la firma de binarios: firma ad-hoc macOS en CI + hoja de ruta de firma documentada (docs/SIGNING.md).

Purpose: El repo aún es de autor único — tras aceptar la primera contribución externa una relicensing ya no sería legalmente limpia (haría falta acuerdo de todos los titulares). GPL-3.0-or-later habilita contribuidores externos. La firma ad-hoc en CI reduce los falsos «app dañada» en macOS, y docs/SIGNING.md deja trazado el camino hacia SignPath Foundation (Windows) sin meter CI especulativo que no se puede probar hasta tener credenciales.

Decisiones bloqueadas (del orquestador — NO NEGOCIABLES):
- D-01: Licencia → GPL-3.0-or-later. Objetivo: permitir contribuidores externos. Un futuro dual licensing/pago es plausible pero NO forma parte de esta tarea (no implementarlo ni prometerlo como activo).
- D-02: Estrategia de firma — Windows: objetivo SignPath Foundation (firma OSS gratuita; requiere licencia OSI-aprobada, GPLv3 cualifica; la SOLICITUD es manual y está fuera de esta tarea → solo roadmap documentado). macOS: SIN Apple Developer de pago; distribuir sin firma verificable pero con firma ad-hoc en CI + documentar el workaround de Gatekeeper. Linux: ya cubierto (`.sha256` por asset). Sin distribución Docker para Mac (sin USB passthrough).

Output: LICENSE reemplazada, README.md simétrico actualizado, main.py con cabecera, build.yml con codesign ad-hoc en macOS, docs/SIGNING.md nuevo.
</objective>

<execution_context>
@C:/Users/JoanRamon/.config/opencode/gsd-core/workflows/execute-plan.md
@C:/Users/JoanRamon/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@LICENSE
@README.md
@main.py
@.github/workflows/build.yml

Estado verificado por el orquestador (no volver a investigar):
- LICENSE = texto de licencia no comercial actual (75 líneas, cabecera en línea 1). Sustituir completo.
- README.md: sección EN `## License` líneas ~116–121; sección ES `## Licencia` líneas ~236–241; ambas con el mismo contenido espejo. Secciones `## Download` (líneas 39–50) y `## Descarga` (159–170) terminan con el párrafo del autoactualizador. Créditos (EN ~122, ES ~242) quedan intactos.
- `app/ui/about_dialog.py` NO menciona ninguna licencia — no hay que tocarlo.
- No hay más referencias a la licencia antigua fuera de `.planning/` (verificado con grep).
- `.github/workflows/build.yml` (96 líneas): job `build` con matrix de 3 OS; paso «Prepare assets (macOS)» construye Info.plist por heredoc (termina en línea `PLIST`), luego `mkdir -p release` + `ditto -c -k --keepParent ...` + `sha256sum`. NO existe ningún codesign hoy. Los pasos Windows/Linux no se tocan.
- `app/core/updater.py` verifica el SHA-256 de los assets descargados — no tocar código core; la coherencia se mantiene calculando el sidecar DESPUÉS de firmar.

Convenciones: comentarios nuevos en español salvo avisos legales estándar (boilerplate GPL en inglés); mitades README EN/ES siempre simétricas; nada entra en `app/core/`.

Nota: tracer-first no aplica aquí — no hay arquitectura runtime que probar (todo es metadata/docs/CI); cada tarea entrega valor real e independiente.
</context>

<tasks>

<task type="auto">
  <name>Task 1: LICENSE → GPLv3 canónica + secciones de licencia del README (EN/ES) + cabecera en main.py</name>
  <precondition>Acceso de red a https://www.gnu.org/licenses/gpl-3.0.txt disponible; si la descarga falla o el contenido no pasa los marcadores estructurales, DETENER la tarea (nunca reconstruir el texto de la licencia de memoria).</precondition>
  <read_first>
    LICENSE (completa, 75 líneas) — para sustituirla entera. README.md líneas 116–122 (## License EN) y 236–242 (## Licencia ES). main.py completo (31 líneas) — la cabecera se antepone antes del primer import.
  </read_first>
  <files>LICENSE, README.md, main.py</files>
  <action>
Paso A — Descargar el texto canónico y sustituir LICENSE (per D-01):
1. Con PowerShell: fijar `[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12` y ejecutar `Invoke-WebRequest -Uri 'https://www.gnu.org/licenses/gpl-3.0.txt' -OutFile LICENSE -UseBasicParsing` desde la raíz del repo (fallback si falla: `python -c "import urllib.request; urllib.request.urlretrieve('https://www.gnu.org/licenses/gpl-3.0.txt','LICENSE')"`).
2. Verificar marcadores estructurales del archivo resultante: entre las 2 primeras líneas aparecen «GNU GENERAL PUBLIC LICENSE» y «Version 3, 29 June 2007»; el cuerpo contiene «TERMS AND CONDITIONS» y «How to Apply These Terms». Si algún marcador falta → revertir y detener.
3. NO escribir el texto de la licencia a mano bajo ningún concepto (D-01 explícito).

Paso B — Actualizar las dos secciones de licencia del README de forma espejo (misma posición, mismo orden). En la mitad EN, sustituir la línea en negrita con el identificador SPDX de la licencia no comercial y el párrafo explicativo que la sigue (dejar el heading `## License` y la sección Credits intactas) por estas dos piezas exactas:

**GNU General Public License v3.0 or later** (SPDX: `GPL-3.0-or-later`).

Free software: you can use, study, modify and redistribute it under the terms of the [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html), either version 3 or (at your option) any later version. Contributions are welcome under the same terms. See [LICENSE](LICENSE).

En la mitad ES (heading `## Licencia`), el espejo exacto:

**GNU General Public License v3.0 o posterior** (SPDX: `GPL-3.0-or-later`).

Software libre: puedes usarlo, estudiarlo, modificarlo y redistribuirlo bajo los términos de la [GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.html), en su versión 3 o (a tu elección) cualquier versión posterior. Las contribuciones son bienvenidas bajo la misma licencia. Consulta [LICENSE](LICENSE).

No mencionar licenciación dual/pago (D-01: fuera de alcance). No tocar Créditos ni ninguna otra sección.

Paso C — Anteponer a main.py (antes de `from app import __version__`, seguida de una línea en blanco) esta cabecera exacta de comentario:

# CosechaMedia — herramienta de ingesta verificada para producción audiovisual.
# Copyright (C) 2026 JMW Studio / Joan Ramon Viñas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

Solo main.py lleva cabecera en esta tarea (evitar edición masiva de módulos en un quick; el fichero LICENSE es la referencia normativa).
  </action>
  <verify>
    <automated>$head = (Get-Content LICENSE -TotalCount 2) -join ' '; $lic = Get-Content LICENSE -Raw
"header-ok: $($head -match 'GNU GENERAL PUBLIC LICENSE' -and $head -match 'Version 3, 29 June 2007')"
"terms-ok: $($lic.Contains('TERMS AND CONDITIONS') -and $lic.Contains('How to Apply These Terms'))"
"gpl-readme-count: $((Select-String -Path README.md -Pattern 'GPL-3\.0-or-later').Count)"
$stale = @(git grep -n PolyForm -- ':(exclude).planning'); "stale-refs: $($stale.Count)"
python -m py_compile main.py; if ($LASTEXITCODE -ne 0) { throw 'main.py no compila' } else { 'py-compile: ok' }</automated>
  </verify>
  <done>header-ok: True · terms-ok: True · gpl-readme-count ≥ 2 (una por mitad) · stale-refs: 0 (ninguna referencia a la licencia anterior fuera de `.planning/`; el propio comando del gate contiene el literal, el árbol de trabajo no) · py-compile ok. Las secciones Credits EN/ES siguen intactas y las dos mitades leen como traducción mutua.</done>
</task>

<task type="auto">
  <name>Task 2: Firma ad-hoc de macOS en build.yml</name>
  <read_first>.github/workflows/build.yml — paso «Prepare assets (macOS)»: heredoc del Info.plist termina en la línea `PLIST`, seguido de `mkdir -p release`, `ditto -c -k --keepParent ...` y `sha256sum`.</read_first>
  <files>.github/workflows/build.yml</files>
  <action>
Dentro del paso «Prepare assets (macOS)» (job `build`, matrix macos-latest), insertar EXACTAMENTE dos líneas justo después de la línea `PLIST` (fin del heredoc del Info.plist) y ANTES de `mkdir -p release`:

codesign --force --deep -s - dist/CosechaMedia.app
codesign --display dist/CosechaMedia.app >/dev/null && echo "firma ad-hoc aplicada"

Por qué aquí y así (mantener este razonamiento en el commit si hace falta):
- `-s -` = identidad ad-hoc, gratis, sin cuenta Apple Developer (per D-02). `--force` resella; `--deep` cubre los binarios anidados del bundle de PyInstaller. Evita el falso «dañado» típico de zips de apps sin sellar; la identidad verificable llegaría con Developer ID + notarización (fuera de alcance, se documenta en Task 3).
- El orden es crítico: firmar ANTES de `ditto` (zip) y por tanto ANTES del `sha256sum` del sidecar — `updater.py` verifica ese hash contra el asset publicado, así que el hash debe corresponder al artefacto ya firmado. Firmar después rompería la verificación del autoactualizador.
- NO añadir `--options runtime` (hardened runtime sin entitlements revisados puede romper Qt; decisión D-02 = ad-hoc mínimo). NO tocar los pasos de Windows/Linux, NO añadir secretos, NO añadir ningún otro paso de firma al workflow (la integración real de Windows llega con SignPath cuando se apruebe la solicitud — solo se documenta en Task 3).
  </action>
  <verify>
    <automated>$y = Get-Content .github/workflows/build.yml -Raw
$iPlist = $y.IndexOf('CFBundleIdentifier'); $iSign = $y.IndexOf('codesign --force'); $iDitto = $y.IndexOf('ditto -c -k')
"sign-present: $($iSign -ge 0)"
"order-plist-sign-ditto: $(($iPlist -ge 0) -and ($iPlist -lt $iSign) -and ($iSign -lt $iDitto))"
"sign-line-exact: $($null -ne (Select-String -Path .github/workflows/build.yml -SimpleMatch -Pattern 'codesign --force --deep -s - dist/CosechaMedia.app'))"
"steps-count: $((Select-String -Path .github/workflows/build.yml -Pattern '^\s+- name: ').Count)"</automated>
  </verify>
  <done>sign-present: True · order-plist-sign-ditto: True (la firma queda entre el plist y el zip) · sign-line-exact: True · steps-count: 9 (mismos 9 pasos que hoy — edición confinada al script del paso macOS, sin YAML roto ni pasos espurios).</done>
</task>

<task type="auto">
  <name>Task 3: docs/SIGNING.md (hoja de ruta de firma) + enlaces desde ambas mitades del README</name>
  <read_first>README.md líneas 39–51 (## Download) y 159–171 (## Descarga) — el enlace nuevo va justo tras el párrafo del autoactualizador en cada mitad.</read_first>
  <files>docs/SIGNING.md, README.md</files>
  <action>
Paso A — Crear `docs/SIGNING.md` (directorio `docs/` nuevo) en ESPAÑOL, con estas cinco secciones y contenidos mínimos (redactar con el tono sobrio del repo; comandos y claves literales tal cual se listan):
1. Título «Firma de binarios» + intro breve.
2. «Estado actual»: cada asset de Release publica su sidecar `.sha256`; `app/core/updater.py` verifica el SHA-256 del autoactualizador; macOS lleva firma ad-hoc en CI desde esta tarea (`codesign --force --deep -s -` — sella el bundle y evita falsos «dañados», pero no identifica a un desarrollador verificado ante Gatekeeper); Windows/Linux sin firma de autenticidad (integridad por SHA-256).
3. «macOS — primera apertura (usuarios)»: dos caminos — clic derecho sobre `CosechaMedia.app` → Abrir → confirmar (solo la primera vez); y si aparece «aplicación dañada» (cuarentena extendida del navegador), ejecutar `xattr -dr com.apple.quarantine /ruta/a/CosechaMedia.app` en Terminal. Nota técnica: la firma ad-hoc es gratis pero no verificable; una futura Developer ID + notarización requeriría Apple Developer de pago (descartado ahora, per D-02).
4. «Windows — SignPath Foundation (mantenedores)» (per D-02): explicar el programa (firma gratuita para OSS con licencia OSI-aprobada; GPLv3 cualifica tras el cambio de esta tarea) y los pasos previstos, marcándolos claramente como pendientes de solicitud MANUAL fuera de este repo: aplicar en el programa de la fundación vinculando repositorio y licencia; crear política/proyecto de firma en su panel; configurar los secretos de GitHub `SIGNPATH_API_TOKEN`, `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`; y añadir entonces al job de Windows un paso ENTRE «Prepare assets (Windows)» y «Upload release assets» que firme `release/CosechaMedia-windows-x86_64.exe` con la acción oficial de SignPath consumiendo esos secretos. Incluir un esqueleto YAML ilustrativo COMENTADO (bloque de código cercado con `yaml` y cada línea precedida de `# `) con esas mismas claves: `api-token`, `organization-id`, `project-slug` (valor propuesto `cosechamedia`), `signing-policy-slug`, `artifact-configuration-slug`, `input-artifact-path` — dejando claro con texto que NO debe añadirse al workflow hasta tener credenciales válidas. Mientras tanto la integridad en Windows es el sidecar SHA-256.
5. «Linux»: sin cambios previstos — cada asset ya publica su `.sha256`; no hay paquetes nativos (AppImage/deb/rpm) en el roadmap.

Paso B — Añadir UNA línea por mitad del README, simétrica, justo después del párrafo del autoactualizador:
- Mitad EN (tras la línea que termina en "...installs itself on restart."):

Binaries carry no developer-certificate signature (macOS builds get an ad-hoc signature); see [SIGNING](docs/SIGNING.md) for what that means and how to open the app on macOS the first time.

- Mitad ES (tras la línea que termina en "...se instala sola al reiniciar."):

Los binarios no llevan firma de certificado de desarrollador (las builds de macOS reciben una firma ad-hoc); consulta [SIGNING](docs/SIGNING.md) para saber qué implica y cómo abrir la app en macOS la primera vez.

No tocar ninguna otra parte del README. Mantener el resto del documento de firma libre de promesas: la solicitud a la fundación y el paso real de CI son trabajo futuro (per D-02), no hechos actuales.
  </action>
  <verify>
    <automated>"doc-exists: $(Test-Path docs/SIGNING.md)"
$t = Get-Content README.md -Raw; $i = $t.IndexOf('<a name="espanol">')
"links-en: $(([regex]::Matches($t.Substring(0,$i),'docs/SIGNING\.md')).Count)"
"links-es: $(([regex]::Matches($t.Substring($i),'docs/SIGNING\.md')).Count)"
$s = Get-Content docs/SIGNING.md -Raw
"has-signpath: $($s -match 'SignPath')"
"has-secrets: $($s -match 'SIGNPATH_API_TOKEN')"
"has-xattr: $($s -match 'xattr')"
"has-sha256: $($s -match 'SHA-256|sha256')"
"workflow-clean: $(($null -eq (Select-String -Path .github/workflows/build.yml -SimpleMatch -Pattern 'SIGNPATH_API_TOKEN')))"</automated>
  </verify>
  <done>doc-exists: True · links-en: 1 · links-es: 1 (un enlace por mitad, posiciones espejo) · has-signpath/has-secrets/has-xattr/has-sha256: True (el doc cubre los tres pilares: roadmap Windows, workaround macOS, estado Linux/hash) · workflow-clean: True (los secretos de firma viven SOLO en la documentación; el workflow no cambia respecto a Task 2). <!-- planner-discipline-allow: LIT — 'SignPath'/'SIGNPATH_*' aparecen en este <action> porque el entregable de D-02 ES la documentación de esa integración; el único gate negativo asociado (workflow-clean) examina build.yml, que esta tarea no edita. --></done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| gnu.org → LICENSE | Contenido descargado por red se convierte en el texto legal normativo del repo |
| CI runner → Release assets | Edición del workflow altera qué se publica (firmado + hash) |
| docs/SIGNING.md → usuarios | Instrucciones que un usuario final ejecutará en su máquina |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-IVE-01 | Tampering | Descarga de LICENSE | medium | mitigate | Solo URL canónica sobre TLS + verificación de marcadores estructurales (cabecera, versión, TERMS AND CONDITIONS, How to Apply) antes de aceptar el contenido; prohibido escribir el texto de memoria; halt si falla |
| T-IVE-02 | Tampering | build.yml (paso macOS) | medium | mitigate | Cambio aditivo confinado a un script de paso existente (gate de 9 pasos); orden forzado plist→codesign→ditto→sha256 para que el sidecar publicado corresponda al artefacto firmado y la verificación de `updater.py` siga siendo válida |
| T-IVE-03 | Elevation of Privilege | Instrucciones xattr en docs | low | mitigate | Se documenta el comando mínimo con ruta explícita del bundle y su propósito; práctica estándar para apps OSS sin notarizar; no automatizado, lo ejecuta el usuario en su máquina |
| T-IVE-04 | Repudiation | Promesas de firma en docs | low | mitigate | docs/SIGNING.md marca solicitud SignPath y CI real como pasos pendientes/manuales (per D-02); esqueleto YAML comentado y gate de que el workflow no referencia secretos de firma |
| T-IVE-SC | Tampering | Instalaciones npm/pip/cargo | high | mitigate | No aplica — este plan no instala paquetes (Package Legitimacy Gate N/A); sin dependencias nuevas |
</threat_model>

<verification>
Desde la raíz del repo, en orden: (1) gates del Task 1 — LICENSE con marcadores GPLv3, `gpl-readme-count ≥ 2`, `stale-refs: 0`, py_compile ok; (2) gates del Task 2 — firma presente, orden plist<código firma<ditto correcto, 9 pasos; (3) gates del Task 3 — doc creada, 1 enlace por mitad del README, workflow limpio de secretos de firma. Después `git diff --stat`: solo LICENSE, README.md, main.py, .github/workflows/build.yml y docs/SIGNING.md (nuevo). Revisión visual del diff del README: mitades espejo, Créditos intactos, sin cambios colaterales.
</verification>

<success_criteria>
- LICENSE contiene el texto íntegro y canónico de la GPLv3, obtenido por descarga y validado estructuralmente.
- Ambas mitades del README declaran GPL-3.0-or-later con párrafos espejo y conservan Créditos; cero referencias residuales a la licencia anterior fuera de `.planning/`.
- main.py abre con el aviso de copyright/licencia y compila.
- El job macOS de CI firma ad-hoc el bundle antes de comprimir y hashear; los otros dos jobs y el recuento de pasos no cambian.
- Existe docs/SIGNING.md en español con estado actual, instrucciones de primera apertura en macOS, roadmap SignPath Foundation (con secretos nombrados y esqueleto comentado) y estado Linux, enlazado desde ambas mitades del README.
- Sin cambios en `app/core/` y sin dependencias nuevas.
</success_criteria>

<output>
Create `.planning/quick/260822-ive-cambiar-licencia-a-gpl-3-0-y-preparar-fi/260822-ive-SUMMARY.md` when done
</output>
