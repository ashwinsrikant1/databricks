# Claude Code Instructions

## Branch Management

When merging code from a feature branch into main:
1. After the merge is complete and pushed successfully
2. Automatically delete both the local and remote feature branch
3. Use `git branch -d <branch-name>` for local deletion
4. Use `git push origin --delete <branch-name>` for remote deletion
5. Only delete branches that have been fully merged into main

## General Development Preferences

- Always test functionality before committing code changes
- Use descriptive commit messages with the standard format
- Organize code into appropriate subdirectories based on functionality
- Remove credentials and sensitive information before committing
- Keep the repository clean by removing stale branches and unused files

## Code Organization

The project is organized into functional subdirectories under `databricks-utils/`:
- `compute/`: Cluster management utilities
- `dbsql/`: SQL execution utilities
- `etl/`: Pipeline and ETL operations
- `ai/`: AI and ML related components
- `unity_catalog/`: Unity Catalog tools and notebooks
- `infra/`: Infrastructure and deployment tools