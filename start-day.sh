#!/bin/bash

# Daily Work Startup Script
# Helps you get on the right branch for today's work

set -e

echo "=== Daily Work Startup ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${BLUE}Current branch:${NC} ${GREEN}${CURRENT_BRANCH}${NC}"
echo ""

# Show worktrees
echo -e "${BLUE}Available worktrees:${NC}"
git worktree list
echo ""

# Show all branches
echo -e "${BLUE}Available branches:${NC}"
git branch -a | grep -v "remotes/" | sed 's/^[* ]*/  /'
echo ""

# Check working tree status
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    git status --short
    echo ""
fi

# Ask user what they want to do
echo -e "${BLUE}What would you like to do today?${NC}"
echo ""
echo "  1) Continue on current branch (${CURRENT_BRANCH})"
echo "  2) Switch to existing worktree"
echo "  3) Create new feature branch + worktree"
echo "  4) Switch to different branch (same worktree)"
echo "  5) Just show me the status and exit"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}✓ Continuing on branch: ${CURRENT_BRANCH}${NC}"
        echo ""
        echo "Recent commits:"
        git log --oneline -5
        echo ""
        echo -e "${GREEN}Ready to work!${NC}"
        ;;
    2)
        echo ""
        echo -e "${BLUE}Available worktrees:${NC}"
        git worktree list | nl
        echo ""
        read -p "Which worktree? (enter path): " worktree_path
        if [ -d "$worktree_path" ]; then
            echo ""
            echo -e "${GREEN}Switch to worktree:${NC} cd $worktree_path"
            echo ""
            echo "Run this command to switch:"
            echo -e "${YELLOW}cd $worktree_path${NC}"
        else
            echo -e "${RED}Error: Worktree not found${NC}"
            exit 1
        fi
        ;;
    3)
        echo ""
        read -p "Feature name (e.g., 'audit improvements'): " feature_name
        # Convert to branch name
        branch_name="feature/$(echo $feature_name | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
        # Convert to worktree name
        worktree_name="$(echo $feature_name | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
        worktree_path="../rds_databricks_claude-${worktree_name}"

        echo ""
        echo -e "${BLUE}Suggested names:${NC}"
        echo "  Branch: ${branch_name}"
        echo "  Worktree: ${worktree_path}"
        echo ""
        read -p "Proceed with these names? (y/n): " confirm

        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo ""
            echo "Creating worktree..."
            git worktree add -b "$branch_name" "$worktree_path"
            echo ""
            echo -e "${GREEN}✓ Worktree created!${NC}"
            echo ""
            echo "Switch to new worktree:"
            echo -e "${YELLOW}cd $worktree_path${NC}"
        else
            echo "Cancelled"
        fi
        ;;
    4)
        echo ""
        echo -e "${BLUE}Available branches:${NC}"
        git branch | nl
        echo ""
        read -p "Branch name: " branch_name
        git checkout "$branch_name"
        echo ""
        echo -e "${GREEN}✓ Switched to branch: ${branch_name}${NC}"
        ;;
    5)
        echo ""
        echo -e "${GREEN}Current status:${NC}"
        echo ""
        echo "Branch: ${CURRENT_BRANCH}"
        echo "Location: $(pwd)"
        git status
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== Ready to start work! ===${NC}"
