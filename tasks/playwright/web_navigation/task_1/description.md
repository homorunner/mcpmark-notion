Navigate between web pages and extract information using Playwright MCP tools.

**Task Requirements:**

1. Navigate to https://mcp-eval-website.vercel.app/navigation

2. Extract the page title and main heading

3. Discover and extract all available navigation links on the page with their URLs and display text

4. Click on one of the discovered navigation links (preferably a forms-related link if available) to navigate to that page

5. On the new page, extract:
   • Page title and headings
   • Any structured data (JSON) if available
   • Page content summary

6. Return to the navigation page using browser back functionality

7. Verify the navigation history/breadcrumb functionality is working

8. Output your findings as a JSON code block with this exact structure:

```json
{
  "initialPage": {
    "title": "page title",
    "heading": "main heading"
  },
  "navigationLinks": [
    {"text": "Link Text", "url": "https://full-url-here"}
  ],
  "selectedLink": {
    "text": "clicked link text",
    "url": "https://clicked-url"
  },
  "visitedPage": {
    "title": "visited page title",
    "headings": ["heading 1", "heading 2"],
    "structuredData": {},
    "hasFormElements": true/false
  },
  "navigationHistory": {
    "returnedToNavigation": true/false,
    "breadcrumbWorking": true/false
  }
}
```

**Important:** Output only the JSON code block. Use the exact field names shown above.