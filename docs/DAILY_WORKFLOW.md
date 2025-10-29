# Daily Development Workflow

This document describes the recommended daily workflow for working on this project, ensuring you always work on the appropriate branch.

## Core Principle

**Never work directly on `main` for features.** Always use feature branches and worktrees for organized, safe development.

## Starting Your Day

You have two options to start your daily work:

### Option 1: Use Claude Code Slash Command (Recommended)

Simply type in Claude Code:

```
/start-work
```

Claude will:
1. Check your current branch and worktree
2. Ask what you want to work on today
3. Help you switch to existing work or create a new feature branch
4. Verify your setup before you start

### Option 2: Use the Shell Script

Run the interactive helper script:

```bash
./start-day.sh
```

This will:
- Show your current branch and available worktrees
- Let you choose to continue, switch, or create new work
- Provide clear instructions for next steps

## Decision Tree

```
Start of Day
│
├─ On main branch?
│  │
│  ├─ Quick fix/docs? → Continue on main (commit and merge quickly)
│  │
│  └─ New feature? → Create feature branch + worktree
│
├─ On feature branch?
│  │
│  ├─ Continue that feature? → Continue on current branch
│  │
│  ├─ Different feature? → Switch to another worktree
│  │
│  └─ New feature? → Create new feature branch + worktree
│
└─ Need to work on multiple things?
   └─ Create multiple worktrees (parallel work)
```

## Branch Naming Conventions

Follow these patterns for consistency:

| Type | Pattern | Example | Use Case |
|------|---------|---------|----------|
| Feature | `feature/{description}` | `feature/dlt-migration` | New features or enhancements |
| Bugfix | `bugfix/{description}` | `bugfix/pk-validation` | Bug fixes |
| Hotfix | `hotfix/{description}` | `hotfix/critical-data-loss` | Urgent production fixes |
| Refactor | `refactor/{description}` | `refactor/audit-scripts` | Code refactoring |
| Docs | `docs/{description}` | `docs/api-documentation` | Documentation updates |
| Test | `test/{description}` | `test/validation-suite` | Testing improvements |

## Worktree Naming Conventions

Match worktree directory names to branch purpose:

| Branch | Worktree Directory | Description |
|--------|-------------------|-------------|
| `feature/dlt-migration` | `../rds_databricks_claude-dlt` | DLT migration work |
| `feature/audit-improvements` | `../rds_databricks_claude-audit` | Audit tool improvements |
| `bugfix/pk-validation` | `../rds_databricks_claude-bugfix` | Bug fix work |
| `test/validation-suite` | `../rds_databricks_claude-test` | Testing work |

## Common Scenarios

### Scenario 1: Starting a New Feature

```bash
# Using /start-work in Claude Code
/start-work
# Choose option 3: Create new feature

# Or manually:
git worktree add -b feature/my-feature ../rds_databricks_claude-myfeature
cd ../rds_databricks_claude-myfeature
# Start coding!
```

### Scenario 2: Continuing Yesterday's Work

```bash
# Using /start-work in Claude Code
/start-work
# Choose option 1: Continue on current branch

# Or check status:
git branch --show-current
git status
# Continue working
```

### Scenario 3: Switching Between Features

```bash
# Using /start-work in Claude Code
/start-work
# Choose option 2: Switch to existing worktree

# Or manually:
git worktree list
cd ../rds_databricks_claude-other-feature
```

### Scenario 4: Parallel Work on Multiple Features

```bash
# Create multiple worktrees
git worktree add -b feature/dlt-pipeline ../rds_databricks_claude-dlt
git worktree add -b feature/validation ../rds_databricks_claude-validation

# Terminal 1: Work on DLT
cd ../rds_databricks_claude-dlt
# Edit pipeline code

# Terminal 2: Run validation
cd ../rds_databricks_claude-validation
# Run validation scripts
```

### Scenario 5: Quick Fix on Main

```bash
# Only for small, quick fixes!
git branch --show-current  # Should show: main
# Make small fix
git add .
git commit -m "Quick fix: ..."
git push
```

## Daily Checklist

