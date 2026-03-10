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

> For nb users who keep date-stamped notes (daily journals, logs, diaries) — an interactive calendar browser plus date-range list and search.

### What this does

`nb cal` opens an interactive two-panel calendar browser. The left panel shows the current month; days with notes are highlighted in cyan, today in bold yellow, the cursor day in reverse video. The right panel shows the note titles (with nb IDs) for whichever day the cursor is on, updating live as you navigate. Press Enter to select a day and list its notes; `q` to quit.

For range queries, `--start` and `--end` accept any date format — or omit the date to open an interactive date picker.

### Install

```bash
nb plugin install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/cal.nb-plugin
```

### Usage

```bash
# Interactive calendar browser
nb cal                                               # current month
nb cal jan                                           # month by name (current year)
nb cal 2026-01                                       # specific month (YYYY-MM)

# Range listing — shows [notebook:id], date, title
nb cal --start 2026-01-01                            # from date to today
nb cal --end   2026-03-01                            # from start of month to date
nb cal --start 2026-01-01 --end 2026-03-01           # explicit range

# Range grep
nb cal --start 2026-01-01 --end 2026-03-01 g <term> # search in range (case-insensitive)
nb cal --start mar1 g -C 3 meeting                  # 3 lines of context
nb cal --start mar1 g -I Meeting                    # case-sensitive

# Interactive date pickers (omit date after --start / --end)
nb cal --start                                       # pick start date interactively
nb cal --start --end                                 # pick both dates

# Notebook scoping (append notebook: as last arg)
nb cal --start mar4 g gbct home:
```

### Navigation keys (browser and date picker)

| Key | Action |
|-----|--------|
| `←` / `→` | Previous / next day |
| `↑` / `↓` | Previous / next week |
| `<` / `>` | Previous / next month |
| Enter | Select — lists notes for that day |
| `q` / Esc | Quit |

### Output format

```
[home:42]  2026-03-08  Daily Journal
[home:43]  2026-03-05  Meeting notes
```

IDs match nb's own numbering — use them directly with `nb edit home:42`, `nb show home:42`, etc.

### Notes

- Notes are matched by filename prefix: `YYYYMMDD*.md` (or `.txt`, `.org`).
- Date arguments accept anything GNU `date -d` understands: `2026-03-01`, `mar1`, `last monday`, `20260301`, etc.
- `g` grep is case-insensitive by default; `g -I` for case-sensitive. All standard grep flags (`-C`, `-A`, `-B`) are supported.

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
nb g <pattern>                      # search all notebooks (default: 1 line context, case-insensitive)
nb g <pattern> tasks:               # scope to one notebook
nb g -C 3 <pattern>                 # 3 lines of context around each match
nb g -A 2 -B 0 <pattern>            # 2 lines after, none before
nb g -I <pattern>                   # case-sensitive search
nb g -w <pattern>                   # whole-word matches only
nb g -F "[project.home]"            # literal string, no regex
nb g -v <pattern> tasks:            # list notes NOT containing pattern
nb g -e foo -e bar                  # OR: notes containing either pattern
nb g -l <pattern>                   # list matching note titles only
NB_GREP_CONTEXT=3 nb g <pattern>    # set default context via env var
```

Both `nb g` (short alias) and `nb nb_grep` (full name) work.

### Options

| Flag | Description |
|------|-------------|
| `-C <n>` | Lines of context around each match (default: 1) |
| `-A <n>` | Lines after each match |
| `-B <n>` | Lines before each match |
| `-I` | Case-sensitive search (default is case-insensitive) |
| `-w` | Whole-word matches only |
| `-F` | Literal string, no regex (useful for `[tags]`, URLs, etc.) |
| `-v` | List notes NOT containing the pattern (implies `-l`) |
| `-e <pattern>` | Extra pattern; repeatable, OR logic |
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
