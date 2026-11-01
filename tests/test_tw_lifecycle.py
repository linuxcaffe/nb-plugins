"""tw.nb-plugin M2: `nb tw status` (status mirroring, both ways), locks on every write, and
recurring tasks (series vs each, native `parent:` and recurrence-overhaul `rtemplate`)."""
import re
from datetime import date

import pytest
import yaml


def fm(path):
    text = path.read_text()
    assert text.startswith('---\n'), text[:80]
    return yaml.safe_load(text[4:text.index('\n---', 3)]) or {}


def noted(env, *words):
    """A task with a note; returns (uuid, note path)."""
    uuid = env.add_task('--', *words)
    from pathlib import Path
    return uuid, Path(env.porcelain('note', uuid)['path'])


# ── nb tw status ─────────────────────────────────────────────────────────────

def test_done_mirrors_completed_and_end_date(env):
    uuid, path = noted(env, 'Finish me')
    env.task(uuid, 'done')
    env.nb('tw', 'status', uuid)
    meta = fm(path)
    assert meta['tw_status'] == 'completed'
    assert str(meta['tw_end']) == date.today().isoformat()
    assert env.git_clean('tasknotes')


def test_reopen_flips_back_and_drops_end(env):
    uuid, path = noted(env, 'Reopen me')
    env.task(uuid, 'done')
    env.nb('tw', 'status', uuid)
    env.task(uuid, 'modify', 'status:pending')
    env.nb('tw', 'status', uuid)
    meta = fm(path)
    assert meta['tw_status'] == 'pending'
    assert 'tw_end' not in meta


def test_delete_and_wait(env):
    a, pa = noted(env, 'Delete me')
    env.task(a, 'delete')
    env.nb('tw', 'status', a)
    assert fm(pa)['tw_status'] == 'deleted'
    b, pb = noted(env, 'Wait for me')
    env.task(b, 'modify', 'wait:tomorrow')
    env.nb('tw', 'status', b)
    assert fm(pb)['tw_status'] == 'waiting'


def test_body_and_other_keys_untouched(env):
    uuid, path = noted(env, 'Keep the rest')
    path.write_text(path.read_text().replace('---\n# ', '---\nmy note\n\n# ', 1)
                    .replace('type: task\n', 'type: task\npinned: yes\n'))
    env.task(uuid, 'done')
    env.nb('tw', 'status', uuid)
    text = path.read_text()
    assert 'pinned: yes' in text and 'my note\n\n# Keep the rest' in text


def test_no_note_is_a_quiet_no_op(env):
    uuid = env.add_task('--', 'No note at all')
    r = env.nb('tw', 'status', uuid)
    assert r.returncode == 0


def test_note_for_several_tasks_gets_no_single_status(env):
    home = env.nb_dir / 'home'
    (home / 'shared.md').write_text('# Shared\n')
    a = env.add_task('--', 'One')
    b = env.add_task('--', 'Two')
    env.nb('tw', 'link', 'home:shared.md', a)
    env.nb('tw', 'link', 'home:shared.md', b)
    env.task(a, 'done')
    env.nb('tw', 'status', a)
    assert 'tw_status' not in fm(home / 'shared.md')


def test_annn_note_without_frontmatter_is_left_alone(env):
    uuid = env.add_task('--', 'Plain annn')
    p = env.nb_dir / 'tasknotes' / f'plain-annn-{uuid[:8]}.note.md'
    p.write_text('first line\n')
    env.task(uuid, 'annotate', '--', f'nb: tasknotes:{p.name}')
    env.task(uuid, 'done')
    env.nb('tw', 'status', uuid)
    assert p.read_text() == 'first line\n'


# ── locks (nb-web invariant 76) ─────────────────────────────────────────────

def test_locked_note_is_skipped(env):
    uuid, path = noted(env, 'Locked note')
    path.write_text(path.read_text().replace('type: task\n', 'type: task\nlock: yes\n'))
    env.task(uuid, 'done')
    r = env.nb('tw', 'status', uuid)
    assert fm(path)['tw_status'] == 'pending'
    assert 'locked' in r.stdout + r.stderr


def test_locked_folder_is_skipped(env):
    uuid, path = noted(env, 'In a locked folder')
    (path.parent / '.nb-lock').write_text('frozen\n')
    env.task(uuid, 'done')
    env.nb('tw', 'status', uuid)
    assert fm(path)['tw_status'] == 'pending'


def test_no_new_note_in_a_locked_folder(env):
    (env.nb_dir / 'tasknotes' / '.nb-lock').write_text('')
    uuid = env.add_task('--', 'Nowhere to go')
    r = env.nb('tw', 'note', uuid, check=False)
    assert r.returncode != 0 and 'locked' in r.stderr
    assert not list((env.nb_dir / 'tasknotes').rglob('*.note.md'))


def test_link_refuses_a_locked_note(env):
    home = env.nb_dir / 'home'
    (home / 'frozen.md').write_text('---\nlock: true\n---\n# Frozen\n')
    uuid = env.add_task('--', 'Link me')
    r = env.nb('tw', 'link', 'home:frozen.md', uuid, check=False)
    assert r.returncode != 0 and 'locked' in r.stderr
    assert 'tw' not in fm(home / 'frozen.md')


# ── recurring: recurrence-overhaul shape (template + rtemplate occurrences) ──

@pytest.fixture
def overhaul(env):
    env.set_rc('uda.rtemplate.type', 'string')
    env.set_rc('uda.r.type', 'string')
    tpl = env.add_task('project:garden', 'r:1w', '--', 'Water the plants')
    occ = [env.add_task('project:garden', f'rtemplate:{tpl}', '--', 'Water the plants')
           for _ in range(2)]
    return tpl, occ


