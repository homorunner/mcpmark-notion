# Element Extraction Task

Use Playwright MCP tools to extract specific elements and data from a webpage.

## Requirements:

1. Navigate to https://mcp-eval-website.vercel.app/extraction
2. Extract all the main navigation links and their URLs:
   - /forms (Form Interaction)
   - /extraction (Element Extraction) 
   - /downloads (File Downloads)
   - /auth/basic (Basic Auth)
   - /auth/form (Form Login)
   - /auth/challenge (Challenge Auth)
   - /navigation (Web Navigation)
3. Find and extract the page headings:
   - "MCPBench Test Environment"
   - "HTTP Request & Response Service"
   - "HTTP Methods"
   - "HTTP Status Codes"
4. Locate all HTTP method buttons (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
5. Extract all HTTP status code sections:
   - 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found, 500 Internal Server Error
6. Extract JSON/code block examples from the page
7. Generate a structured report of all extracted data

## Expected Outcomes:

- Navigation links should be extracted with their URLs and labels
- Page headings should be captured accurately
- All 7 HTTP method buttons should be identified
- All 6 status code sections should be extracted
- JSON/code examples should be captured
- Structured data report should be generated in JSON format

## Success Criteria:

- All 7 navigation elements are correctly identified with URLs
- All 7 HTTP method buttons are extracted
- All 6 status code sections are captured
- Page headings match expected values
- JSON/code blocks are properly extracted
- No missing or duplicate elements in extraction
- Structured output is well-formatted and complete