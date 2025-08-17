# QGen Web Interface

A modern web interface for the QGen query generation tool, built with React + FastAPI.

## Architecture

- **Frontend**: React 18 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (single file for simplicity)
- **Build**: Vite for fast development and optimized builds

## Features

✅ **Complete Project Management**
- Create new projects with templates
- Load existing projects
- Project overview with statistics

✅ **Professional Query Review Interface**
- Floating action bar with bulk operations
- Status-based visual styling (pending/approved/rejected)
- Individual and bulk approve/reject/edit
- Proper visual containment (solved Streamlit issue)

✅ **Full Workflow Support**
- Tuple generation from dimensions
- Query generation from approved tuples
- Data export to CSV/JSON

## Quick Start

From project root:

```bash
# Start the web interface
qgen web
```

This will:
1. Start FastAPI backend on http://localhost:8000
2. Start React dev server on http://localhost:5173  
3. Open browser automatically

## Development

### Backend (FastAPI)
- Single file: `backend.py`
- Auto-reloads on changes
- API docs at http://localhost:8000/docs

### Frontend (React)
- Source: `frontend/src/`
- Hot reload enabled
- Built with Vite for fast development

### Key Components

- `ProjectSelector.tsx` - Project creation/loading
- `ProjectDashboard.tsx` - Main project interface with tabs
- `QueryReview.tsx` - Advanced query review with floating action bar

## Advantages over Streamlit

✅ **Full UI Control**: Custom components with precise styling
✅ **Professional UX**: Complex interactions like floating action bars
✅ **Performance**: Optimized React rendering
✅ **Type Safety**: End-to-end TypeScript
✅ **Maintainable**: Clear separation of concerns

## API Endpoints

- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `GET /api/projects/{name}` - Get project details
- `POST /api/projects/{name}/generate/tuples` - Generate tuples
- `POST /api/projects/{name}/generate/queries` - Generate queries
- `GET /api/projects/{name}/queries/generated` - Get queries
- `PUT /api/projects/{name}/queries/{id}` - Update query
- `POST /api/projects/{name}/queries/approve` - Bulk approve

## Files

```
src/qgen/web/
├── backend.py           # FastAPI server (single file)
├── launcher.py          # Launch script  
├── frontend/            # React application
│   ├── src/
│   │   ├── App.tsx      # Main app component
│   │   └── components/  # React components
│   ├── dist/            # Built files
│   └── package.json     # Frontend dependencies
└── README.md           # This file
```