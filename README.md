# nb-plugins

A collection of community plugins for [nb](https://xwmx.github.io/nb/) — the command-line note-taking, bookmarking, and archiving tool.

---

## Plugins

| Plugin | Command | Description |
|--------|---------|-------------|
| [cal.nb-plugin](#calnb-plugin) | `nb cal` | Date-aware calendar view and range search for date-stamped notes |
| [grep.nb-plugin](#grepnb-plugin) | `nb g` | Context-aware search — see surrounding lines, not just the match |
| [send.nb-plugin](#sendnb-plugin) | `nb send` | Send a file to an nb notebook via a GUI dialog (zenity); desktop file manager integration |
| [tw.nb-plugin](#twnb-plugin) | `nb tw` | Pair Taskwarrior tasks with nb notes: find, create and link a task's note |

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

### Regex examples

The plugin uses ERE (extended regular expressions) by default — the same dialect as `grep -E` and `rg`. Use `-F` to disable regex and search for a literal string.

```bash
nb g "meeting|standup"              # OR: notes matching either word
nb g "(TODO|FIXME|HACK)"            # any of three keywords
nb g "^#+ "                         # lines that are markdown headings
nb g "\+\w+"                        # taskwarrior-style tags (+word)
nb g "[0-9]{4}-[0-9]{2}-[0-9]{2}"  # ISO date pattern
nb g "https?://"                    # any URL
nb g -C 3 "def \w+\("               # function definitions, 3 lines context
nb g -F "[project.home]"            # -F: literal string, brackets not special
```

### Options

| Flag | Description |
|------|-------------|
| `-C <n>` | Lines of context around each match (default: 1) |
| `-A <n>` | Lines after each match |
| `-B <n>` | Lines before each match |
| `-I` | Case-sensitive search (default is case-insensitive) |
| `-w` | Whole-word matches only |
| `-F` | Literal string, no regex (useful for `[tags]`, URLs, etc.) — disables ERE |
| `-v` | List notes NOT containing the pattern (implies `-l`) |
| `-e <pattern>` | Extra pattern; repeatable, OR logic |
| `-l` | List matching note titles only |

---

## send.nb-plugin

> For desktop Linux users — import any file from your file manager (Caja, Nemo, or terminal) directly into an nb notebook with a two-step GUI dialog.

### What this does

`nb send` opens a two-step zenity dialog: first choose a notebook, then choose a folder and optionally rename the file. The actual import — file copy, `.index` entry, git commit — is handled by nb's own `import copy` command.

Calling convention is auto-detected:
- **Nemo action**: called with a `file:///` URI argument
- **Caja Scripts menu**: reads `$CAJA_SCRIPT_SELECTED_FILE_PATHS`
- **Terminal**: plain file path argument

Files with unrecognised MIME types (executables, unknown binaries) trigger a warning with the option to cancel or proceed. The original file extension is always preserved — the rename field accepts only the stem.

### Install

```bash
nb plugin install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/send.nb-plugin
```

For Caja / Nemo file manager integration, see [nb-desktop](https://github.com/linuxcaffe/nb-desktop).

### Usage

```bash
nb send ~/Pictures/photo.jpg          # terminal — plain path
nb send file:///home/djp/doc.pdf      # terminal — URI (as passed by Nemo)
nb send                               # Caja script — reads env var automatically
```

All activity is logged to `/tmp/nb-send.log` — useful for debugging file manager invocations where there is no visible terminal.

---

## tw.nb-plugin

> For Taskwarrior users who keep notes in nb — every task can have a note, and every note knows its task.

### What this does

`nb tw` links a Taskwarrior task and an nb note in both directions. The task carries an
annotation `nb: <notebook>:<path>` (the authoritative link); the note carries `tw: <uuid>` in its
frontmatter (a list when one note serves several tasks).

- `nb tw note 42` opens task 42's note: the one its `nb:` annotation names, else a note whose
  frontmatter names the task (and the lost annotation is restored), else a new one.
- **Ask for a note from any client:** annotate the task with a bare `nb:` (a note in `tasknotes:`)
  or `nb: <notebook>:` (a note in that notebook; note the trailing colon). `nb tw note` honours
  the request: it makes or finds the note, adds the real link and removes the request; tw2nb's
  on-exit hook runs it as soon as the annotation is saved. An unknown notebook leaves the
  request in place and says why. `nb: djp` without the colon is still a note named `djp`.
- New notes are `<slug>-<uuid8>.note.md` with `type: task`, in the `tasknotes` notebook, filed in
  a folder per project (`project:kitchen.reno` → `tasknotes:kitchen/`).
- `nb tw link` makes any existing note a task's note, without renaming it or changing its type.
- `nb tw status 42` writes the task's status into its note (`tw_status`, and `tw_end` once it's
  completed or deleted); reopening reverses it. Meant for hooks: it follows annotations only and
  never scans. A note serving several tasks gets no single status.
- The note's frontmatter carries the task, so nb can search and sort by it: `title` (the
  description), `project`, `due` (a local date), `priority` and `tags`, written when the note is
  made and on every `nb tw status`. The `tw_` keys (`tw_project`, `tw_due`, `tw_priority`,
  `tw_tags`) record the task's own values, so the note's own win: a `project:` you set in the
  note stays (the task's is still in `tw_project`), and a tag added in nb stays beside the
  task's. The status is `tw_status` only, since `status:` means other things in nb-web. One-way:
  editing these in nb doesn't change the task.
- `nb tw info` shows `task info` for every task a note is about (also the uuid8s tw2nb writes).
- `nb tw restore 42` brings back a note deleted in nb, from its notebook's git history, at the path
  the task's `nb:` link names. `nb tw unlink 42` drops the link instead; a note that still exists
  becomes a plain note (`type: note`, frontmatter kept, `tw:` renamed `tw_was:`, so it's never
  adopted again). A link to a notebook that isn't on this station is left alone by both.
- Locks are respected the way nb-web does: a `.nb-lock` in the folder chain or a note's own
  `lock: yes` means nothing is written there.

**Recurring tasks** (native `recur:` or [recurrence-overhaul](https://github.com/linuxcaffe/tw-recurrence_overhaul-hook)'s
`r:`): one note for the whole series (the default), or `--each`, a folder holding one note per
occurrence. The choice is the template's own `nb:` annotation (a note, or a folder ending in `/`),
which every occurrence inherits. When an occurrence of a series is done or deleted,
`nb tw status` adds `- 2026-11-01 ✓ done (1a2b3c4d)` under the note's `## Occurrences`.

Notes are written directly and committed with nb's own `index reconcile --commit`. Each run takes
the same lock nb-web uses for nb (`$NB_DIR/.logs/nb-web-nb.lock`); a caller that already holds it
sets `NB_LOCK_HELD=1`.

### Install

```bash
nb notebooks add tasknotes
nb plugin install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/tw.nb-plugin
```

Requires Taskwarrior 2.6 and Python 3. It replaces tw2nb's older `tw.nb-plugin` (`nb info` still
works, as an alias of `nb tw info`).

### Usage

```bash
nb tw note 42                                   # find or create task 42's note
nb tw note 42 --notebook cine                   # create it in cine: instead
nb tw add "Grout the backsplash" project:kitchen due:fri +reno
nb tw link cine:edl-definition.md 42            # an existing note becomes task 42's note
nb tw info tasknotes:kitchen/grout-the-backsplash-1a2b3c4d.note.md
nb tw add "Water the plants" recur:weekly due:sat            # one note for the series
nb tw add "Stretch" recur:daily due:today --each              # a note per occurrence
nb tw status 42                                 # after task 42 done/delete/modify
nb tw note 42 --porcelain                       # uuid/selector/path/created, for scripts
```

`nb tw` needs a command (`note`, `add`, `link`, `status`, `info`, `restore`, `unlink`); if you also have a notebook
named `tw`, bare `nb tw` lists that notebook instead. `nb help tw` shows nothing, as for any nb plugin: this README is the help.

`nb tw add` takes the description first, then attributes only (`name:value`, `+tag`, `-tag`):
never a command word and never an `rc.` override.

### Settings

Taskwarrior config entries (put them in your `.taskrc` or an included file):

```ini
tw.notebook        = tasknotes  # default notebook for new notes
tw.notebook.film   = cine   # new notes for project film (and film.*) go to cine:
tw.folder_depth    = 1      # 0: no folders, 1: tasknotes:kitchen/, 2: tasknotes:kitchen/reno/
```

### Templates

If `<notebook>/.templates/task.md` exists, new notes start from it. `{{field}}` and
`{{field|default}}` are filled from the task: `description`, `project`, `uuid`, `uuid8`, `id`,
`due`, `scheduled`, `priority`, `tags`, `status`, `date`. Without a template a note starts with
`# <description>`.

### Tests

```bash
python3 -m pytest -q tests     # throwaway nb + Taskwarrior; never touches ~/.nb or ~/.task
```

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
