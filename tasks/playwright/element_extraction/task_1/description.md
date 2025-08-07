Extract specific elements and data from a webpage using Playwright MCP tools.

**Task Requirements:**

1. Navigate to https://mcp-eval-website.vercel.app/extraction

2. Extract and collect the following elements:
   • **Navigation Links** – All `<a>` elements within `<nav>` tags, including both regular paths (e.g., `/forms`) and anchor links (e.g., `#http-methods`)
   • **Page Headings** – All heading elements (h1, h2, h3, h4, h5, h6) with their level and text content
   • **HTTP Methods** – All HTTP method names displayed on the page (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
   • **Status Codes** – All HTTP status codes with their descriptions (e.g., "200 OK - Request successful")
   • **Code Blocks** – All JSON examples or code snippets displayed on the page

3. Output your findings as a JSON code block with this exact structure:

```json
{
  "navigationLinks": [
    {"text": "Link Text", "url": "/path/or#anchor"}
  ],
  "headings": [
    {"level": "h1", "text": "Heading Text"}
  ],
  "httpMethods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
  "statusCodes": [
    {"code": "200", "description": "OK - Request successful"}
  ],
  "codeBlocks": [
    "code block content as string"
  ]
}
```

**Important:** Output only the JSON code block. Use the exact field names shown above (camelCase).