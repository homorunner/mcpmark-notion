# Element Extraction Task

Use Playwright MCP tools to extract specific elements and data from a webpage.

## Requirements:

1. Navigate to https://mcp-eval-website.vercel.app/extraction
2. Discover and extract all main navigation links from the page:
   - Identify each navigation link's URL and display text
   - Count the total number of navigation links found
3. Find and extract all page headings (h1, h2, h3, h4, h5, h6):
   - Capture the heading text content
   - Note the heading level (h1, h2, etc.)
4. Locate and identify all HTTP method elements on the page:
   - Look for buttons, links, or text displaying HTTP methods
   - Extract method names (e.g., GET, POST, PUT, DELETE, etc.)
5. Find all HTTP status code references on the page:
   - Extract status codes and their descriptions
   - Look for both numeric codes and status text
6. Extract any JSON or code block examples displayed on the page:
   - Capture code snippets, JSON objects, or formatted code blocks
   - Preserve formatting where possible
7. Generate a comprehensive structured report of all extracted data

## Expected Outcomes:

- All navigation links are discovered and extracted with URLs and labels
- Page headings are captured with their text and hierarchy level
- HTTP method elements are identified and extracted
- Status code sections are found and extracted
- Code examples/JSON blocks are captured accurately
- Structured data report is generated in organized format (JSON recommended)

## Success Criteria:

- All discoverable navigation elements are correctly identified
- All page headings are extracted without missing any
- HTTP methods and status codes are comprehensively found
- Code blocks are properly captured with formatting preserved
- No duplicate elements in extraction results
- Structured output is well-formatted, complete, and machine-readable