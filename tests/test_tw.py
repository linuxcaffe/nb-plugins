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
    assert p['selector'] == f'tasknotes:fix-the-billing-discrepancy-{uuid[:8]}.note.md'
    path = env.nb_dir / 'tasknotes' / f'fix-the-billing-discrepancy-{uuid[:8]}.note.md'
    assert p['path'] == str(path)
    meta = fm(path)
    assert meta['type'] == 'task'
    assert meta['tw'] == uuid
    assert meta['tw_status'] == 'pending'
    assert meta['title'] == 'Fix the billing discrepancy'
    assert f'nb: {p["selector"]}' in env.annotations(uuid)
    assert env.git_clean('tasknotes'), 'note is committed'
    listed = env.nb('tasknotes:list', '--no-color', check=False).stdout
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
    assert p['selector'] == f'tasknotes:{folder}grout-the-backsplash-{uuid[:8]}.note.md'
    assert (env.nb_dir / 'tasknotes' / folder / f'grout-the-backsplash-{uuid[:8]}.note.md').is_file()
    assert env.git_clean('tasknotes')


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
    assert not list((env.nb_dir / 'tasknotes').glob('*.note.md'))


def test_bare_annotation_means_tw(env):
    uuid = env.add_task('--', 'Bare link')
    name = f'bare-link-{uuid[:8]}.note.md'
    (env.nb_dir / 'tasknotes' / name).write_text(f'---\ntype: task\ntw: {uuid}\n---\n')
    env.task(uuid, 'annotate', '--', f'nb: {name}')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'no'
    assert p['selector'] == f'tasknotes:{name}'


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
        'project folders apply to tasknotes: only'
    assert env.git_clean('cine')


def test_template_fills_fields(env):
    tdir = env.nb_dir / 'tasknotes' / '.templates'
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
    assert p['selector'] == f'tasknotes:rf-quoted-home-rm-it-caf-{uuid[:8]}.note.md'
    assert fm(env.nb_dir / 'tasknotes' / p['selector'].split(':', 1)[1])['title'] == desc


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
    assert p['selector'] == f'tasknotes:kitchen/buy-grout-{p["uuid"][:8]}.note.md'
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
    assert text.startswith(f'---\ntw: {uuid}\ntype: task\n')   # linking makes it a task note (djp 2026-11-04)
    assert text.endswith('# Plain\n')


# ── nb tw info ───────────────────────────────────────────────────────────────

def test_info_reads_frontmatter_uuid(env):
    uuid = env.add_task('--', 'Info about me')
    env.porcelain('note', uuid)
    out = env.nb('tw', 'info', f'tasknotes:info-about-me-{uuid[:8]}.note.md').stdout
    assert 'Info about me' in out and uuid in out


def test_bare_info_alias_still_works(env):
    uuid = env.add_task('--', 'Alias check')
    env.porcelain('note', uuid)
    out = env.nb('info', f'tasknotes:alias-check-{uuid[:8]}.note.md').stdout
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


# ── backwards compatibility: annn, tw2nb, the old `nb info` ─────────────────

def test_annn_note_without_frontmatter_is_found_not_duplicated(env):
    """annn writes <slug>-<uuid8>.note.md with no frontmatter; it is the task's note."""
    uuid = env.add_task('--', 'Old annn note')
    old = env.nb_dir / 'tasknotes' / f'old-annn-note-{uuid[:8]}.note.md'
    old.write_text('just text, as annn writes it\n')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'no'
    assert p['path'] == str(old)
    assert len(list((env.nb_dir / 'tasknotes').rglob('*.note.md'))) == 1


def _tw2nb_archive(env, uuid):
    """A tw2nb-style archive note in tasks:, linked by tw2nb's numeric breadcrumb."""
    tasks = env.notebook('tasks')
    env.nb('tasks:add', '--filename', 'archived.todo.md',
           '--content', f'# [x] Archived thing\n\n`{uuid[:8]}`\n')
    nid = env.nb('tasks:list', '--no-color').stdout.split(']')[0].split(':')[-1]
    return tasks / 'archived.todo.md', f'tasks:{nid}'


def test_tw2nb_numeric_annotation_is_honoured(env):
    uuid = env.add_task('--', 'Archived thing')
    path, sel = _tw2nb_archive(env, uuid)
    env.task(uuid, 'annotate', '--', f'nb: {sel}')
    p = env.porcelain('note', uuid)
    assert p['created'] == 'no'
    assert p['path'] == str(path)
    assert sum(a.startswith('nb: ') for a in env.annotations(uuid)) == 1


def test_info_numeric_selector_like_old_plugin(env):
    uuid = env.add_task('--', 'Archived thing')
    _, sel = _tw2nb_archive(env, uuid)
    out = env.nb('info', sel).stdout
    assert 'Archived thing' in out


