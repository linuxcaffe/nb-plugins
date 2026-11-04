"""More of the task in its note's frontmatter (djp 2026-11-04: "adding a task's tags to FM makes
them nb searchable. Why not include more of a task's fields"). Written when the note is made and
on every change (`nb tw status`, which tw2nb's on-exit runs): tw_project, tw_due (local date),
tw_priority, title (the description), and tags beside nb's own (djp: "keep nb tags beside the
task's"): `tw_tags:` records which tags came from the task, so a tag added in nb stays when the
task's change. A note written before this (no tw_tags) counts a tag the task has as the task's.
One-way: the task is the source; nothing here changes the task.
"""
import yaml


def fm(path):
    text = path.read_text()
    return yaml.safe_load(text[4:text.index('\n---', 3)]) or {}


def note_of(env, uuid):
    p = env.porcelain('note', uuid)
    return env.nb_dir / p['selector'].replace(':', '/', 1)


def test_a_new_note_carries_the_tasks_fields(env):
    uuid = env.add_task('project:kitchen', 'due:2026-12-01', 'priority:H', '+reno', '+tiles', '--', 'Retile')
    m = fm(note_of(env, uuid))
    assert (m['tw_project'], str(m['tw_due']), m['tw_priority']) == ('kitchen', '2026-12-01', 'H')
    assert m['tags'] == ['reno', 'tiles'] and m['tw_tags'] == ['reno', 'tiles']
    assert m['title'] == 'Retile'


def test_a_change_follows_and_nb_tags_stay_beside_the_tasks(env):
    uuid = env.add_task('project:kitchen', '+reno', '--', 'Retile')
    path = note_of(env, uuid)
    path.write_text(path.read_text().replace('\ntags: [reno]', '\ntags: [reno, pat-smith]'))   # not tw_tags
    env.task(uuid, 'modify', 'project:bath', '-reno', '+grout', 'priority:L', '--', 'Retile the bath')
    env.nb('tw', 'status', uuid)
    m = fm(path)
    assert m['tags'] == ['pat-smith', 'grout'] and m['tw_tags'] == ['grout']
    assert (m['tw_project'], m['tw_priority'], m['title']) == ('bath', 'L', 'Retile the bath')


def test_a_field_the_task_drops_leaves_the_note(env):
    uuid = env.add_task('project:kitchen', 'due:2026-12-01', '+reno', '--', 'Retile')
    path = note_of(env, uuid)
    env.task(uuid, 'modify', 'project:', 'due:', '-reno')
    env.nb('tw', 'status', uuid)
    m = fm(path)
    assert not {'tw_project', 'tw_due', 'tags', 'tw_tags'} & set(m)
    assert m['tw_status'] == 'pending'


def test_hand_written_tags_from_before(env):
    uuid = env.add_task('+bug', '+test', '--', 'Older note')
    path = note_of(env, uuid)
    text = path.read_text()
    start = text.index('tags:')
    end = text.index('\n', text.index('tw_tags:')) + 1
    path.write_text(text[:start] + 'tags: bug,test,mine\n' + text[end:])   # as djp typed it, no tw_tags
    env.nb('tw', 'status', uuid)                     # the first copy: bug, test are the task's
    assert fm(path)['tw_tags'] == ['bug', 'test']
    env.task(uuid, 'modify', '-test')
    env.nb('tw', 'status', uuid)
    m = fm(path)
    assert m['tags'] == ['mine', 'bug'] and m['tw_tags'] == ['bug']


def test_nothing_changed_writes_nothing(env):
    import subprocess
    uuid = env.add_task('project:kitchen', '+reno', '--', 'Quiet')
    path = note_of(env, uuid)
    root = env.nb_dir / 'tasknotes'
    head = lambda: subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout
    before, text = head(), path.read_text()
    env.nb('tw', 'status', uuid)
    assert (head(), path.read_text()) == (before, text)
