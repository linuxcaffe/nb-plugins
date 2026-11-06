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
    # curl stands in for the README download; no network
    (bin_ / 'curl').write_text('#!/bin/sh\nexit 0\n')
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
    assert dev.read_text() == '# dev\n' and 'tw: already installed' in out


def test_a_failed_download_is_named_and_never_fails_the_install(tmp_path):
    _, out, calls = _run(tmp_path, works=False)
    assert len(calls) == 4
    assert f"couldn't install nb-plugin tw (no network?): nb plugins install {BASE}/tw.nb-plugin" in out


def test_without_nb_says_how_to_come_back(tmp_path):
    _, out, calls = _run(tmp_path, with_nb=False)
    assert calls == [] and 'nb not found' in out and 'tw -I nb-plugins' in out
