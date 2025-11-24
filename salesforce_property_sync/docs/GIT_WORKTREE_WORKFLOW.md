# Git Worktree Workflow

This project uses Git worktrees for efficient multi-branch development. This allows you to work on multiple branches simultaneously without switching contexts.

## What are Git Worktrees?

Git worktrees allow you to have multiple working directories (worktrees) attached to the same repository. Each worktree can have a different branch checked out, enabling you to:

- Work on multiple features simultaneously
- Run tests on one branch while developing on another
- Compare implementations across branches
- Avoid context switching overhead

**Reference**: [Anthropic Engineering - Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)

## Current Setup

Your project is now initialized as a git repository with the `main` branch.

```
/Users/danerosa/
└── rds_databricks_claude/          # Main repository (main branch)
```

## Recommended Worktree Structure

The recommended structure for using worktrees is:

```
/Users/danerosa/
├── rds_databricks_claude-main/     # Main development branch
├── rds_databricks_claude-feature/  # Feature branch worktree
├── rds_databricks_claude-bugfix/   # Bugfix branch worktree
└── rds_databricks_claude-test/     # Testing branch worktree
```

## Setting Up Worktrees

### Option 1: Start Fresh with Worktree Structure

If you want to reorganize to use worktrees from the start:

```bash
# Step 1: Rename current directory to indicate it's the main worktree
cd /Users/danerosa
mv rds_databricks_claude rds_databricks_claude-main

# Step 2: CD into the main worktree
cd rds_databricks_claude-main

# Step 3: Create a feature branch worktree
git worktree add ../rds_databricks_claude-feature feature/dlt-migration

# Step 4: List all worktrees
git worktree list
```

### Option 2: Add Worktrees as Needed

Keep the current directory as-is and add worktrees when needed:

```bash
# From the current directory
cd /Users/danerosa/rds_databricks_claude

# Create a feature branch worktree
git worktree add ../rds_databricks_claude-feature feature/dlt-migration

# Create a bugfix worktree
git worktree add ../rds_databricks_claude-bugfix bugfix/pk-validation

# List all worktrees
git worktree list
```

Output will look like:
```
/Users/danerosa/rds_databricks_claude              4c0cd6b [main]
/Users/danerosa/rds_databricks_claude-feature      2a3b4c5 [feature/dlt-migration]
/Users/danerosa/rds_databricks_claude-bugfix       1a2b3c4 [bugfix/pk-validation]
```

## Common Workflows

### Creating a New Feature Branch with Worktree

```bash
# Create a new branch and worktree in one command
git worktree add -b feature/audit-improvements ../rds_databricks_claude-audit feature/audit-improvements

# Or if branch already exists
git worktree add ../rds_databricks_claude-audit feature/audit-improvements
```

### Working in Multiple Worktrees

Open multiple terminal windows or IDE instances:

**Terminal 1** - Main development:
```bash
cd /Users/danerosa/rds_databricks_claude-main
# Work on main branch
```

**Terminal 2** - Feature work:
```bash
cd /Users/danerosa/rds_databricks_claude-feature
# Work on feature branch
```

**Terminal 3** - Running tests:
```bash
cd /Users/danerosa/rds_databricks_claude-test
# Run tests without interrupting other work
```

### Using Claude Code with Worktrees

Open Claude Code in each worktree directory:

```bash
# Terminal 1
cd /Users/danerosa/rds_databricks_claude-main
claude-code

# Terminal 2
cd /Users/danerosa/rds_databricks_claude-feature
claude-code
```

Each instance works independently with its own branch!

### Switching Context

Instead of `git checkout`, just switch directories:

```bash
# Old way (without worktrees)
git checkout feature/new-feature

# New way (with worktrees)
cd ../rds_databricks_claude-feature
```

## Managing Worktrees

### List All Worktrees

```bash
git worktree list
```

Output:
```
/Users/danerosa/rds_databricks_claude              4c0cd6b [main]
/Users/danerosa/rds_databricks_claude-feature      2a3b4c5 [feature/dlt-migration]
/Users/danerosa/rds_databricks_claude-bugfix       1a2b3c4 [bugfix/pk-validation]
```

### Remove a Worktree

When you're done with a feature:

```bash
# Step 1: Remove the worktree
git worktree remove ../rds_databricks_claude-feature

# Step 2: Delete the branch (if merged)
git branch -d feature/dlt-migration
```

Or manually:
```bash
# Remove directory
rm -rf ../rds_databricks_claude-feature

# Prune worktree info
git worktree prune
```

### Move a Worktree

```bash
# Move the directory
mv ../rds_databricks_claude-feature ../rds_databricks_claude-new-location

# Update git's record
git worktree repair ../rds_databricks_claude-new-location
```

## Best Practices for This Project

### 1. Share Config Across Worktrees

The `config/` directory contains credentials that should be shared across all worktrees. Create a shared config:

```bash
# In your main worktree
cd /Users/danerosa/rds_databricks_claude-main

# Create a shared config directory
mkdir -p ~/.databricks_shared_config

# Move config files to shared location
cp config/.env ~/.databricks_shared_config/
cp config/.databrickscfg ~/.databricks_shared_config/

# In each worktree, symlink to shared config
cd /Users/danerosa/rds_databricks_claude-feature
ln -s ~/.databricks_shared_config config
```

**Or** use environment variables:
```bash
# In your shell profile (~/.zshrc or ~/.bashrc)
export DATABRICKS_CONFIG_DIR="$HOME/.databricks_shared_config"
```

