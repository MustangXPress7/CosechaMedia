---
quick_id: 260904-dwm
slug: fix-browse-session-src-unpacking-error-v
title: Fix _browse_session_src unpacking error
---

# Quick Task: Fix _browse_session_src unpacking error

## Why

`_browse_session_src` (app/ui/main_window.py:3256) crashes with
`ValueError: not enough values to unpack (expected 2, got 1)` when the user
chooses a source in the session's "Examinar origen" picker.

Root cause: `_pick_source_entry()` returns a **list of source dicts** (or
`None`), but `_browse_session_src` unpacks it as a single 2-tuple:
`kind, value = choice`. The dialog can also return sources of kinds
`device`, `usb`, `ftp_new`, `wifi` that the current code does not handle.

## What

Rewrite `_browse_session_src` to iterate the list of selected source dicts and
dispatch each to a session-binding handler:

- `folder` / `usb` -> `self._assign_session_folder(self.current_session_id, value)`
- `browse` -> prompt with `QFileDialog.getExistingDirectory`, then `_assign_session_folder`
- `sender` -> `self._bind_wifi_sender(value, session_id=self.current_session_id)`
- `ftp_profile` / `ftp_new` -> `_pick_ftp_source(...)`
- `device` -> `_register_device_source_from_picker(...)`
- `wifi` -> `self._pick_wifi_source()`

Mirror `_apply_source_choice` (app/ui/main_window.py:3459) but keep the
session-bound variants for folder/sender (since this flow binds to the current
session, unlike the main source list).

## Tasks

1. Rewrite `_browse_session_src` to iterate the list of dicts and dispatch
   each source with session binding; retain the `current_session_id is None`
   guard. Also handle `ftp_new`, `device`, `usb`, `wifi` kinds like
   `_apply_source_choice`.
2. Add/extend a test verifying `_browse_session_src` no longer crashes and
   dispatches a folder source to `_assign_session_folder`.
3. Run the full test suite; confirm all pass.
