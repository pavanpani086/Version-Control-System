# MiniVCS - Python Version Control System

MiniVCS is a lightweight version control system built from scratch in Python for an Operating Systems project.

## Features

- Repository initialization
- Add files to staging area
- Commit snapshots
- View status
- View commit log
- See diffs
- Create and list branches
- Checkout branches or specific commits
- Merge branches with fast-forward and conflict detection
- Restore a file from staging
- Tag commits
- Remove tracked files

## Project Structure

```text
minivcs_project/
├── main.py
├── requirements.txt
├── README.md
├── demo_script.txt
├── report_outline.md
├── minivcs/
│   ├── __init__.py
│   ├── cli.py
│   ├── repo.py
│   └── utils.py
└── tests/
    └── test_flow.py
```

## How It Works

MiniVCS stores repository data inside a hidden `.minivcs/` folder.

- `objects/` stores file contents using SHA-1 hashes
- `index.json` is the staging area
- `commits.json` stores commit metadata and file trees
- `refs/heads/` stores branches
- `refs/tags/` stores tags
- `HEAD` points to the current branch or detached commit
- `MERGE_HEAD` is created while a merge is in progress

Each commit saves a full snapshot of tracked files using blob hashes. Merge commits store the current branch parent and a second merge parent.

## Requirements

- Python 3.10+
- No extra packages needed

## Run

```bash
python main.py init
python main.py config "Your Name" "you@example.com"
python main.py status
```

## Example Workflow

```bash
python main.py init
python main.py config "Tharun" "tharun@example.com"
echo "hello" > notes.txt
python main.py add notes.txt
python main.py commit -m "first commit"
python main.py log
python main.py status
```

## Commands

### 1. Initialize repository
```bash
python main.py init
```

### 2. Configure author
```bash
python main.py config "Your Name" "you@example.com"
```

### 3. Add files
```bash
python main.py add file1.txt folder1
```

### 4. Commit staged files
```bash
python main.py commit -m "commit message"
```

### 5. Check status
```bash
python main.py status
```

### 6. Show commit log
```bash
python main.py log
```

### 7. Diff working tree vs staging
```bash
python main.py diff
```

### 8. Diff staging vs last commit
```bash
python main.py diff --staged
```

### 9. Create or list branches
```bash
python main.py branch feature1
python main.py branch
```

### 10. Checkout branch or commit
```bash
python main.py checkout feature1
python main.py checkout <commit_id>
```

### 11. Merge branch into current branch
```bash
python main.py merge feature1
```

### 12. Restore a file from staging
```bash
python main.py restore notes.txt
```

### 13. Remove tracked file
```bash
python main.py rm notes.txt
python main.py rm notes.txt --keep
```

### 14. Tag commits
```bash
python main.py tag v1.0
python main.py tag --list
```

### 15. Show commit details
```bash
python main.py show <commit_id>
```

## Merge Behavior

MiniVCS supports three important merge cases.

### Fast-forward merge
If the current branch has not moved ahead of the target branch, MiniVCS simply moves the current branch pointer forward.

### Automatic merge
If both branches changed different files or one branch changed a file while the other kept the base version, MiniVCS builds a merged tree automatically and creates a merge commit.

### Merge conflict
If both branches changed the same file differently after the common ancestor, MiniVCS writes conflict markers into the working file:

```text
<<<<<<< HEAD
current branch content
=======
incoming branch content
>>>>>>> feature1
```

Then you resolve the file manually, run `add`, and create the final commit.





## Limitations

- No remote repositories
- Optimized mainly for text files
- Uses full snapshots, not delta storage
- Conflict resolution is manual

## Future Improvements

- Three-way merge with smarter line-level merging
- Rebase
- Compression for object storage
- Binary diff support
- Ignore file patterns
- Remote push/pull support
