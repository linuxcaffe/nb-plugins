"""A task note deleted in nb (djp 2026-11-04: "I just used nb Delete on a few test notes"): the
task kept an `nb:` link to nothing, and nothing said so. Two ways back, both by the task:

- `nb tw restore <task>` brings the note back from its notebook's git history, at the path the
  link names (nb commits every delete, so nothing is lost).
- `nb tw unlink <task>` drops the link. A note that still exists becomes a plain note (djp:
  "changing to type: note ... you could leave the fm"): `type: note`, its frontmatter kept, `tw:`
  renamed `tw_was:` so the plugin never adopts it again by its uuid.

A link that merely doesn't resolve here (its note on another station) is never "deleted": only
a file git shows deleted in a notebook here counts.
"""
import subprocess

import yaml


def fm(path):
    text = path.read_text()
    return yaml.safe_load(text[4:text.index('\n---', 3)]) or {}


def made(env, desc):
    uuid = env.add_task('--', desc)
    p = env.porcelain('note', uuid)
    return uuid, p, env.nb_dir / p['selector'].replace(':', '/', 1)


def git_delete(env, path):
    root = env.nb_dir / 'tasknotes'
    subprocess.run(['git', '-C', str(root), 'rm', '-q', str(path.relative_to(root))], check=True)
    subprocess.run(['git', '-C', str(root), 'commit', '-qm', '[nb] Delete: x'], check=True)


def test_restore_brings_a_deleted_note_back_from_git(env):
    uuid, p, path = made(env, 'Order the tiles')
    path.write_text(path.read_text() + '\nKim Lee will deliver.\n')
    subprocess.run(['git', '-C', str(env.nb_dir / 'tasknotes'), 'commit', '-qam', 'edit'], check=True)
    git_delete(env, path)
    assert not path.exists()
    r = env.nb('tw', 'restore', uuid)
    assert path.exists() and 'Kim Lee will deliver.' in path.read_text()
    assert fm(path)['tw'] == uuid
    assert env.annotations(uuid) == [f'nb: {p["selector"]}']
    assert p['selector'] in r.stdout
    assert not subprocess.run(['git', '-C', str(env.nb_dir / 'tasknotes'), 'status', '--porcelain'],
                              capture_output=True, text=True).stdout.strip()


def test_restore_says_so_when_there_is_nothing_deleted(env):
    uuid, p, path = made(env, 'Still here')
    r = env.nb('tw', 'restore', uuid, check=False)
    assert r.returncode != 0 and 'nothing to restore' in r.stderr


def test_unlink_a_deleted_note_drops_the_link(env):
    uuid, p, path = made(env, 'Call Jones')
    git_delete(env, path)
    env.nb('tw', 'unlink', uuid)
    assert env.annotations(uuid) == []


def test_unlink_a_note_that_exists_keeps_it_as_a_plain_note(env):
    uuid, p, path = made(env, 'Grout the backsplash')
    env.nb('tw', 'unlink', uuid)
    assert env.annotations(uuid) == []
    meta = fm(path)
    assert meta['type'] == 'note' and meta['tw_was'] == uuid and 'tw' not in meta
    assert meta['tw_status'] == 'pending'                     # the rest stays, as history
    r = env.porcelain('note', uuid)                           # never adopted again by its uuid
    assert r['created'] == 'yes' and r['path'] != str(path)
    assert fm(path)['type'] == 'note'                         # and the plain note is untouched


def test_unlink_keeps_a_link_that_only_does_not_resolve_here(env):
    uuid = env.add_task('--', 'On the phone')
    env.task(uuid, 'annotate', '--', 'nb: mobile:elsewhere.md')   # no mobile notebook here
    env.nb('tw', 'unlink', uuid)
    assert env.annotations(uuid) == ['nb: mobile:elsewhere.md']
