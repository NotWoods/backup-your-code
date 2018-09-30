import os
import subprocess
from enum import Enum
from pathlib import Path
from shutil import which
from typing import Iterable, NamedTuple, Optional
if os.name == 'nt':
    from stat import FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_SYSTEM


NotBackedUpReason = Enum('NotBackedUpReason',
                         'NO_REMOTE NOT_COMMITTED NOT_PUSHED')


class NotBackedUp(NamedTuple):
    path: Path
    reason: NotBackedUpReason

    def __str__(self):
        if self.reason == NotBackedUpReason.NO_REMOTE:
            reason_str = 'No remotes in git repository'
        elif self.reason == NotBackedUpReason.NOT_COMMITTED:
            reason_str = 'Some code is not yet comitted'
        elif self.reason == NotBackedUpReason.NOT_PUSHED:
            reason_str = 'Some code is not pushed to a remote'

        return f'{self.path}: {reason_str}.'


class GitNotInstalledError(Exception):
    """Raised if git is not a recognized command."""
    pass


def backup_your_code(pattern: str = None, cwd: str = os.path.curdir) -> Iterable[NotBackedUp]:
    """Return iterable of paths that don't have code pushed to a git remote.

    Based on the input glob |pattern|, find folders and filter it to
    only folders with one of:
        - No git repository
        - No git remote
        - Code not pushed to a remote

    If no pattern is supplied, every git repository in |cwd| is searched.

    :param pattern: Glob pattern of folders to check, relative to |cwd|.
    :param cwd: Current working directory, used as base folder for |pattern|.
    :raises GitNotInstalledError: Raises error if git is not found.
    """
    # Check that git is installed
    if which('git') is None:
        raise GitNotInstalledError()

    # List all desired folders
    if pattern is not None:
        # Ensure pattern checks for folders only
        if not pattern.endswith('/'):
            pattern += '/'
        folders = Path(cwd).expanduser().glob(pattern)
    else:
        folders = _all_git_repo_folders(cwd)

    # Filter out the folders
    for repo in folders:
        # Make sure glob yieled actual directories
        if _is_valid_folder(repo):
            # Check conditions for repo
            reason = None
            remotes = _list_remotes(repo)
            if not remotes:
                reason = NotBackedUpReason.NO_REMOTE
            elif not _all_code_comitted(repo):
                reason = NotBackedUpReason.NOT_COMMITTED
            else:
                branch = _current_branch(repo)
                if not any(_code_pushed_to(r, repo, branch) for r in remotes):
                    reason = NotBackedUpReason.NOT_PUSHED

            if reason is not None:
                yield NotBackedUp(repo, reason)


def _all_git_repo_folders(root_path: str) -> Iterable[Path]:
    """Yield all git repositories in |root_path|."""
    git_folders = Path(root_path).expanduser().glob('**/.git/')
    while True:
        try:
            folder = next(git_folders)
            yield folder.parent
        except StopIteration:
            return
        except FileNotFoundError:
            pass  # Sometimes git_folders fails to open a directory


def _is_valid_folder(folder: Path) -> bool:
    """Return true if |folder| points to a not-hidden directory.

    :param folder: Path object potentially pointing to folder.
    """
    # Check if path points to a directory
    if not folder.is_dir():
        return False
    # Check that the folder isn't hidden
    if os.name == 'nt':
        # Check if folder is hidden on Windows
        attrs = folder.stat().st_file_attributes
        hidden = attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    else:
        # Check if folder is hidden on Unix
        hidden = str(folder).startswith('.')  # linux-os
    return not hidden


def _run_git_command(*args: str, cwd: Path):
    return subprocess.run(
        ['git', *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd),
        encoding='utf-8'
    )


def _all_code_comitted(repo_path: Path) -> bool:
    """Check that all files in a repository are comitted.

    Runs the `git status --short` command in the given path,
    then checks to see if any added/removed/modifed files are returned.
    If an error is thrown by the command, False is returned.

    :param repo_path: Path object or string representing path to git repo.
    """
    process = _run_git_command('status', '--short', cwd=repo_path)

    if process.returncode:
        return False
    else:
        return process.stdout is not None and process.stdout.isspace()


def _list_remotes(repo_path: Path) -> Iterable[str]:
    """Check that all commits in a repository are pushed.

    :param repo_path: Path object or string representing path to git repo.
    """
    process = _run_git_command('remote', cwd=repo_path)
    if process.returncode:
        return []
    remotes = process.stdout.split('\n') if process.stdout else []
    return (s.strip() for s in remotes if not s.isspace())


def _current_branch(repo_path: Path) -> Optional[str]:
    """Return the current branch of a git repostory.

    :param repo_path: Path object or string representing path to git repo.
    """
    process = _run_git_command('branch', cwd=repo_path)
    if process.returncode:
        return None
    branches = process.stdout.split('\n') if process.stdout else []
    try:
        # Get the first string that starts with `*`
        current_branch = next(b for b in branches if b.startswith('*'))
        return current_branch[1:].trim()  # Remove * character from string
    except StopIteration:
        return None


def _code_pushed_to(remote: str, repo: Path, branch: Optional[str]) -> bool:
    """Check that all commits in a branch are pushed to a git remote.

    Runs the `git log {remote}/{branch}..{branch}` command in the given path,
    then checks to see if any added/removed/modifed files are returned.
    If an error is thrown by the command, False is returned.

    :param remote: Name of the remote to check against.
    :param repo: Path object or string representing path to git repo.
    :param branch: Branch to check.
    """
    if not branch:
        return False
    process = _run_git_command('log', f'{remote}/{branch}..{branch}', cwd=repo)
    if process.returncode:
        return False
    else:
        return process.stdout is not None and process.stdout.isspace()


if __name__ == '__main__':
    import sys
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Find project folders that aren't backed up to a git remote")
    parser.add_argument('--pattern',
                        help='glob pattern to find git repository folders')
    parser.add_argument('--cwd',
                        help='directory to start searching from')

    args = parser.parse_args()

    try:
        for folder in backup_your_code(pattern=args.pattern, cwd=args.cwd):
            print(folder)
    except GitNotInstalledError:
        print('Could not use git, is it installed?', file=sys.stdout)
        sys.exit(1)