Use this checklist at the start of each day:

- [ ] Run `/start-work` in Claude Code or `./start-day.sh`
- [ ] Verify you're on the right branch for today's work
- [ ] Check `git status` for any uncommitted changes
- [ ] Review recent commits: `git log --oneline -5`
- [ ] If starting new feature, create feature branch + worktree
- [ ] If continuing, verify branch name matches your work

## End of Day Checklist

Before finishing for the day:

- [ ] Commit your changes: `git add . && git commit -m "..."`
- [ ] Push to remote: `git push origin {branch-name}`
- [ ] Note which branch you're on for tomorrow
- [ ] If feature is complete, merge to main

## Workflow Rules

### ✅ DO

- **Always** use feature branches for new features
- **Always** commit frequently with clear messages
- **Always** push your branches to remote for backup
- **Use** worktrees for parallel development
- **Keep** main branch clean and deployable
- **Review** your work before merging to main

### ❌ DON'T

- **Don't** work directly on main for features (only quick fixes)
- **Don't** commit directly to main without review
- **Don't** leave uncommitted changes overnight
- **Don't** forget to push your branches
- **Don't** create branches without descriptive names
- **Don't** forget which branch you're on

## Merging Back to Main

When your feature is complete:

```bash
# 1. Make sure feature branch is clean
git status

# 2. Go back to main worktree
cd /Users/danerosa/rds_databricks_claude  # or rds_databricks_claude-main

# 3. Update main
git checkout main
git pull origin main

# 4. Merge feature
git merge feature/your-feature

# 5. Push to remote
git push origin main

# 6. Clean up worktree (optional)
git worktree remove ../rds_databricks_claude-yourfeature
git branch -d feature/your-feature
```

## Troubleshooting

### "I forgot which branch I'm on"

```bash
git branch --show-current
```

### "I have uncommitted changes"

```bash
git status  # See what changed
git add .   # Stage changes
git commit -m "WIP: describe changes"  # Commit them
```

### "I'm on main but started coding a feature"

```bash
# Don't panic! Create a branch from current state
git checkout -b feature/my-feature
# Now you're on a feature branch with your changes
```

### "I can't remember which worktree has which feature"

```bash
git worktree list
# Shows all worktrees with their branches
```

## Integration with Claude Code

When starting a Claude Code session:

1. Type `/start-work` to begin
2. Claude will guide you through branch selection
3. Continue with your work
4. Claude will remind you to work on appropriate branches

## Benefits of This Workflow

- **Organized**: Always know which branch is for which feature
- **Safe**: Main branch stays clean and deployable
- **Efficient**: Work on multiple features in parallel
- **Collaborative**: Easy to share feature branches
- **Professional**: Industry-standard git workflow
- **Recoverable**: Easy to rollback or abandon features

## Examples from This Project

### Example 1: DLT Migration Feature

```bash
# Day 1: Start DLT migration
git worktree add -b feature/dlt-migration ../rds_databricks_claude-dlt
cd ../rds_databricks_claude-dlt
# Work on pipeline code...
git commit -m "Initial DLT pipeline structure"
git push origin feature/dlt-migration

# Day 2: Continue DLT migration
cd ../rds_databricks_claude-dlt
git pull origin feature/dlt-migration
# Continue working...
```

### Example 2: Parallel Audit and Validation Work

```bash
# Create two worktrees
git worktree add -b feature/audit-improvements ../rds_databricks_claude-audit
git worktree add -b feature/validation-suite ../rds_databricks_claude-validation

# Terminal 1: Improve audit scripts
cd ../rds_databricks_claude-audit
# Edit scripts/audit/*.py

# Terminal 2: Build validation suite
cd ../rds_databricks_claude-validation
# Edit scripts/validation/*.py

# Both get merged when ready
```

## Resources

- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree)
- [Project Git Worktree Workflow](GIT_WORKTREE_WORKFLOW.md)
- [Anthropic Engineering Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)

---

**Remember**: The `/start-work` command in Claude Code automates this entire workflow. Just type it at the start of each session!

**Document Version**: 1.0
**Last Updated**: 2024-10-29
