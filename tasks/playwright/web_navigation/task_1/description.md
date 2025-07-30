# Web Navigation Task

Use Playwright MCP tools to navigate to a website and extract basic information.

## Requirements:

1. Navigate to https://mcp-eval-website.vercel.app/navigation
2. Extract the page title and main heading
3. Identify and extract all available navigation links:
   - Form Interaction (/forms)
   - Element Extraction (/extraction)
   - File Downloads (/downloads)
   - Basic Auth (/auth/basic)
   - Form Login (/auth/form)
   - Challenge Auth (/auth/challenge)
   - Web Navigation (/navigation)
4. Click on the "Form Interaction" navigation link
5. Navigate to the forms page
6. Extract the page content, navigation history, and JSON data if available
7. Return to navigation page and verify breadcrumb/history functionality

## Expected Outcomes:

- Page title and headings should be extracted
- All 7 navigation links should be identified and extracted
- Navigation between pages should work correctly with proper redirects
- Page content including JSON data should be captured
- Navigation history/breadcrumbs should be tracked
- All navigation should be performed using Playwright tools

## Success Criteria:

- Successfully navigate to both pages (/navigation and /forms)
- All 7 navigation links are correctly identified and extracted
- Page titles and content are extracted correctly
- Navigation functionality works without browser errors or timeouts
- JSON page data is captured if present
- Navigation history is properly tracked