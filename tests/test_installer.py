"""nb-plugins 1.3.0: `tw -I nb-plugins` installs the plugins into nb (djp 2026-11-05: "any part of the
program that needs an nb-plugin should install it"). Before, it installed only the README.
A fake nb records what it's asked; nothing touches the real ~/.nb."""
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = 'https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main'


def _run(tmp_path, with_nb=True, works=True):
    home = tmp_path / 'home'
    home.mkdir(exist_ok=True)
    bin_ = tmp_path / 'bin'
    bin_.mkdir(exist_ok=True)
    log = tmp_path / 'nb-calls'
    if with_nb:
        make = ('mkdir -p "$HOME/.nb/.plugins" && touch "$HOME/.nb/.plugins/$(basename "$3")"'
                if works else 'exit 1')
        (bin_ / 'nb').write_text(f'#!/bin/sh\necho "$*" >> "{log}"\n'
                                 f'if [ "$1 $2" = "plugins install" ]; then {make}; fi\n')
        (bin_ / 'nb').chmod(0o755)
    # curl stands in for the network: a file in remote/ is served by its name, else it fails
    remote = tmp_path / 'remote'
    remote.mkdir(exist_ok=True)
    (bin_ / 'curl').write_text('#!/bin/sh\n'
                               'out=""; url=""\n'
                               'while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; -*) shift;; *) url="$1"; shift;; esac; done\n'
                               f'src="{remote}/$(basename "$url")"\n'
                               '[ -f "$src" ] || exit 22\n'
                               '[ -n "$out" ] && cp "$src" "$out" || cat "$src"\n')
    (bin_ / 'curl').chmod(0o755)
    path = ':'.join([str(bin_)] + [d for d in ('/usr/bin', '/bin') if not (Path(d) / 'nb').exists()])
    r = subprocess.run(['bash', str(REPO / 'nb-plugins.install'), 'install'], capture_output=True,
                       text=True, timeout=60, env={'PATH': path, 'HOME': str(home)})
    assert r.returncode == 0, r.stdout + r.stderr
    calls = log.read_text().splitlines() if log.exists() else []
    return home, r.stdout, calls


def test_installs_every_plugin_into_nb(tmp_path):
    home, out, calls = _run(tmp_path)
    assert calls == [f'plugins install {BASE}/{p}.nb-plugin' for p in ('cal', 'grep', 'send', 'tw')]
    for p in ('cal', 'grep', 'send', 'tw'):
        assert (home / '.nb' / '.plugins' / f'{p}.nb-plugin').exists()


def test_keeps_a_plugin_already_there(tmp_path):
    plugins = tmp_path / 'home' / '.nb' / '.plugins'
    plugins.mkdir(parents=True)
    dev = tmp_path / 'dev-tw.nb-plugin'
    dev.write_text('# dev\n')
    (plugins / 'tw.nb-plugin').symlink_to(dev)
    _, out, calls = _run(tmp_path)
    assert not any(c.endswith('/tw.nb-plugin') for c in calls)
    assert dev.read_text() == '# dev\n' and 'tw: a link, left as it is' in out


def test_a_failed_download_is_named_and_never_fails_the_install(tmp_path):
    _, out, calls = _run(tmp_path, works=False)
    assert len(calls) == 4
    assert f"couldn't install nb-plugin tw (no network?): nb plugins install {BASE}/tw.nb-plugin" in out


def test_without_nb_says_how_to_come_back(tmp_path):
    _, out, calls = _run(tmp_path, with_nb=False)
    assert calls == [] and 'nb not found' in out and 'tw -I nb-plugins' in out



# ── 1.3.1: a copy that differs from the repo's is updated (djp 2026-11-05: the phone's tw.nb-plugin
# was older than yoga's, and "already installed" never changed it) ─────────────────────────────

def _remote(tmp_path, **plugins):
    r = tmp_path / 'remote'
    r.mkdir(exist_ok=True)
    (r / 'README.md').write_text('# readme\n')
    for name, text in plugins.items():
        (r / f'{name}.nb-plugin').write_text(text)


def _have(tmp_path, name, text):
    d = tmp_path / 'home' / '.nb' / '.plugins'
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{name}.nb-plugin').write_text(text)
    (d / f'{name}.nb-plugin').chmod(0o755)
    return d / f'{name}.nb-plugin'


def test_an_old_copy_is_updated(tmp_path):
    _remote(tmp_path, tw='# tw new\n', cal='# cal\n', grep='# grep\n', send='# send\n')
    old = _have(tmp_path, 'tw', '# tw old\n')
    _, out, calls = _run(tmp_path)
    assert old.read_text() == '# tw new\n' and 'Updated nb-plugin tw' in out
    assert old.stat().st_mode & 0o111                                # still runnable
    assert not any(c.endswith('/tw.nb-plugin') for c in calls)        # by the installer, not nb


def test_a_current_copy_is_left_alone(tmp_path):
    _remote(tmp_path, tw='# tw\n')
    cur = _have(tmp_path, 'tw', '# tw\n')
    _, out, _ = _run(tmp_path)
    assert cur.read_text() == '# tw\n' and 'nb-plugin tw: up to date' in out


def test_a_link_is_never_touched(tmp_path):
    _remote(tmp_path, tw='# tw new\n')
    d = tmp_path / 'home' / '.nb' / '.plugins'
    d.mkdir(parents=True)
    dev = tmp_path / 'dev-tw.nb-plugin'
    dev.write_text('# dev\n')
    (d / 'tw.nb-plugin').symlink_to(dev)
    _, out, _ = _run(tmp_path)
    assert dev.read_text() == '# dev\n' and (d / 'tw.nb-plugin').is_symlink()
    assert 'nb-plugin tw: a link, left as it is' in out


def test_no_network_keeps_the_copy_and_says_so(tmp_path):
    old = _have(tmp_path, 'tw', '# tw old\n')                        # remote/ has no tw
    _, out, _ = _run(tmp_path)
    assert old.read_text() == '# tw old\n' and "couldn't check nb-plugin tw for an update" in out
