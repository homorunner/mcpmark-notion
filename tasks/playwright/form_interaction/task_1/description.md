# Form Interaction Task

Use Playwright MCP tools to interact with web forms and submit data.

## Requirements:

1. Navigate to https://mcp-eval-website.vercel.app/forms/
2. Fill out the customer information form with the following data:
   - Customer Name: "John Doe" (text input, required)
   - Phone Number: "123-456-7890" (text input, required)
   - Email Address: "john.doe@example.com" (text input, required)
   - Size: Select "Large" from dropdown (Small/Medium/Large, required)
   - Delivery Time: Select "Afternoon" radio button (Morning/Afternoon/Evening, required)
   - Additional Comments: "This is a test submission for MCPBench" (textarea, optional)
3. Submit the form by clicking the submit button
4. Wait for redirect to /forms/result page
5. Capture the response page content and verify submitted data

## Expected Outcomes:

- All required form fields should be filled with specified data
- Form validation should pass (all required fields completed)
- Form submission should be successful without errors
- Page should redirect to /forms/result automatically
- Response page should display the submitted form data from sessionStorage

## Success Criteria:

- All 6 form fields are filled correctly (5 required + 1 optional)
- No form validation errors occur
- Form submission completes successfully
- Redirect to /forms/result happens automatically
- Response page displays all submitted data correctly