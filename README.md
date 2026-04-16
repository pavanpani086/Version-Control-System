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
Creates the hidden `.minivcs` folder and sets up the repository structure.  
Use this first in any folder where you want MiniVCS to start tracking files.

---

### 2. Configure author
```bash
python main.py config "Your Name" "you@example.com"
```
Stores the username and email that will be attached to commits.  
Use this so every commit records who created it.

---

### 3. Add files
```bash
python main.py add file1.txt folder1
```
Copies file information into the staging area and stores content as objects.  
Use this to select which files should be included in the next commit.

---

### 4. Commit staged files
```bash
python main.py commit -m "commit message"
```
Creates a new snapshot from all currently staged files and saves commit metadata.  
Use this to permanently record a version of your project with a message.

---

### 5. Check status
```bash
python main.py status
```
Shows the current state of the working directory, staging area, and tracked files.  
Use this to see which files are staged, modified, deleted, or untracked.

---

### 6. Show commit log
```bash
python main.py log
```
Displays commit history from latest to oldest by following parent links.  
Use this to review previous commits and understand project history.

---

### 7. Diff working tree vs staging
```bash
python main.py diff
```
Shows differences between the current file contents and the staged version.  
Use this before adding files to check what has changed locally.

---

### 8. Diff staging vs last commit
```bash
python main.py diff --staged
```
Shows differences between staged files and the most recent commit snapshot.  
Use this to verify exactly what will be committed next.

---

### 9. Create or list branches
```bash
python main.py branch feature1
python main.py branch
```
Creates a new branch pointing to the current commit or lists existing branches.  
Use branches to work on new features without affecting the main branch immediately.

---

### 10. Checkout branch or commit
```bash
python main.py checkout feature1
python main.py checkout <commit_id>
```
Switches the working directory to match a selected branch or a specific commit.  
Use this to move between branches or inspect an older project version.

---

### 11. Merge branch into current branch
```bash
python main.py merge feature1
```
Combines changes from another branch into the branch you are currently on.  
Use this to bring completed feature work back into `main` or another branch.

---

### 12. Restore a file from staging
```bash
python main.py restore notes.txt
```
Replaces the current file with its stored tracked version from the repository state.  
Use this to discard unwanted local changes in a file.

---

### 13. Remove tracked file
```bash
python main.py rm notes.txt
python main.py rm notes.txt --keep
```
Removes a file from version control, and optionally also removes it from disk.  
Use `--keep` when you want to stop tracking the file but still keep it locally.

---

### 14. Tag commits
```bash
python main.py tag v1.0
python main.py tag --list
```
Creates a readable label for a commit and can list all existing tags.  
Use tags to mark important versions such as releases or milestones.

---
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
