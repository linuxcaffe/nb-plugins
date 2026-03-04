# nb-plugins

A collection of community plugins for [nb](https://xwmx.github.io/nb/) — the command-line note-taking, bookmarking, and archiving tool.

---

## Plugins

| Plugin | Command | Description |
|--------|---------|-------------|
| [grep.nb-plugin](#grepnb-plugin) | `nb g` | Context-aware search — see surrounding lines, not just the match |

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
nb g -i <pattern>               # case-insensitive
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
| `-i` | Case-insensitive search |
| `-l` | List matching note titles only |

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
