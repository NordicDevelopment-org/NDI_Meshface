from meshdash.revision import RevisionInfo, detect_git_commit, revision_info, sanitize_revision_token


def test_sanitize_revision_token_filters_characters():
    assert sanitize_revision_token(" v1.2.3+abc!@# ", "fallback") == "v1.2.3+abc"


def test_detect_git_commit_prefers_explicit():
    commit = detect_git_commit(
        explicit_commit="abc123def",
        script_dir="/tmp",
        cwd="/tmp",
        unknown_git_commit="nogit",
    )
    assert commit == "abc123def"


def test_revision_info_uses_detect_commit_callback():
    info = revision_info(
        version_raw="v2.0.1",
        default_version="0.1.0",
        unknown_git_commit="nogit",
        detect_commit=lambda: "deadbeef",
    )
    assert isinstance(info, RevisionInfo)
    assert info.version == "2.0.1"
    assert info.commit == "deadbeef"
    assert info.label == "Rev: v2.0.1 (deadbeef)"
    assert "version 2.0.1" in info.title
