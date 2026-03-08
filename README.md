# nb-plugins

A collection of community plugins for [nb](https://xwmx.github.io/nb/) — the command-line note-taking, bookmarking, and archiving tool.

---

## Plugins

| Plugin | Command | Description |
|--------|---------|-------------|
| [cal.nb-plugin](#calnb-plugin) | `nb cal` | Date-aware calendar view and range search for date-stamped notes |
| [grep.nb-plugin](#grepnb-plugin) | `nb g` | Context-aware search — see surrounding lines, not just the match |

---

## cal.nb-plugin

> For nb users who keep date-stamped notes (daily journals, logs, diaries) — a calendar view plus date-range list and search.

### What this does

`nb cal` renders a monthly calendar in the terminal. Days that have notes are highlighted in cyan; today is bold yellow. From there you can list or grep all notes within any date range, with an interactive date picker when you need it.

### Install

```bash
nb plugin install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/cal.nb-plugin
```

### Usage

```bash
nb cal                                          # current month calendar
nb cal jan                                      # month by name (current year)
nb cal 2026-01                                  # specific month

nb cal --start 2026-01-01                       # list notes from date to today
nb cal --end   2026-03-01                       # list notes from month start to date
nb cal --start 2026-01-01 --end 2026-03-01      # list notes in range
nb cal --start 2026-01-01 --end 2026-03-01 g <term>  # grep in range

nb cal --start                                  # interactive date picker → sets start
nb cal --end                                    # interactive date picker → sets end
nb cal --start --end                            # pick both dates interactively

nb cal --start mar4 g gbct home:               # natural date, grep term, scoped notebook
```

### Date picker keys

| Key | Action |
|-----|--------|
| `←` / `→` | Previous / next day |
| `↑` / `↓` | Previous / next week |
| `<` / `>` | Previous / next month |
| Enter / Space | Select date |
| `q` / Esc | Cancel |

### Notes

- Notes are matched by filename prefix: files named `YYYYMMDD*.md` (or `.txt`, `.org`) are treated as date-stamped.
- The `--start` / `--end` date arguments accept any format that GNU `date -d` understands: `2026-03-01`, `mar1`, `last monday`, `20260301`, etc.
- Scoping to a notebook: append `notebook:` as the last argument.

---

## grep.nb-plugin

> Addresses the longstanding limitation of `nb search` showing only one matched line per result.
> See: [nb issue #437](https://github.com/xwmx/nb/issues/437)

### The problem

`nb search` is great for finding which notes match — but it shows only a single line per result. When your notes have structure (headings, metadata, annotations), one line is rarely enough context to know *why* a note matched or what surrounds the match.

### What this does

`nb g` searches your notes like `grep -C`: results grouped by note, with surrounding context lines, match term highlighted. Works across all notebooks or scoped to one.

```
[home:12] 2026-03-01.md
────────────────────────────────────────────────
  4-
  5:## ✅ Fix the login bug                        ← match (highlighted)
  6-> #project/work/web #bug
  7-
```

### Install

```bash
nb plugin install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/grep.nb-plugin
```

### Usage

```bash
nb g <pattern>                  # search all notebooks (default: 1 line context)
nb g <pattern> tasks:           # scope to one notebook
nb g -C 3 <pattern>             # 3 lines of context around each match
nb g -A 2 -B 0 <pattern>        # 2 lines after, none before
nb g -I <pattern>               # case-insensitive
nb g -l <pattern>               # list matching note titles only
NB_GREP_CONTEXT=3 nb g <pattern> # set default context via env var
```

Both `nb g` (short alias) and `nb nb_grep` (full name) work.

### Options

| Flag | Description |
|------|-------------|
| `-C <n>` | Lines of context around each match (default: 1) |
| `-A <n>` | Lines after each match |
| `-B <n>` | Lines before each match |
| `-I` | Case-insensitive search (`-i` is reserved by nb) |
| `-l` | List matching note titles only |

---

## Related

**[tw2nb](https://github.com/linuxcaffe/tw2nb)** — archives Taskwarrior task events (completed, deleted, annotated) to nb as structured todo notes and a running daily journal. Includes `nb info`, a companion plugin that shows Taskwarrior task details for any uuid referenced in an nb note.

---

## Contributing

New plugins welcome. Each plugin should:

- Be a single self-contained `.nb-plugin` file
- Follow nb's plugin conventions (`_subcommands add`, leading-underscore function)
- Include a description block (`_subcommands describe`)
- Work without external dependencies where possible

---

## License

MIT
