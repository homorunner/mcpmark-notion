"""Example – Duplicate a child page

Update the placeholders below with your own page URL/title information, then
run:
    python example/duplicate_child_page_demo.py
"""
from tasks.utils.page_duplication import duplicate_child_page

if __name__ == "__main__":
    duplicate_child_page(
        parent_url="https://www.notion.so/MCPBench-Test-22c0b91d1c3f80bb8c28d142062abe50",
        source_title="Japan Travel Planner 🌸",                          # ← replace
        target_title="Japan Travel Planner (Copy)",                     # ← replace
        headless=True,  # Set False to watch the browser window
    ) 