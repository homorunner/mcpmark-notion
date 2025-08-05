# Form Interaction Task

Use Playwright MCP tools to interact with web forms and submit data.

## Requirements:

1. Navigate to https://mcp-eval-website.vercel.app/forms/
2. Fill out the customer information form with the following data (add short pauses between fields):
   - Customer Name: "John Doe"
   - Phone Number: "123-456-7890" 
   - Email Address: "john.doe@example.com"
   - Size: Select "Large" from dropdown
   - Delivery Time: Select "Afternoon" radio button  
   - Additional Comments: "This is a test submission for MCPBench"
   
   After filling each field, wait 1-2 seconds and verify the field contains only the expected data. If any field contains data from multiple fields (concatenation), clear and re-fill that field before proceeding.

3. Submit the form by clicking the submit button
4. Wait for backend processing and redirect to /forms/result/{submission_id} page
5. Capture the response page content and verify submitted data appears correctly

## Expected Outcomes:

- All required form fields should be filled with specified data
- Form validation should pass (all required fields completed)
- Form submission should be successful without errors
- Page should redirect to /forms/result/{submission_id} automatically after backend processing
- Result page should display server-rendered submission data with proper formatting

## Success Criteria:

- All 6 form fields are filled correctly (5 required + 1 optional)
- No form validation errors occur
- Form submission completes successfully with backend processing
- Redirect to /forms/result/{submission_id} happens automatically (where {submission_id} is a numeric ID)
- Result page displays all submitted data with proper field labels:
  - Submission ID: {numeric_id}
  - Customer Name: John Doe
  - Phone Number: 123-456-7890
  - Email Address: john.doe@example.com
  - Size: large
  - Delivery Time: afternoon
  - Comments: This is a test submission for MCPBench
  - Submitted At: {timestamp}
- All submitted data matches the input values exactly

Use Playwright MCP tools to complete this web automation task.