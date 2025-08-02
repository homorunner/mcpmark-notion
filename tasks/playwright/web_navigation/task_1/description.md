# Web Navigation Task

Use Playwright MCP tools to navigate to a website and extract basic information.

## Requirements:

1. Navigate to https://mcp-eval-website.vercel.app/navigation
2. Extract the page title and main heading
3. Discover and extract all available navigation links on the page:
   - Identify each navigation link's URL and display text
   - Count the total number of navigation links found
4. Select one of the discovered navigation links (preferably a forms-related link if available)
5. Navigate to that page by clicking the selected link
6. Extract the page content, navigation history, and any structured data (JSON) if available
7. Return to the navigation page and verify breadcrumb/history functionality

## Expected Outcomes:

- Page title and headings are accurately extracted
- All navigation links are discovered and extracted with their URLs and labels
- Navigation between pages works correctly with proper redirects
- Page content including structured data is captured
- Navigation history/breadcrumbs are tracked and functional
- All navigation is performed using Playwright tools

## Success Criteria:

- Successfully navigate between multiple pages
- All discoverable navigation links are correctly identified and extracted
- Page titles and content are extracted accurately
- Navigation functionality works without browser errors or timeouts
- Structured data (JSON) is captured if present on pages
- Navigation history is properly tracked and breadcrumb functionality verified