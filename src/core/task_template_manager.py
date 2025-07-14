#!/usr/bin/env python3
"""
Task Template Manager for MCPBench Evaluation
============================================

This module manages dynamic task descriptions by injecting runtime values
like duplicated page IDs into task templates.
"""

import re
from typing import Dict, Any, Optional


class TaskTemplateManager:
    """Manages task description templates and dynamic value injection."""
    
    # Template placeholders
    PAGE_ID_PLACEHOLDER = "{{PAGE_ID}}"
    PAGE_URL_PLACEHOLDER = "{{PAGE_URL}}"
    
    def __init__(self):
        """Initialize the task template manager."""
        pass
    
    def inject_page_id(self, template: str, page_id: str, page_url: Optional[str] = None) -> str:
        """Inject page ID and optionally page URL into a task template.
        
        Args:
            template: Task description template containing placeholders
            page_id: The page ID to inject
            page_url: Optional page URL to inject
            
        Returns:
            Task description with placeholders replaced
        """
        # Replace page ID placeholder
        result = template.replace(self.PAGE_ID_PLACEHOLDER, page_id)
        
        # Replace page URL placeholder if provided
        if page_url and self.PAGE_URL_PLACEHOLDER in result:
            result = result.replace(self.PAGE_URL_PLACEHOLDER, page_url)
        
        return result
    
    def has_page_id_placeholder(self, template: str) -> bool:
        """Check if a template contains page ID placeholder.
        
        Args:
            template: Task description template
            
        Returns:
            True if template contains page ID placeholder
        """
        return self.PAGE_ID_PLACEHOLDER in template
    
    def convert_legacy_description(self, description: str, page_id: str) -> str:
        """Convert legacy task descriptions to use the provided page ID.
        
        This function handles existing task descriptions that search for pages
        by name and converts them to use a specific page ID.
        
        Args:
            description: Original task description
            page_id: The page ID to use
            
        Returns:
            Modified task description with page ID
        """
        # Pattern to match "Find page named" or similar phrases
        patterns = [
            (r'Find page named "([^"]+)"', f'Use page with ID: {page_id}'),
            (r'Find the page named "([^"]+)"', f'Use page with ID: {page_id}'),
            (r'Navigate to "([^"]+)" page', f'Navigate to page with ID: {page_id}'),
            (r'Open the "([^"]+)" page', f'Open page with ID: {page_id}'),
        ]
        
        modified = description
        for pattern, replacement in patterns:
            if re.search(pattern, modified):
                modified = re.sub(pattern, replacement, modified)
                break
        
        # If no pattern matched, prepend the page ID information
        if modified == description:
            modified = f"Use page with ID: {page_id}\n\n{description}"
        
        return modified
    
    def create_templated_description(self, original_description: str) -> str:
        """Create a templated version of a task description.
        
        This converts a regular task description into a template that can
        accept dynamic values like page IDs.
        
        Args:
            original_description: Original task description
            
        Returns:
            Templated task description
        """
        # Pattern to match page references
        patterns = [
            (r'Find page named "([^"]+)"', f'Find page with ID: {self.PAGE_ID_PLACEHOLDER}'),
            (r'Find the page named "([^"]+)"', f'Find page with ID: {self.PAGE_ID_PLACEHOLDER}'),
            (r'Navigate to "([^"]+)" page', f'Navigate to page with ID: {self.PAGE_ID_PLACEHOLDER}'),
            (r'Open the "([^"]+)" page', f'Open page with ID: {self.PAGE_ID_PLACEHOLDER}'),
        ]
        
        templated = original_description
        for pattern, replacement in patterns:
            templated = re.sub(pattern, replacement, templated)
        
        return templated
    
    def extract_page_name_from_description(self, description: str) -> Optional[str]:
        """Extract the page name from a task description.
        
        Args:
            description: Task description
            
        Returns:
            Page name if found, None otherwise
        """
        # Patterns to extract page names
        patterns = [
            r'Find page named "([^"]+)"',
            r'Find the page named "([^"]+)"',
            r'Navigate to "([^"]+)" page',
            r'Open the "([^"]+)" page',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
        
        return None
    
    def generate_task_description_with_context(self, 
                                             template: str, 
                                             page_id: str,
                                             page_url: Optional[str] = None,
                                             additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a complete task description with all context.
        
        Args:
            template: Task description template
            page_id: The page ID to inject
            page_url: Optional page URL
            additional_context: Additional context to prepend
            
        Returns:
            Complete task description with context
        """
        # Start with the base description
        description = self.inject_page_id(template, page_id, page_url)
        
        # Add additional context if provided
        if additional_context:
            context_lines = []
            
            if "note" in additional_context:
                context_lines.append(f"Note: {additional_context['note']}")
            
            if "entry_page" in additional_context:
                context_lines.append(f"Entry page: {additional_context['entry_page']}")
            
            if context_lines:
                context_text = "\n".join(context_lines)
                description = f"{context_text}\n\n{description}"
        
        return description

    # ---------------------------------------------------------------------
    # Compatibility helpers
    # ---------------------------------------------------------------------

    def replace_page_search_with_id(self, description: str, page_id: str) -> str:
        """Replace legacy page-search instructions with a concrete page ID.

        The evaluation pipeline may pass in arbitrary task descriptions that either already
        use the ``{{PAGE_ID}}`` placeholder *or* contain human-readable instructions like
        "Find page named \"XYZ\"". This convenience wrapper handles both cases by either
        injecting the page ID into the template placeholder or converting the legacy text
        into an instruction that references the explicit ``page_id``.
        """

        # Case 1 – description is templated using the placeholder
        if self.has_page_id_placeholder(description):
            return self.inject_page_id(description, page_id)

        # Case 2 – legacy description that references page by name
        return self.convert_legacy_description(description, page_id)


def main():
    """Example usage of TaskTemplateManager."""
    manager = TaskTemplateManager()
    
    # Example 1: Using templates with placeholders
    template = 'Find page with ID: {{PAGE_ID}}, then in "Skills" section, add a new skill.'
    result = manager.inject_page_id(template, "12345678-1234-5678-1234-567812345678")
    print("Template example:")
    print(result)
    print()
    
    # Example 2: Converting legacy descriptions
    legacy = 'Find page named "Maya Zhang", then in "Skills" section, add a new skill.'
    converted = manager.convert_legacy_description(legacy, "12345678-1234-5678-1234-567812345678")
    print("Legacy conversion:")
    print(converted)
    print()
    
    # Example 3: Creating templates from original descriptions
    original = 'Find page named "John Doe" and update the contact information.'
    templated = manager.create_templated_description(original)
    print("Created template:")
    print(templated)
    print()
    
    # Example 4: Extracting page name
    page_name = manager.extract_page_name_from_description(legacy)
    print(f"Extracted page name: {page_name}")


if __name__ == "__main__":
    main()