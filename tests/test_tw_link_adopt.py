"""An existing task and an existing note, joined (djp 2026-11-04: "how would I connect them?").
Every way in ends in `nb tw link`:

- link sets `type: task` when the note has no type, or the plain `note` (djp: yes); a note with
  a type of its own (project, job, cine) keeps it and just gains tw:
- link replaces what it resolves: `tw: 89` (an ID changes after gc), or a short uuid, written by
  hand, becomes the task's full uuid; one task stays a scalar `tw: <uuid>`
- status adopts: a task annotated `nb: <notebook>:<path>` (tw-web, the CLI, vit) pointing at an
  existing note with no tw: (or only a short ref to this task) links that note, then copies the
  fields as usual. A note naming another task is left alone: never taken over.
"""
import yaml


def fm(path):
    text = path.read_text()
    return yaml.safe_load(text[4:text.index('\n---', 3)]) or {}


def note(env, name, text, nb='home'):
    p = env.nb_dir / nb / name
    p.write_text(text)
    env.run('git', '-C', str(env.nb_dir / nb), 'add', '-A')
    env.run('git', '-C', str(env.nb_dir / nb), 'commit', '-qm', name)
    return p


def test_link_makes_a_plain_note_a_task_note(env):
    p = note(env, 'plain.md', '---\ntitle: Plain\n---\n# Plain\n')
    uuid = env.add_task('--', 'Plain link')
    env.nb('tw', 'link', 'home:plain.md', uuid)
    m = fm(p)
    assert m['type'] == 'task' and m['tw'] == uuid
    assert m['tw_status'] == 'pending'                      # and its fields follow at once


def test_link_keeps_a_type_of_its_own(env):
    p = note(env, 'job.md', '---\ntype: job\n---\n# Job\n')
    uuid = env.add_task('--', 'Job task')
    env.nb('tw', 'link', 'home:job.md', uuid)
    assert fm(p)['type'] == 'job' and fm(p)['tw'] == uuid


def test_link_note_type_becomes_task(env):
    p = note(env, 'n.md', '---\ntype: note\n---\n# N\n')
    uuid = env.add_task('--', 'N task')
    env.nb('tw', 'link', 'home:n.md', uuid)
    assert fm(p)['type'] == 'task'


def _id(env, uuid):
    return str(env.export(uuid)['id'])


def test_link_resolves_an_id_written_by_hand(env):
    uuid = env.add_task('--', 'By its ID')
    tid = _id(env, uuid)
    p = note(env, 'by-id.md', f'---\ntype: task\ntw: {tid}\n---\n# By ID\n')
    env.nb('tw', 'link', 'home:by-id.md', tid)
    assert fm(p)['tw'] == uuid                              # the full uuid, a scalar, no 89 left
    assert 'nb: home:by-id.md' in env.annotations(uuid)


def test_link_resolves_a_short_uuid_written_by_hand(env):
    uuid = env.add_task('--', 'By short uuid')
    p = note(env, 'by-short.md', f'---\ntw: {uuid[:8]}\n---\n# Short\n')
    env.nb('tw', 'link', 'home:by-short.md', uuid[:8])
    assert fm(p)['tw'] == uuid and fm(p)['type'] == 'task'


def test_status_adopts_a_note_the_task_points_at(env):
    p = note(env, 'adopt-me.md', '---\ntitle: Adopt me\n---\n# Adopt me\n\nMine.\n')
    uuid = env.add_task('project:kitchen', '--', 'Adopt me')
    env.task(uuid, 'annotate', '--', 'nb: home:adopt-me.md')     # tw-web, the CLI, vit
    env.nb('tw', 'status', uuid)
    m = fm(p)
    assert m['tw'] == uuid and m['type'] == 'task'
    assert m['tw_status'] == 'pending' and m['project'] == 'kitchen'
    assert p.read_text().endswith('# Adopt me\n\nMine.\n')      # body untouched
    assert env.git_clean('home')


def test_status_never_takes_over_another_tasks_note(env):
    other = env.add_task('--', 'The owner')
    p = note(env, 'owned.md', f'---\ntype: task\ntw: {other}\n---\n# Owned\n')
    uuid = env.add_task('--', 'Claims it')
    env.task(uuid, 'annotate', '--', 'nb: home:owned.md')
    env.nb('tw', 'status', uuid)
    assert fm(p)['tw'] == other                              # left as it was


def test_status_adopts_a_short_ref_to_itself(env):
    uuid = env.add_task('--', 'Short ref')
    p = note(env, 'short-ref.md', f'---\ntw: {uuid[:8]}\n---\n# S\n')
    env.task(uuid, 'annotate', '--', 'nb: home:short-ref.md')
    env.nb('tw', 'status', uuid)
    assert fm(p)['tw'] == uuid
