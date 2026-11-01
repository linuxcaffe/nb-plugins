"""Throwaway nb + Taskwarrior for plugin tests: own HOME, NB_DIR, TASKRC and task data.

Nothing here touches the real ~/.nb or ~/.task. The plugin under test is symlinked into the
temp NB_DIR's .plugins/, so a test always runs the working copy.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\([A-Za-z0-9]')


class Env:
    def __init__(self, root: Path):
        self.root = root
        self.home = root / 'home'
        self.nb_dir = self.home / '.nb'
        self.task_dir = root / 'task'
        self.taskrc = self.home / '.taskrc'
        self.env = {
            'PATH': os.environ['PATH'],
            'HOME': str(self.home),
            'NB_DIR': str(self.nb_dir),
            'NBRC_PATH': str(self.home / '.nbrc'),
            'TASKRC': str(self.taskrc),
            'EDITOR': 'true',
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'GIT_AUTHOR_DATE': '', 'GIT_COMMITTER_DATE': '',
        }
        for k in ('GIT_AUTHOR_DATE', 'GIT_COMMITTER_DATE'):
            del self.env[k]

    def run(self, *args, check=True, env=None, timeout=60):
        r = subprocess.run(list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           env={**self.env, **(env or {})}, timeout=timeout)
        if check and r.returncode != 0:
            raise AssertionError(f'{args} exited {r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}')
        r.stdout = ANSI.sub('', r.stdout)
        r.stderr = ANSI.sub('', r.stderr)
        return r

    def nb(self, *args, **kw):
        return self.run('nb', *args, **kw)

    def task(self, *args, **kw):
        return self.run('task', 'rc.hooks=off', *args, **kw)

    def add_task(self, *words):
        """Add a task; return its uuid."""
        out = self.task('rc.verbose=new-uuid', 'add', *words).stdout
        return re.search(r'Created task ([0-9a-f-]{36})', out).group(1)

    def export(self, uuid):
        return json.loads(self.task(uuid, 'export').stdout)[0]

    def annotations(self, uuid):
        return [a['description'] for a in self.export(uuid).get('annotations', [])]

    def porcelain(self, *args, **kw):
        """Run `nb tw … --porcelain`, return its key: value block as a dict."""
        out = self.nb('tw', *args, '--porcelain', **kw).stdout
        return dict(line.split(': ', 1) for line in out.splitlines() if ': ' in line)

    def notebook(self, name):
        if not (self.nb_dir / name).is_dir():
            self.nb('notebooks', 'add', name)
        return self.nb_dir / name

    def git_clean(self, notebook):
        return self.run('git', '-C', str(self.nb_dir / notebook), 'status', '--porcelain').stdout == ''

    def set_rc(self, key, value):
        with open(self.taskrc, 'a') as f:
            f.write(f'{key}={value}\n')


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    e.home.mkdir()
    e.task_dir.mkdir()
    e.taskrc.write_text(f'data.location={e.task_dir}\nconfirmation=off\n')
    e.run('git', 'config', '--global', 'user.name', 'Pat Smith')
    e.run('git', 'config', '--global', 'user.email', 'pat@example.com')
    e.nb('notebooks', '--names')          # first run: creates `home` (and prints a splash)
    e.notebook('tw')
    (e.nb_dir / '.plugins').mkdir(exist_ok=True)
    (e.nb_dir / '.plugins' / 'tw.nb-plugin').symlink_to(REPO / 'tw.nb-plugin')
    return e
