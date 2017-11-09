import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from subprocess import run, PIPE
if os.name == 'nt':
    from stat import FILE_ATTRIBUTE_HIDDEN, FILE_ATTRIBUTE_SYSTEM


class GitNotInstalledError(Exception):
    """Raised if git is not a recognized command."""
    pass


def _folder_is_valid(folder):
    if not folder.is_dir():
        return False
    if os.name == 'nt':
        attrs = folder.stat().st_file_attributes
        hidden = attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    else:
        hidden = str(folder).startswith('.')  # linux-os
    return not hidden


def _has_remote(folder):
    process = run(
        ['git', 'remote'],
        stdout=PIPE,
        stderr=PIPE,
        cwd=str(folder),
        encoding='utf-8'
    )

    if process.returncode:
        if process.returncode == 127:
            raise GitNotInstalledError()
        return False

    return process.stdout and not process.stdout.isspace()


def find_code_missing_backups(pattern, cwd='.'):
    """Return an iterable of paths that have no git remote.

    Gets folders from the input glob pattern, and only returns those
    that are missing a git remote or are not git repositories.
    """
    if not pattern.endswith('/'):
        pattern += '/'

    folders = Path(cwd).glob(pattern)
    return (
        folder for folder in folders
        if _folder_is_valid(folder) and not _has_remote(folder)
    )


if __name__ == '__main__':
    description = "Find project folders that aren\'t backed up to a git remote"

    parser = ArgumentParser(description=description)
    parser.add_argument(
        'pattern',
        metavar='pattern',
        help='glob pattern to find project folders',
    )

    args = parser.parse_args()

    try:
        folders = find_code_missing_backups(args.pattern)
        for folder in folders:
            print(folder)
    except GitNotInstalledError:
        print('Could not use git, is it installed?', file=sys.stdout)
        sys.exit(1)