def test_series_by_default_one_note_for_all(env, overhaul):
    tpl, (o1, o2) = overhaul
    p = env.porcelain('note', o1)
    assert p['created'] == 'yes'
    assert p['selector'] == f'tasknotes:garden/water-the-plants-{tpl[:8]}.note.md'
    meta = fm(env.nb_dir / 'tasknotes' / p['selector'].split(':', 1)[1])
    assert meta['tw'] == tpl and meta['tw_recur'] == 'series'
    link = f'nb: {p["selector"]}'
    for u in (tpl, o1, o2):
        assert link in env.annotations(u), 'template and existing occurrences all link'
    again = env.porcelain('note', o2)
    assert again['created'] == 'no' and again['path'] == p['path']


def test_each_makes_a_folder_and_a_note_per_occurrence(env, overhaul):
    tpl, (o1, o2) = overhaul
    p1 = env.porcelain('note', o1, '--each')
    folder = f'tasknotes:garden/water-the-plants-{tpl[:8]}/'
    for u in (tpl, o1, o2):
        assert f'nb: {folder}' in env.annotations(u)
    assert p1['selector'] == f'{folder[:-1]}/water-the-plants-{o1[:8]}.note.md'
    m1 = fm(env.nb_dir / 'tasknotes' / p1['selector'].split(':', 1)[1])
    assert m1['tw'] == o1 and m1['tw_template'] == tpl
    assert f'nb: {p1["selector"]}' in env.annotations(o1)
    p2 = env.porcelain('note', o2)          # no flag: the template's choice stands
    assert p2['selector'] == f'{folder[:-1]}/water-the-plants-{o2[:8]}.note.md'
    assert env.git_clean('tasknotes')


def test_template_choice_wins_over_a_later_flag(env, overhaul):
    tpl, (o1, o2) = overhaul
    series = env.porcelain('note', o1)
    assert env.porcelain('note', o2, '--each')['path'] == series['path']


def test_note_on_each_template_is_the_folder(env, overhaul):
    tpl, (o1, _) = overhaul
    env.porcelain('note', o1, '--each')
    p = env.porcelain('note', tpl)
    assert p['selector'] == f'tasknotes:garden/water-the-plants-{tpl[:8]}/'
    assert p['created'] == 'no'


def test_series_occurrence_done_is_logged_not_closed(env, overhaul):
    tpl, (o1, o2) = overhaul
    path = env.nb_dir / 'tasknotes' / env.porcelain('note', o1)['selector'].split(':', 1)[1]
    env.task(o1, 'done')
    env.nb('tw', 'status', o1)
    env.nb('tw', 'status', o1)              # idempotent
    text = path.read_text()
    today = date.today().isoformat()
    assert text.count(f'- {today} ✓ done ({o1[:8]})') == 1
    assert '## Occurrences' in text
    assert fm(path)['tw_status'] == 'pending', 'the series note mirrors the template'
    env.task(o2, 'delete')
    env.nb('tw', 'status', o2)
    assert f'- {today} ✗ deleted ({o2[:8]})' in path.read_text()
    env.task(o1, 'modify', 'status:pending')
    env.nb('tw', 'status', o1)
    assert f'({o1[:8]})' not in path.read_text(), 'reopened: its line goes'


def test_series_ends_when_template_does(env, overhaul):
    tpl, (o1, _) = overhaul
    path = env.nb_dir / 'tasknotes' / env.porcelain('note', o1)['selector'].split(':', 1)[1]
    env.task(tpl, 'delete')
    env.nb('tw', 'status', tpl)
    assert fm(path)['tw_status'] == 'deleted'


def test_each_occurrence_note_mirrors_its_own_status(env, overhaul):
    tpl, (o1, _) = overhaul
    path = env.nb_dir / 'tasknotes' / env.porcelain('note', o1, '--each')['selector'].split(':', 1)[1]
    env.task(o1, 'done')
    env.nb('tw', 'status', o1)
    assert fm(path)['tw_status'] == 'completed'


# ── recurring: native Taskwarrior recurrence (parent:) ──────────────────────

def test_native_recurrence_series_and_inheritance(env):
    p = env.porcelain('add', 'Take out the bins', 'recur:weekly', 'due:today')
    t = env.export(p['uuid'])
    assert t['status'] == 'recurring'
    assert p['selector'] == f'tasknotes:take-out-the-bins-{p["uuid"][:8]}.note.md'
    assert fm(env.nb_dir / 'tasknotes' / p['selector'].split(':', 1)[1])['tw_recur'] == 'series'
    env.task('list', check=False)           # native recurrence spawns occurrences here
    kids = [x for x in __import__('json').loads(env.task('rc.json.array=on', 'export').stdout)
            if x.get('parent') == p['uuid']]
    assert kids, 'an occurrence was generated'
    for k in kids:
        assert f'nb: {p["selector"]}' in [a['description'] for a in k.get('annotations', [])], \
            'native occurrences inherit the template annotation'
        assert env.porcelain('note', k['uuid'])['path'] == p['path']


def test_add_recurring_each(env):
    p = env.porcelain('add', 'Stretch', 'recur:daily', 'due:today', '--each')
    assert p['selector'] == f'tasknotes:stretch-{p["uuid"][:8]}/'
    assert (env.nb_dir / 'tasknotes' / f'stretch-{p["uuid"][:8]}').is_dir()
    assert env.git_clean('tasknotes')
