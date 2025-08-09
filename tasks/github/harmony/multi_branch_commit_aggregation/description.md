I need you to create a comprehensive commit history report by aggregating changes from multiple branches. Here's what you need to do:

**Step 1: Create Analysis Branch**
Create a new branch called 'history-report-2025' from the main branch.

**Step 2: Generate Branch Commits Report**
In the 'history-report-2025' branch, create a file called `BRANCH_COMMITS.json` that contains a JSON object with the following structure:
- For each of these branches: ['main', 'pr/25-neuralsorcerer-patch-1', 'pr/41-amirhosseinghanipour-fix-race-conditions-and-offline-api']
- List the 3 most recent commits for each branch
- Each commit must include: SHA, author login, commit message, and files changed count
- The JSON structure should be:
```json
{
  "main": [
    {
      "sha": "commit_sha",
      "author": "github_username",
      "message": "commit message",
      "files_changed": number
    }
  ],
  "pr/25-neuralsorcerer-patch-1": [...],
  "pr/41-amirhosseinghanipour-fix-race-conditions-and-offline-api": [...]
}
```

**Step 3: Create Cross-Branch Analysis**
Create a file `CROSS_BRANCH_ANALYSIS.md` that contains:
- A section "## Unique Contributors" listing all unique contributors across ALL 7 branches with their GitHub usernames
- A section "## Commit Statistics" showing the total number of commits across all 7 branches
- A section "## Files Modified in Multiple Branches" identifying which files have been modified in more than one branch
- Must include keywords: "contributors", "total commits", "modified across branches"

**Step 4: Generate Merge Timeline**
Create a file `MERGE_TIMELINE.txt` that lists all merge commits from the main branch:
- Format: `DATE | MERGE_COMMIT_MESSAGE | COMMIT_SHA`
- List in reverse chronological order (newest first)
- Only include actual merge commits (commits that have exactly 2 parent commits)
- Note: While the commit messages reference PR numbers, those PRs no longer exist in the repository

**Step 5: Create Pull Request**
Create a pull request from 'history-report-2025' to main with:
- Title: `Cross-Branch Commit Analysis Report`
- Body must contain exactly these lines:
  - `Total branches analyzed: 7`
  - `Total unique contributors: [COUNT]` (replace [COUNT] with actual number)
  - `Most modified file: [FILENAME]` (replace [FILENAME] with the file modified most across branches)