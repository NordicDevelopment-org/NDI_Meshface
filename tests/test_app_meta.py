from meshdash.app_meta import detect_git_commit_from_env, revision_info_from_env
from meshdash.revision import RevisionInfo


def test_detect_git_commit_from_env_passes_expected_context(tmp_path):
    captured = {}

    def _fake_detect_git_commit(**kwargs):
        captured.update(kwargs)
        return "abc123"

    commit = detect_git_commit_from_env(
        script_file=str(tmp_path / "mesh_dashboard.py"),
        cwd=str(tmp_path),
        explicit_commit="deadbeef",
        unknown_git_commit="nogit",
        detect_git_commit_fn=_fake_detect_git_commit,
    )

    assert commit == "abc123"
    assert captured["explicit_commit"] == "deadbeef"
    assert captured["cwd"] == str(tmp_path)
    assert captured["unknown_git_commit"] == "nogit"
    assert captured["script_dir"] == str(tmp_path)


def test_revision_info_from_env_uses_build_function():
    captured = {}

    def _fake_build_revision_info(**kwargs):
        captured.update(kwargs)
        return RevisionInfo(version="1.2.3", commit="abc", label="L", title="T")

    info = revision_info_from_env(
        env_version="v1.2.3",
        default_version="0.1.0",
        unknown_git_commit="nogit",
        detect_commit_fn=lambda: "abc",
        build_revision_info_fn=_fake_build_revision_info,
    )

    assert isinstance(info, RevisionInfo)
    assert info.version == "1.2.3"
    assert captured["version_raw"] == "v1.2.3"
    assert captured["default_version"] == "0.1.0"
    assert captured["unknown_git_commit"] == "nogit"
    assert callable(captured["detect_commit"])
