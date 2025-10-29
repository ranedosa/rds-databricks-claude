---
description: Start daily work - ensures you're on the right branch or creates a new one for new features
---

# Daily Work Startup

You are helping the user start their daily work session. Follow this workflow:

## Step 1: Check Current Branch and Worktree

First, determine:
1. What branch are they currently on?
2. Are they in the main worktree or a feature worktree?
3. What's the status of their working directory?

Run these commands using the Bash tool:
```bash
git branch --show-current
git worktree list
git status
```

## Step 2: Ask About Today's Work

Based on the branch status, ask the user what they plan to work on today using the AskUserQuestion tool.

**If on `main` branch:**
Ask: "You're on the main branch. What would you like to work on today?"

**If on a feature branch:**
Ask: "You're on branch `{branch_name}`. Would you like to continue working on this feature, switch to another, or start something new?"

## Step 3: Present Available Options

List available worktrees and branches to help them decide.

Show the user:
1. **Existing worktrees** they can switch to
2. **Existing branches** they can checkout
3. **Option to create new feature** with new worktree

## Step 4: Take Action Based on User Choice

### Option A: Continue Current Work
- Verify branch is appropriate for the work
- Show last few commits: `git log --oneline -5`
- Confirm they're ready to continue

### Option B: Switch to Existing Worktree/Branch
- Show available worktrees: `git worktree list`
- Tell them which directory to `cd` to
- Or help them checkout existing branch

### Option C: Create New Feature Branch + Worktree
1. Ask for feature name using AskUserQuestion
2. Suggest branch name based on feature (e.g., `feature/audit-improvements`)
3. Suggest worktree directory name (e.g., `../rds_databricks_claude-audit`)
4. Create worktree:
   ```bash
   git worktree add -b {branch-name} {worktree-path}
   ```
5. Tell them to `cd` to new worktree

### Option D: Quick Work on Main
- Warn them: "Working directly on main is for small fixes only"
- Confirm they don't need a feature branch
- Proceed with caution

## Step 5: Verify Setup

Once branch is selected/created:
1. Show current branch: `git branch --show-current`
2. Show worktree location: `pwd`
3. Show working directory status: `git status`
4. Confirm they're ready to start

## Step 6: Summary

Provide a summary:
```
✓ Branch: {branch-name}
✓ Worktree: {worktree-location}
✓ Status: {working tree status}
✓ Ready to start work!
```

## Important Reminders

- **Never work directly on main** for features (only small fixes)
- **Always create feature branches** for new work
- **Use worktrees** for parallel development
- **Commit frequently** with clear messages
- **Keep main clean** and deployable

## Branch Naming Conventions

Suggest these naming patterns:
- `feature/{description}` - New features (e.g., feature/dlt-migration)
- `bugfix/{description}` - Bug fixes (e.g., bugfix/pk-validation)
- `hotfix/{description}` - Urgent production fixes
- `refactor/{description}` - Code refactoring
- `docs/{description}` - Documentation updates
- `test/{description}` - Testing improvements

## Worktree Naming Conventions

Suggest these directory patterns:
- `../rds_databricks_claude-{shortname}`
- Examples:
  - `../rds_databricks_claude-dlt` for DLT work
  - `../rds_databricks_claude-audit` for audit improvements
  - `../rds_databricks_claude-validation` for validation work
  - `../rds_databricks_claude-bugfix` for bug fixes
