# MCPBench – Quick Start

## Setup

1. Create a `.env` file in the project root with:

```
OPENAI_API_KEY=<your-openai-key>
NOTION_API_KEY=<your-notion-token>
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Run a Task

```bash
python notion_task_runner.py tasks/calendar/modify_calendar.md
```

## Verify the Result

```bash
python tasks/calendar/verify_calendar_event.py <notion_page_id>
```

Each sub-folder in `tasks/` contains a Markdown task file and a matching `verify_*.py` script.

## Task Structure

```
tasks/
  ├── calendar/
  │   ├── modify_calendar.md          # Task instructions
  │   └── verify_calendar_event.py    # Verification script
  ├── modify_resume_template/
  │   ├── modify_resume.md
  │   ├── read_resume.md
  │   └── verify_resume_modify.py
  └── resume_submit/
      ├── resume_submit.md
      └── verify_resume_entry.py
```
