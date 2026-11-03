"""An `nb:` request (tw-nb-interop M7 (b), djp 2026-11-02): annotate a task with a bare `nb:`
(a note in tasknotes:) or `nb: <notebook>:` (a note there), from any client, and nobody names
anything. `nb tw note <uuid>` honours it: makes (or finds) the note, adds the real link and
removes the request. tw2nb's on-exit hook runs it when a task carries a request. A request is
an empty path ending in a colon; `nb: djp` (no colon) stays a note named djp (M1's bare form).
"""
import yaml


def fm(path):
    text = path.read_text()
    return yaml.safe_load(text[4:text.index('\n---', 3)]) or {}


def test_a_bare_request_makes_a_tasknote_and_becomes_its_link(env):
    uuid = env.add_task('--', 'Order the tiles')
    env.task(uuid, 'annotate', '--', 'nb:')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'yes'
    assert p['selector'] == f'tasknotes:order-the-tiles-{uuid[:8]}.note.md'
    anns = env.annotations(uuid)
    assert 'nb:' not in anns
    assert anns.count(f'nb: {p["selector"]}') == 1


def test_a_request_names_its_notebook(env):
    env.notebook('acme')
    uuid = env.add_task('project:kitchen', '--', 'Call Jones about the grout')
    env.task(uuid, 'annotate', '--', 'nb: acme:')
    p = env.porcelain('note', uuid)
    assert p['selector'].startswith('acme:'), p['selector']
    path = env.nb_dir / 'acme' / p['selector'].split(':', 1)[1]
    assert fm(path)['tw'] == uuid
    anns = env.annotations(uuid)
    assert 'nb: acme:' not in anns
    assert f'nb: {p["selector"]}' in anns


def test_a_request_for_a_notebook_that_does_not_exist_stays_and_says_why(env):
    uuid = env.add_task('--', 'Nowhere to go')
    env.task(uuid, 'annotate', '--', 'nb: nosuch:')
    r = env.nb('tw', 'note', uuid, check=False)
    assert r.returncode != 0
    assert 'nosuch' in r.stderr
    assert env.annotations(uuid) == ['nb: nosuch:']
    assert not list((env.nb_dir / 'tasknotes').glob('*.md'))


def test_a_request_on_a_task_that_has_a_note_just_goes(env):
    uuid = env.add_task('--', 'Already noted')
    first = env.porcelain('note', uuid)
    env.task(uuid, 'annotate', '--', 'nb:')
    again = env.porcelain('note', uuid)
    assert again['created'] == 'no'
    assert again['path'] == first['path']
    assert env.annotations(uuid) == [f'nb: {first["selector"]}']


def test_a_name_without_the_colon_is_a_note_not_a_request(env):
    uuid = env.add_task('--', 'Keep my name')
    env.task(uuid, 'annotate', '--', 'nb: djp')
    env.nb('tw', 'note', uuid, check=False)
    assert 'nb: djp' in env.annotations(uuid)


def test_status_ignores_a_request(env):
    """nb tw status runs on every change (tw2nb's on-exit); a request is not a link to mirror."""
    uuid = env.add_task('--', 'Not yet')
    env.task(uuid, 'annotate', '--', 'nb: acme:')
    r = env.nb('tw', 'status', uuid, check=False)
    assert r.returncode == 0, r.stderr
    assert env.annotations(uuid) == ['nb: acme:']
