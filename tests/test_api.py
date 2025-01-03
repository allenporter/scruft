import json
import os
import re
from pathlib import Path
from subprocess import run

import pytest
from git import Repo

import scruft
from scruft import exceptions
from scruft._commands import utils

TEST_PYTHON_REPO = "https://github.com/timothycrosley/cookiecutter-python"
TEST_CRUFT_REPO = "https://github.com/timothycrosley/cruft"
TEST_COOKIECUTTER_REPO = "https://github.com/cruft/cookiecutter-test"


def test_invalid_cookiecutter_repo(tmpdir):
    with pytest.raises(exceptions.InvalidCookiecutterRepository):
        scruft.create("invalid-rep", Path(tmpdir))


def test_invalid_cookiecutter_reference(tmpdir):
    with pytest.raises(exceptions.InvalidCookiecutterRepository):
        scruft.create(TEST_COOKIECUTTER_REPO, Path(tmpdir), checkout="invalid-reference")


def test_no_cookiecutter_dir(tmpdir):
    with pytest.raises(exceptions.UnableToFindCookiecutterTemplate):
        scruft.create(TEST_COOKIECUTTER_REPO, Path(tmpdir))


def test_create(tmpdir):
    tmpdir.chdir()
    scruft.create(TEST_PYTHON_REPO)


def test_check(tmpdir, project_dir):
    tmpdir.chdir()
    with pytest.raises(exceptions.NoCruftFound):
        scruft.check()

    os.chdir(project_dir)
    scruft.check()


def test_create_with_skips(tmpdir):
    tmpdir.chdir()
    skips = ["setup.cfg"]
    scruft.create(TEST_PYTHON_REPO, Path(tmpdir), skip=skips)

    assert json.load((tmpdir / "python_project_name" / ".cruft.json").open("r"))["skip"] == skips


@pytest.mark.parametrize("value", ["main", None])
def test_create_stores_checkout_value(value, tmpdir):
    tmpdir.chdir()

    scruft.create(
        TEST_PYTHON_REPO, Path(tmpdir), checkout=value
    )

    assert (
        json.load((tmpdir / "python_project_name" / ".cruft.json").open("r"))["checkout"] == value
    )


@pytest.mark.parametrize("value", ["main", None])
def test_link_stores_checkout_value(value, tmpdir):
    project_dir = Path(tmpdir)
    scruft.link(
        TEST_PYTHON_REPO,
        project_dir=project_dir,
        checkout=value,
    )

    assert json.load(utils.cruft.get_cruft_file(project_dir).open("r"))["checkout"] == value


@pytest.mark.parametrize("value", ["main", None])
def test_update_stores_checkout_value(value, tmpdir):
    tmpdir.chdir()
    scruft.create(
        TEST_PYTHON_REPO,
        Path(tmpdir),
        checkout="ea8f733f85e7089df338d41ace199d3f4d397e29",
    )
    project_dir = tmpdir / "python_project_name"

    scruft.update(Path(project_dir), checkout=value)

    assert json.load((project_dir / ".cruft.json").open("r"))["checkout"] == value


def test_update_and_check_real_repo(tmpdir):
    tmpdir.chdir()
    repo = Repo.clone_from(TEST_CRUFT_REPO, str(tmpdir))
    repo.head.reset(commit="86a6e6beda8095690414ff7652c15b7ae36e6128", working_tree=True)
    with open(os.path.join(tmpdir, ".cruft.json")) as cruft_file:
        cruft_state = json.load(cruft_file)
        cruft_state["skip"] = ["cruft/__init__.py", "tests"]
    with open(os.path.join(tmpdir, ".cruft.json"), "w") as cruft_file:
        json.dump(cruft_state, cruft_file)
    repo_dir = Path(tmpdir)
    assert not scruft.check(repo_dir)
    # Update should fail since we have an unclean git repo
    assert not scruft.update(repo_dir)
    # Commit the changes so that the repo is clean
    run(
        [
            "git",
            "-c",
            "user.name='test'",
            "-c",
            "user.email='user@test.com'",
            "commit",
            "-am",
            "test",
        ],
        cwd=repo_dir,
    )
    assert scruft.update(repo_dir, skip_apply_ask=True)


def test_update_allows_untracked_files_option(tmpdir):
    tmpdir.chdir()
    Repo.clone_from(TEST_CRUFT_REPO, str(tmpdir))
    with open(os.path.join(tmpdir, "untracked.txt"), "w") as new_file:
        new_file.write("hello, world!\n")
    repo_dir = Path(tmpdir)
    # update should fail since repo is now unclean (has a tracked file)
    assert not scruft.update(repo_dir)
    # update should work if allow_untracked_files is True
    assert scruft.update(repo_dir, allow_untracked_files=True)


def test_relative_repo_check(tmpdir):
    tmpdir.chdir()
    temp_dir = Path(tmpdir)
    Repo.clone_from(TEST_COOKIECUTTER_REPO, str(temp_dir / "cc"))
    project_dir = scruft.create("./cc", output_dir=str(temp_dir / "output"), directory="dir")
    assert scruft.check(project_dir)


def test_update(project_dir, tmpdir):
    tmpdir.chdir()
    with pytest.raises(exceptions.NoCruftFound):
        scruft.update(skip_apply_ask=False)

    os.chdir(project_dir)
    scruft.update(skip_apply_ask=True)


def test_link(project_dir, tmpdir):
    os.chdir(project_dir)
    with pytest.raises(exceptions.CruftAlreadyPresent):
        scruft.link(TEST_PYTHON_REPO)

    tmpdir.chdir()
    Repo.clone_from(TEST_CRUFT_REPO, str(tmpdir))
    os.remove(os.path.join(tmpdir, ".cruft.json"))
    scruft.link(TEST_PYTHON_REPO)