def test_info_bare_selector_uses_current_notebook_like_nb(env):
    """Bare means tw: only inside nb: annotations; on the command line it's nb's own rule."""
    uuid = env.add_task('--', 'In home')
    (env.nb_dir / 'home' / 'same.md').write_text(f'`{uuid[:8]}`\n')
    (env.nb_dir / 'tasknotes' / 'same.md').write_text('no uuid here\n')
    env.nb('use', 'home')
    out = env.nb('info', 'same.md', check=False)
    assert 'In home' in out.stdout, out.stderr


def test_a_note_that_names_the_task_beats_an_earlier_archive_link(env):
    """tw2nb's `nb: tasks:N` (an archive) may come first; the real tasknote wins."""
    uuid = env.add_task('--', 'Archived thing')
    _, sel = _tw2nb_archive(env, uuid)
    env.task(uuid, 'annotate', '--', f'nb: {sel}')
    real = env.nb_dir / 'tasknotes' / f'archived-thing-{uuid[:8]}.note.md'
    real.write_text(f'---\ntype: task\ntw: {uuid}\n---\n# mine\n')
    env.task(uuid, 'annotate', '--', f'nb: tasknotes:{real.name}')
    assert env.porcelain('note', uuid)['path'] == str(real)


def test_find_never_creates(env):
    uuid = env.add_task('--', 'Only looking')
    r = env.nb('tw', 'note', uuid, '--find', '--porcelain', check=False)
    assert r.returncode == 1
    assert not list((env.nb_dir / 'tasknotes').rglob('*.note.md'))
    assert env.annotations(uuid) == []
    made = env.porcelain('note', uuid)
    found = env.porcelain('note', uuid, '--find')
    assert found['path'] == made['path'] and found['created'] == 'no'


def test_add_odd_tags_go_through_tags_list(env):
    """Taskwarrior silently drops +bug-fix; tags:bug-fix,v2.1 works (tw-web's own route)."""
    p = env.porcelain('add', 'Tagged', 'tags:bug-fix,v2.1', '+next')
    assert sorted(env.export(p['uuid'])['tags']) == ['bug-fix', 'next', 'v2.1']


@pytest.mark.parametrize('word', ['+bug-fix', '+v2.1', '+a,b', "+it's"])
def test_add_refuses_tags_taskwarrior_would_drop(env, word):
    r = env.nb('tw', 'add', 'Odd', word, check=False)
    assert r.returncode != 0 and 'not an attribute' in r.stderr and 'tags:' in r.stderr


# ── a moved / renamed note: link replaces the stale annotation (djp, 2026-11-01) ──────────

def _git_mv(env, nb, old, new):
    d = env.nb_dir / nb
    (d / new).parent.mkdir(parents=True, exist_ok=True)
    env.run('git', '-C', str(d), 'mv', old, new)
    env.run('git', '-C', str(d), 'commit', '-qm', 'move')


def test_link_after_a_move_replaces_the_stale_annotation(env):
    uuid = env.add_task('project:legal.dogbite', '--', 'Write thankyou note')
    sel = env.porcelain('note', uuid)['selector']                 # tasknotes:legal/write-…
    old_rel = sel.split(':', 1)[1]
    name = old_rel.split('/')[-1]
    _git_mv(env, 'tasknotes', old_rel, name)
    env.nb('tw', 'link', f'tasknotes:{name}', uuid)
    assert env.annotations(uuid) == [f'nb: tasknotes:{name}']


def test_link_from_replaces_a_renamed_notes_annotation(env):
    uuid = env.add_task('--', 'Rename me')
    old = env.porcelain('note', uuid)['selector'].split(':', 1)[1]
    _git_mv(env, 'tasknotes', old, 'renamed.note.md')
    env.nb('tw', 'link', 'tasknotes:renamed.note.md', uuid, '--from', f'tasknotes:{old}')
    assert env.annotations(uuid) == ['nb: tasknotes:renamed.note.md']


def test_link_keeps_annotations_it_cannot_prove_stale(env):
    """A note missing *here* may live on another station (a notebook that doesn't sync), and a
    second note that still exists is a real link: neither is touched."""
    uuid = env.add_task('--', 'Keep my links')
    sel = env.porcelain('note', uuid)['selector']
    env.task(uuid, 'annotate', '--', 'nb: cine:edl-definition.md')        # not on this machine
    home = env.nb_dir / 'home'
    (home / 'other.md').write_text('# Other\n')
    env.task(uuid, 'annotate', '--', 'nb: home:other.md')                 # exists
    old = sel.split(':', 1)[1]
    _git_mv(env, 'tasknotes', old, 'moved.note.md')
    env.nb('tw', 'link', 'tasknotes:moved.note.md', uuid, '--from', sel)
    ann = env.annotations(uuid)
    assert 'nb: cine:edl-definition.md' in ann and 'nb: home:other.md' in ann
    assert sel not in [a[4:] for a in ann] and 'nb: tasknotes:moved.note.md' in ann
