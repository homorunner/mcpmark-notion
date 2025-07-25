# Form Interaction Task

Use Playwright MCP tools to interact with web forms and submit data.

## Requirements:

1. Navigate to https://httpbin.org/forms/post
2. Fill out the form with the following data:
   - custname: "John Doe"
   - custtel: "123-456-7890"
   - custemail: "john.doe@example.com"
   - size: Select "Large"
   - delivery: Check the appropriate delivery time
   - comments: "This is a test submission"
3. Submit the form
4. Capture the response page
5. Extract the form data from the response to verify submission

## Expected Outcomes:

- Form should be filled with specified data
- Form submission should be successful
- Response page should contain the submitted data
- All form interactions should use Playwright tools

## Success Criteria:

- All form fields are filled correctly
- Form submission completes without errors
- Response contains the submitted form data
- No form validation errors occur