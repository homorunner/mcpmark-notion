import notion_client as notion_client

def main():
    # Initialize the Notion client
    client = notion_client.Client(auth="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")
    
    # Search for "Job Applications" page
    search_results = client.search(query="Job Applications")
    
    job_applications_page = None
    for result in search_results.get("results", []):
        if result.get("object") == "page" and "Job Applications" in result.get("properties", {}).get("title", {}).get("title", [{}])[0].get("plain_text", ""):
            job_applications_page = result
            break
    
    if not job_applications_page:
        print("Job Applications page not found")
        return
    
    page_id = job_applications_page["id"]
    print(f"Found Job Applications page: {page_id}")
    
    # Get the page content to find databases
    page_content = client.blocks.children.list(block_id=page_id)
    
    database_id = None
    for block in page_content.get("results", []):
        if block.get("type") == "child_database":
            database_id = block["id"]
            break
    
    if not database_id:
        print("No database found in Job Applications page")
        return
    
    print(f"Found database: {database_id}")
    
    # Get current database properties
    database = client.databases.retrieve(database_id=database_id)
    current_properties = database.get("properties", {})
    
    print("Current properties:")
    for prop_name, prop_config in current_properties.items():
        print(f"  {prop_name}: {prop_config.get('type')}")
    
    # Check if Test property already exists
    if "Test" in current_properties:
        print("Test property already exists")
        return
    
    # Add only the new "Test" property
    new_properties = {
        "Test": {
            "type": "rich_text",
            "rich_text": {}
        }
    }
    
    # Update the database with the new property
    updated_database = client.databases.update(
        database_id=database_id,
        properties=new_properties
    )
    
    print(f"Successfully added 'Test' property to database {database_id}")
    print(f"Database now has {len(updated_database.get('properties', {}))} properties")

if __name__ == "__main__":
    main()