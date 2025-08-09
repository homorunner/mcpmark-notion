I need you to implement a comprehensive label color standardization workflow for the mcpleague-eval/claude-code repository, which currently has many labels using the default gray color (#ededed).

**Step 1: Create Label Color Documentation Issue**
Create a new issue with:
- Title containing: "Standardize label colors for better visual organization" and "color scheme"
- Body must include:
  - A "## Problem" heading describing the current state where many labels use default gray (#ededed)
  - A "## Proposed Solution" heading about implementing a color scheme for different label categories
  - A "## Benefits" heading listing improved visual organization and easier issue triage
  - Keywords: "label colors", "visual organization", "gray labels", "color standardization", "#ededed"
- Labels: Initially add "enhancement" and "documentation" labels to the issue

**Step 2: Create Feature Branch**
Create a new branch called 'feat/label-color-guide' from main.

**Step 3: Create Label Color Documentation**
On the feature branch, create the file `docs/LABEL_COLORS.md` with:
- A "# Label Color Standardization Guide" title
- A "## Color Scheme" section with a table that MUST follow this exact format:
```markdown
| Label Name | Category | Color Hex | Description |
|------------|----------|-----------|-------------|
```
The table must include ALL existing labels in the repository. For each label:
- Assign a non-gray color (anything except #ededed)
- Group labels by category (e.g., issue-type, platform, area, status, performance)
- Ensure each category uses a distinct color palette
- Include a description for each label

- A "## Implementation Status" section documenting which labels have been updated from gray
- A "## Usage Guidelines" section explaining when to use each label category

**Step 4: Update All Gray Labels**
For each label currently using the gray color (#ededed):
1. Look up the label in your documentation table
2. Update the label's color to match what you defined in the documentation
3. Ensure ALL gray labels are updated to non-gray colors

**Step 5: Apply ALL Labels to the Documentation Issue**
Update the issue you created in Step 1 by adding ALL existing labels from the repository. This serves as a visual demonstration of the complete color scheme. The issue should have every single label that exists in the repository applied to it.

**Step 6: Create Pull Request**
Create a pull request from 'feat/label-color-guide' to 'main' with:
- Title containing: "Add label color standardization guide" and "visual organization"  
- Body must include:
  - A "## Summary" heading explaining the label color standardization
  - A "## Changes" heading with a bullet list of what was added
  - A "## Label Updates" heading documenting the color changes
  - "Fixes #[ISSUE_NUMBER]" pattern linking to your created issue
  - A "## Verification" section stating that all labels now use non-gray colors
  - Keywords: "label standardization", "color guide", "visual improvement", "documentation"
- Labels: Add a reasonable subset of labels to the PR (at least 5-10 labels from different categories)

**Step 7: Document Color Changes in Issue**
Add a comment to the original issue with:
- Confirmation that all gray labels have been updated
- Total count of labels updated from gray (#ededed) to new colors
- Confirmation that the documentation has been created
- Reference to the PR using "PR #[NUMBER]" pattern
- Keywords: "colors updated", "gray labels replaced", "standardization complete"