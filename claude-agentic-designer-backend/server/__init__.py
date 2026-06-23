"""FastAPI server package for Claude Agentic Designer.

Bridges the Claude Skill (which emits events via tools/emit_event.py and JSONL) to
the React companion UI over Server-Sent Events, and manages the persistent reference
library (master deck + examples) with Microsoft 365 / SharePoint integration.
"""