def test_directory_and_checkout(tmpdir):
    output_path = scruft.create(
        TEST_COOKIECUTTER_REPO,
        output_dir=Path(tmpdir),
        directory="dir",
        checkout="initial",
    )
    cruft_file = utils.cruft.get_cruft_file(output_path)
    assert cruft_file.exists()
    assert scruft.check(output_path, checkout="initial")
    assert not scruft.check(output_path, checkout="updated")
    assert scruft.update(output_path, checkout="updated")
    assert scruft.check(output_path, checkout="updated")
    cruft_file.unlink()
    assert not cruft_file.exists()
    assert scruft.link(
        TEST_COOKIECUTTER_REPO,
        project_dir=output_path,
        directory="dir",
        checkout="updated",
    )
    assert scruft.check(output_path, checkout="updated")
    # Add checks for strictness where main is an older
    # version than updated
    assert not scruft.check(output_path, strict=True)
    assert scruft.check(output_path, strict=False)


@pytest.mark.parametrize(
    "exit_code,isatty,expect_reproducible_diff,expected_return_value",
    [
        (False, False, True, True),  # $ cruft diff | cat
        (False, True, False, True),  # $ cruft diff
        (True, False, True, False),  # $ cruft diff --exit-code | cat
        (True, True, False, False),  # $ cruft diff --exit-code
    ],
)
def test_diff_has_diff(
    exit_code, isatty, expect_reproducible_diff, expected_return_value, capfd, tmpdir
):
    project_dir = scruft.create(
        TEST_COOKIECUTTER_REPO, Path(tmpdir), directory="dir", checkout="diff"
    )
    (project_dir / "file0").write_text("new content 0\n")
    (project_dir / "dir0/file1").write_text("new content 1\n")
    (project_dir / "dir0/file2").unlink()

    assert scruft.diff(project_dir, exit_code=exit_code) == expected_return_value

    captured = capfd.readouterr()
    stdout = captured.out
    stderr = captured.err

    assert stderr == ""

    expected_output = """diff --git upstream-template-old{tmpdir}/dir0/file1 upstream-template-new{tmpdir}/dir0/file1
index eaae237..ac3e272 100644
--- upstream-template-old{tmpdir}/dir0/file1
+++ upstream-template-new{tmpdir}/dir0/file1
@@ -1 +1 @@
-new content 1
+content1
diff --git upstream-template-old{tmpdir}/file0 upstream-template-new{tmpdir}/file0
index be6a56b..1fc03a9 100644
--- upstream-template-old{tmpdir}/file0
+++ upstream-template-new{tmpdir}/file0
@@ -1 +1 @@
-new content 0
+content0
"""
    expected_output_regex = re.escape(expected_output)
    expected_output_regex = expected_output_regex.replace(r"\{tmpdir\}", r"([^\n]*)")
    expected_output_regex = rf"^{expected_output_regex}$"

    match = re.search(expected_output_regex, stdout, re.MULTILINE)
    assert match is not None

    if expect_reproducible_diff:
        # If the output is not displayed to the user (for example when piping the result
        # of the "cruft diff" command) or if the user requested an exit code, we must make
        # sure the absolute path to the temporary directory does not appear in the diff
        # because the user might want to process the output.
        # Conversely, when the output is supposed to be displayed to the user directly (e.g.
        # when running "cruft diff" command directly in a terminal), absolute path to the
        # actual files on disk may be displayed because git diff command is called directly
        # without reprocessing by cruft. This delegates diff coloring and paging to git which
        # improves user experience. As far as I know, there is no way to ask git diff to not
        # display this path.
        assert set(match.groups()) == {""}


@pytest.mark.parametrize("exit_code", [(False,), (True,)])
def test_diff_no_diff(exit_code, capfd, tmpdir):
    project_dir = scruft.create(
        TEST_COOKIECUTTER_REPO, Path(tmpdir), directory="dir", checkout="diff"
    )

    assert scruft.diff(project_dir, exit_code=exit_code) is True

    captured = capfd.readouterr()
    stdout = captured.out
    stderr = captured.err

    assert stdout == ""
    assert stderr == ""


def test_diff_checkout(capfd, tmpdir):
    project_dir = scruft.create(
        TEST_COOKIECUTTER_REPO,
        Path(tmpdir),
        directory="dir",
        checkout="main",
    )

    assert scruft.diff(project_dir, exit_code=True, checkout="updated") is False

    captured = capfd.readouterr()
    stdout = captured.out
    stderr = captured.err

    assert stderr == ""
    assert "--- upstream-template-old/README.md" in stdout
    assert "+++ upstream-template-new/README.md" in stdout
    assert "+Updated again" in stdout
    assert "-Updated" in stdout


def test_diff_git_subdir(capfd, tmpdir):
    tmpdir.chdir()
    temp_dir = Path(tmpdir)
    Repo.clone_from(TEST_COOKIECUTTER_REPO, temp_dir)

    # Create something deeper in the git tree
    project_dir = scruft.create(
        TEST_COOKIECUTTER_REPO,
        Path("tmpdir/foo/bar"),
        directory="dir",
        checkout="main",
    )
    # not added & committed
    assert not scruft.update(project_dir)
    # Add & commit the changes so that the repo is clean
    run(["git", "add", "."], cwd=temp_dir)
    run(
        [
            "git",
            "-c",
            "user.name='test'",
            "-c",
            "user.email='user@test.com'",
            "commit",
            "-am",
            "test",
        ],
        cwd=temp_dir,
    )

    assert scruft.update(project_dir, checkout="updated")
