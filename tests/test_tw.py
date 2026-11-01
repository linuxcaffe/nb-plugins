"""tw.nb-plugin, M1 of the tw-nb-interop plan (claude:tw_nb_interop_plan_2026-11-01.md):
`nb tw note | add | link | info`, the lock handoff and --porcelain."""
import fcntl
import subprocess

import pytest
import yaml


def fm(path):
    """A note's frontmatter, parsed as YAML (uuids come back as strings)."""
    text = path.read_text()
    assert text.startswith('---\n'), text[:80]
    return yaml.safe_load(text[4:text.index('\n---', 3)]) or {}


# ── nb tw note ───────────────────────────────────────────────────────────────

def test_note_creates_tasknote_with_frontmatter_and_annotation(env):
    uuid = env.add_task('--', 'Fix the billing discrepancy')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'yes'
    assert p['selector'] == f'tw:fix-the-billing-discrepancy-{uuid[:8]}.note.md'
    path = env.nb_dir / 'tw' / f'fix-the-billing-discrepancy-{uuid[:8]}.note.md'
    assert p['path'] == str(path)
    meta = fm(path)
    assert meta['type'] == 'task'
    assert meta['tw'] == uuid
    assert meta['tw_status'] == 'pending'
    assert meta['title'] == 'Fix the billing discrepancy'
    assert f'nb: {p["selector"]}' in env.annotations(uuid)
    assert env.git_clean('tw'), 'note is committed'
    listed = env.nb('tw:list', '--no-color', check=False).stdout
    assert 'Fix the billing discrepancy' in listed or path.name in listed, 'nb indexed it'


def test_note_by_numeric_id(env):
    env.add_task('--', 'First')
    uuid = env.add_task('--', 'Second one')
    p = env.porcelain('note', '2')
    assert p['uuid'] == uuid


def test_note_again_returns_the_same_note_and_one_annotation(env):
    uuid = env.add_task('--', 'Water the plants')
    first = env.porcelain('note', uuid)
    again = env.porcelain('note', uuid)
    assert again['created'] == 'no'
    assert again['path'] == first['path']
    assert sum(a.startswith('nb: ') for a in env.annotations(uuid)) == 1


@pytest.mark.parametrize('depth, folder', [(None, 'kitchen/'), ('1', 'kitchen/'),
                                           ('2', 'kitchen/reno/'), ('0', '')])
def test_project_folders_follow_folder_depth(env, depth, folder):
    if depth is not None:
        env.set_rc('tw.folder_depth', depth)
    uuid = env.add_task('project:kitchen.reno.tiles', '--', 'Grout the backsplash')
    p = env.porcelain('note', uuid)
    assert p['selector'] == f'tw:{folder}grout-the-backsplash-{uuid[:8]}.note.md'
    assert (env.nb_dir / 'tw' / folder / f'grout-the-backsplash-{uuid[:8]}.note.md').is_file()
    assert env.git_clean('tw')


def test_existing_annotation_wins_even_in_another_notebook(env):
    cine = env.notebook('cine')
    (cine / 'edl-definition.md').write_text('---\ntype: cine\n---\n# EDL\n')
    env.run('git', '-C', str(cine), 'add', '-A')
    env.run('git', '-C', str(cine), 'commit', '-qm', 'edl')
    uuid = env.add_task('--', 'Define the EDL')
    env.task(uuid, 'annotate', '--', 'nb: cine:edl-definition.md')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'no'
    assert p['selector'] == 'cine:edl-definition.md'
    assert not list((env.nb_dir / 'tw').glob('*.note.md'))


def test_bare_annotation_means_tw(env):
    uuid = env.add_task('--', 'Bare link')
    name = f'bare-link-{uuid[:8]}.note.md'
    (env.nb_dir / 'tw' / name).write_text(f'---\ntype: task\ntw: {uuid}\n---\n')
    env.task(uuid, 'annotate', '--', f'nb: {name}')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'no'
    assert p['selector'] == f'tw:{name}'


def test_lost_annotation_found_by_uuid_and_restored(env):
    uuid = env.add_task('--', 'Lost link')
    first = env.porcelain('note', uuid)
    ann = f'nb: {first["selector"]}'
    env.task(uuid, 'denotate', '--', ann)
    p = env.porcelain('note', uuid)
    assert p['created'] == 'no'
    assert p['path'] == first['path']
    assert ann in env.annotations(uuid)


def test_notebook_option_and_project_map(env):
    env.notebook('cine')
    a = env.add_task('project:kitchen', '--', 'Explicit notebook')
    assert env.porcelain('note', a, '--notebook', 'cine')['selector'] == \
        f'cine:explicit-notebook-{a[:8]}.note.md'
    env.set_rc('tw.notebook.film', 'cine')
    b = env.add_task('project:film.edit', '--', 'Mapped project')
    assert env.porcelain('note', b)['selector'] == f'cine:mapped-project-{b[:8]}.note.md', \
        'project folders apply to tw: only'
    assert env.git_clean('cine')


def test_template_fills_fields(env):
    tdir = env.nb_dir / 'tw' / '.templates'
    tdir.mkdir()
    (tdir / 'task.md').write_text('# {{description}}\n\nproject {{project}}, uuid {{uuid}}\n'
                                  '{{missing|fallback}}\n')
    uuid = env.add_task('project:kitchen', '--', 'Templated')
    p = env.porcelain('note', uuid)
    body = open(p['path']).read().split('\n---\n', 1)[1]
    assert '# Templated' in body
    assert f'project kitchen, uuid {uuid}' in body
    assert 'fallback' in body


