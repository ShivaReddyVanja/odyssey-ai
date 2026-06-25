# OdysseyAI Project Guide

Welcome! Before writing any code, please review the complete system architecture, backend data schemas, and frontend layout choices here:
* **Project Context**: [docs/project_context.md](file:///Users/shivareddy/Projects/travel-agents/docs/project_context.md)

---

## Core Command Cheatsheet

### Backend (Python FastAPI + LangGraph)
- **Start Dev Server**: `cd backend && python server.py`
- **Run Tests**: `cd backend && pytest`
- **Dependencies**: Defined in [backend/requirements.txt](file:///Users/shivareddy/Projects/travel-agents/backend/requirements.txt)

### Frontend (Next.js + TypeScript)
- **Start Dev Server**: `cd frontend && npm run dev`
- **Install Dependencies**: `cd frontend && npm install`
- **Port**: Typically runs on `http://localhost:3000` (points to FastAPI on `http://localhost:8000`)