### 2. Gitignore is Shared

The `.gitignore` file is part of the repository, so all worktrees share the same ignore rules. This means:
- `config/` is protected in all worktrees
- `results/` is ignored in all worktrees
- No need to duplicate security settings

### 3. Virtual Environments

Each worktree can have its own virtual environment:

```bash
# In each worktree
cd /Users/danerosa/rds_databricks_claude-feature
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Or share a virtual environment:
```bash
# Create shared venv
python3 -m venv ~/.venv-rds-databricks
source ~/.venv-rds-databricks/bin/activate
pip install -r requirements.txt

# Use in all worktrees
cd /Users/danerosa/rds_databricks_claude-feature
source ~/.venv-rds-databricks/bin/activate
```

### 4. Branch Naming Convention

Use descriptive branch names that match worktree directories:

| Worktree Directory | Branch Name | Purpose |
|-------------------|-------------|---------|
| `rds_databricks_claude-main` | `main` | Main development |
| `rds_databricks_claude-dlt-migration` | `feature/dlt-migration` | DLT migration work |
| `rds_databricks_claude-audit` | `feature/audit-improvements` | Audit tool improvements |
| `rds_databricks_claude-bugfix-pk` | `bugfix/pk-validation` | Fix PK validation |
| `rds_databricks_claude-hotfix` | `hotfix/critical-fix` | Production hotfix |

### 5. Commit from Any Worktree

All worktrees share the same git history:

```bash
# In worktree 1
cd /Users/danerosa/rds_databricks_claude-feature
git commit -m "Add new feature"
git push origin feature/dlt-migration

# In worktree 2 (main)
cd /Users/danerosa/rds_databricks_claude-main
git fetch origin
git merge origin/feature/dlt-migration
```

## Example: DLT Migration Workflow

Here's a complete workflow for the DLT migration project:

### Step 1: Set Up Worktrees

```bash
cd /Users/danerosa/rds_databricks_claude

# Create worktrees for different phases
git worktree add -b feature/dlt-fde-pipeline ../rds_databricks_claude-dlt-fde
git worktree add -b feature/dlt-validation ../rds_databricks_claude-dlt-validation
git worktree add -b feature/dlt-testing ../rds_databricks_claude-dlt-testing
```

### Step 2: Work in Parallel

**Terminal 1** - Develop pipeline:
```bash
cd /Users/danerosa/rds_databricks_claude-dlt-fde
# Edit scripts/pipeline/dlt_fde_pipeline.py
git add .
git commit -m "Update FDE pipeline logic"
```

**Terminal 2** - Run validation:
```bash
cd /Users/danerosa/rds_databricks_claude-dlt-validation
python scripts/validation/check_table_stats.py
# Validation runs while you continue development in Terminal 1
```

**Terminal 3** - Run tests:
```bash
cd /Users/danerosa/rds_databricks_claude-dlt-testing
python scripts/testing/test_pk_consistency.py
```

### Step 3: Merge When Ready

```bash
cd /Users/danerosa/rds_databricks_claude-main
git merge feature/dlt-fde-pipeline
git merge feature/dlt-validation
git push origin main
```

### Step 4: Clean Up

```bash
git worktree remove ../rds_databricks_claude-dlt-fde
git worktree remove ../rds_databricks_claude-dlt-validation
git branch -d feature/dlt-fde-pipeline
git branch -d feature/dlt-validation
```

## Troubleshooting

### Error: "fatal: 'branch' is already checked out at 'path'"

You cannot check out the same branch in multiple worktrees simultaneously. Each worktree must have a different branch.

**Solution**: Create a new branch or use a different existing branch.

### Worktree Shows as "broken"

```bash
git worktree list
# Shows: /path/to/worktree (broken)
```

**Solution**:
```bash
# If directory was deleted
git worktree prune

# If directory was moved
git worktree repair /new/path
```

### Can't Remove Worktree

```bash
git worktree remove path/to/worktree
# Error: "fatal: validation failed, cannot remove working tree"
```

**Solution**:
```bash
# Force remove
git worktree remove --force path/to/worktree

# Or manually
rm -rf path/to/worktree
git worktree prune
```

### Config Files Not Working in New Worktree

Remember that `config/` is gitignored, so it won't be present in new worktrees.

**Solution**: Use symlinks or environment variables (see Best Practices #1)

## Advantages of Worktrees for This Project

1. **Parallel Development**: Work on migration and validation simultaneously
2. **Context Preservation**: Keep your editor, terminal, and Claude Code state for each task
3. **Easy Testing**: Run tests in one worktree while developing in another
4. **Branch Comparison**: Easily compare implementations side-by-side
5. **Reduced Risk**: Test risky changes in a separate worktree without affecting main work

## Resources

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Anthropic Engineering - Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Git Worktree Tutorial](https://opensource.com/article/21/4/git-worktree)

## Quick Reference

```bash
# Create worktree
git worktree add <path> <branch>

# Create worktree with new branch
git worktree add -b <new-branch> <path>

# List worktrees
git worktree list

# Remove worktree
git worktree remove <path>

# Prune deleted worktrees
git worktree prune

# Repair moved worktree
git worktree repair <path>

# Lock a worktree (prevent removal)
git worktree lock <path>

# Unlock a worktree
git worktree unlock <path>
```

---

**Document Version**: 1.0
**Last Updated**: 2024-10-29
**See Also**: README.md, docs/PROJECT_STRUCTURE.md
