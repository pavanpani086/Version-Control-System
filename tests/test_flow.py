from pathlib import Path

from minivcs.repo import MiniVCSRepo


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def test_basic_flow(tmp_path: Path):
    repo = MiniVCSRepo(tmp_path)
    repo.init()
    repo.set_user('Test User', 'test@example.com')

    write(tmp_path / 'a.txt', 'hello\n')
    assert repo.add(['a.txt']) == ['a.txt']
    first = repo.commit('first commit')
    assert first
    assert repo.head_commit() == first
    assert len(repo.log()) == 1

    write(tmp_path / 'a.txt', 'hello updated\n')
    diff_output = repo.diff()
    assert '-hello\n' in diff_output
    assert '+hello updated\n' in diff_output


def test_merge_flow(tmp_path: Path):
    repo = MiniVCSRepo(tmp_path)
    repo.init()
    repo.set_user('Test User', 'test@example.com')

    write(tmp_path / 'a.txt', 'base\n')
    repo.add(['a.txt'])
    repo.commit('base commit')

    repo.branch('feature')
    repo.checkout('feature')
    write(tmp_path / 'feature.txt', 'feature work\n')
    repo.add(['feature.txt'])
    feature_commit = repo.commit('feature commit')

    repo.checkout('main')
    result = repo.merge('feature')
    assert result.merged is True
    assert result.fast_forward is True
    assert repo.head_commit() == feature_commit or repo.head_commit() is not None
    assert (tmp_path / 'feature.txt').exists()
