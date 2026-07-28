# Reference prototype

Working, verified code from the exploration phase. **Not the final structure.**

- Comments and identifiers are in Portuguese — the final repo uses English for
  code and Portuguese only for user-facing strings (see `CLAUDE.md` §2).
- The layout is flat; the target layout is `core/` + `data/` + `ui/`.

What is worth porting rather than rewriting:

| File                | Status |
|---------------------|---|
| `/REF/sshconfig.py` | Parser and writer, validated by 10 passing tests. Split into `core/models.py`, `core/parser.py`, `core/writer.py`, `core/store.py`. |
| `/REF/keywords.py`       | The 47-entry catalog with pt-BR descriptions. Move to `data/keywords.py`, translate comments only. |
| `/REF/tester.py`         | The interpretation table. Split `interpret()` out as a pure function. |
| `/REF/keys.py`           | Key discovery and generation. |
| `/REF/guide.py`          | pt-BR help text. Move to `data/guide.py` as-is. |
| `/REF/window.py`         | Every widget and behaviour, in one file. Split into `ui/window.py`, `ui/sidebar.py`, `ui/editor.py`, `ui/rows.py`, `ui/dialogs.py`. |
| `/REF/test_sshconfig.py` | 10 passing assertions. Convert to pytest with fixtures. |

Verified: `python3 tests/test_sshconfig.py` → 10/10 green.
Imports checked against GTK 4.14.5 and libadwaita 1.5.0.