def test_default_body_without_template(env):
    uuid = env.add_task('--', 'No template here')
    body = open(env.porcelain('note', uuid)['path']).read().split('\n---\n', 1)[1]
    assert body.strip() == '# No template here'


def test_awkward_description_is_one_argument_and_a_tidy_slug(env):
    desc = '-rf "quoted" $HOME; rm it & café'
    uuid = env.add_task('--', desc)
    p = env.porcelain('note', uuid)
    assert p['selector'] == f'tw:rf-quoted-home-rm-it-caf-{uuid[:8]}.note.md'
    assert fm(env.nb_dir / 'tw' / p['selector'][3:])['title'] == desc


def test_porcelain_has_no_colour(env):
    uuid = env.add_task('--', 'Plain output')
    out = env.run('nb', 'tw', 'note', uuid, '--porcelain').stdout
    assert '\x1b' not in out


def test_unknown_task_fails_cleanly(env):
    r = env.nb('tw', 'note', 'deadbeef', check=False)
    assert r.returncode != 0
    assert 'no task' in (r.stdout + r.stderr).lower()


# ── nb tw add ────────────────────────────────────────────────────────────────

def test_add_creates_task_and_note(env):
    p = env.porcelain('add', 'Buy grout', 'project:kitchen', 'priority:H')
    t = env.export(p['uuid'])
    assert t['description'] == 'Buy grout'
    assert t['project'] == 'kitchen' and t['priority'] == 'H'
    assert p['created'] == 'yes'
    assert p['selector'] == f'tw:kitchen/buy-grout-{p["uuid"][:8]}.note.md'
    assert f'nb: {p["selector"]}' in env.annotations(p['uuid'])


def test_add_description_cannot_become_a_command(env):
    p = env.porcelain('add', 'delete')
    assert env.export(p['uuid'])['description'] == 'delete'


# ── nb tw link ───────────────────────────────────────────────────────────────

def test_link_existing_note_keeps_type_and_adds_list_of_tasks(env):
    cine = env.notebook('cine')
    note = cine / 'edl-definition.md'
    note.write_text('---\ntype: cine\ntitle: EDL definition\n---\n# EDL\n')
    env.run('git', '-C', str(cine), 'add', '-A')
    env.run('git', '-C', str(cine), 'commit', '-qm', 'edl')
    a = env.add_task('--', 'Define the EDL')
    b = env.add_task('--', 'Review the EDL')
    env.nb('tw', 'link', 'cine:edl-definition.md', a)
    assert fm(note)['type'] == 'cine'
    assert fm(note)['tw'] == a
    env.nb('tw', 'link', 'cine:edl-definition.md', b)
    assert fm(note)['tw'] == [a, b]
    assert 'nb: cine:edl-definition.md' in env.annotations(a)
    assert 'nb: cine:edl-definition.md' in env.annotations(b)
    assert note.read_text().endswith('# EDL\n'), 'body untouched'
    assert note.name == 'edl-definition.md', 'never renamed'
    assert env.git_clean('cine')


def test_link_note_without_frontmatter(env):
    home = env.nb_dir / 'home'
    (home / 'plain.md').write_text('# Plain\n')
    uuid = env.add_task('--', 'Plain link')
    env.nb('tw', 'link', 'home:plain.md', uuid)
    text = (home / 'plain.md').read_text()
    assert text.startswith(f'---\ntw: {uuid}\n---\n')
    assert text.endswith('# Plain\n')


# ── nb tw info ───────────────────────────────────────────────────────────────

def test_info_reads_frontmatter_uuid(env):
    uuid = env.add_task('--', 'Info about me')
    env.porcelain('note', uuid)
    out = env.nb('tw', 'info', f'tw:info-about-me-{uuid[:8]}.note.md').stdout
    assert 'Info about me' in out and uuid in out


def test_bare_info_alias_still_works(env):
    uuid = env.add_task('--', 'Alias check')
    env.porcelain('note', uuid)
    out = env.nb('info', f'tw:alias-check-{uuid[:8]}.note.md').stdout
    assert 'Alias check' in out


# ── lock handoff (invariant 72) ─────────────────────────────────────────────

def _hold_lock(env):
    lock = env.nb_dir / '.logs' / 'nb-web-nb.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock, 'a')
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def test_waits_for_the_nb_lock(env):
    uuid = env.add_task('--', 'Locked out')
    f = _hold_lock(env)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            env.nb('tw', 'note', uuid, timeout=4)
    finally:
        f.close()


def test_lock_held_by_caller_is_not_taken_again(env):
    uuid = env.add_task('--', 'Caller holds it')
    f = _hold_lock(env)
    try:
        p = env.porcelain('note', uuid, env={'NB_LOCK_HELD': '1'}, timeout=30)
        assert p['created'] == 'yes'
    finally:
        f.close()


@pytest.mark.parametrize('word', ['rc.data.location:/tmp/elsewhere', 'rc.hooks:on', 'RC.hooks:on',
                                  'delete', 'modify', '/regex/', 'a=b'])
def test_add_refuses_words_that_are_not_attributes(env, word):
    """invariant 82: a user word can't set an rc override or name a command."""
    r = env.nb('tw', 'add', 'Sneaky', word, check=False)
    assert r.returncode != 0
    assert 'not an attribute' in r.stderr
    assert env.task('count', check=False).stdout.strip() == '0'
