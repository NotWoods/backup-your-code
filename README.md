# backup-your-code

Find project folders that aren't backed up to a git remote. Great to make
sure that everything is backed up before your computer crashes!

Based on the input glob `pattern`, find folders and filter it to
only folders with one of:

- No git repository
- No git remote
- Code not pushed to a remote

If no pattern is supplied, every git repository in the current working directory is searched.

Avaliable as both a function and as a command line tool!

## Usage

### Command line

```
usage: python backup_your_code.py [-h] [--pattern PATTERN] [--cwd CWD]

optional arguments:
  -h, --help         show this help message and exit
  --pattern PATTERN  glob pattern to find git repository folders
  --cwd CWD          directory to start searching from
```

### Module

`backup_your_code.py` is a single Python file with no dependencies (except that git should be installed on the computer).

The main export is the `backup_your_code` function, which yields tuples of `Path` objects and an enum.

```python
def backup_your_code(pattern: str = None, cwd: str = os.path.curdir) -> Iterable[NotBackedUp]
```

If git is not installed, a `GitNotInstalledError` is raised.

The yieled tuples are defined as a named tuple:

```python
NotBackedUp = namedtuple('NotBackedUp', ['path', 'reason'])
NotBackedUpReason = Enum('NotBackedUpReason', 'NO_REMOTE NOT_COMMITTED NOT_PUSHED')
```
