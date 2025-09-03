# Backend Architecture Issues & Improvements

## 🚨 Current Problems Identified

### 1. **Excessive RAGQueryDataManager Instances**
- **Issue**: 11 instances of `RAGQueryDataManager` scattered across backend.py
- **Problem**: Each endpoint creates its own instance instead of using shared services
- **Impact**: Code duplication, harder maintenance, potential inconsistencies

### 2. **No Service Layer Architecture**
- **Issue**: Direct data access from HTTP endpoints
- **Problem**: Business logic mixed with HTTP handling
- **Impact**: Difficult to test, reuse, and maintain

### 3. **Mixed Responsibilities in Single File**
- **Issue**: backend.py handles multiple project types and concerns:
  - Dimension-based projects
  - RAG projects
  - File uploads
  - Query generation
  - Query approval
  - Export functionality
- **Problem**: Violates Single Responsibility Principle
- **Impact**: File is >1400 lines, hard to navigate and maintain

### 4. **Duplicate Code Patterns**
- **Issue**: Similar operations repeated across endpoints:
  - Project path resolution
  - Data manager initialization
  - Error handling patterns
  - Status updates
- **Problem**: Code duplication without shared utilities
- **Impact**: Bugs need to be fixed in multiple places

### 5. **No Dependency Injection**
- **Issue**: Hard-coded dependencies throughout endpoints
- **Problem**: Tight coupling, difficult to test, no flexibility
- **Impact**: Cannot easily mock services for testing

### 6. **Inconsistent Error Handling**
- **Issue**: Different error handling patterns across endpoints
- **Problem**: Some use try/catch, others don't, inconsistent error messages
- **Impact**: Poor debugging experience, inconsistent API responses

---

## 🎯 Proposed Improvements

### 1. **Service Layer Architecture**

```python
# services/rag_project_service.py
class RAGProjectService:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.query_manager = RAGQueryDataManager(str(project_path))
        self.fact_manager = FactDataManager(str(project_path))
        self.chunk_processor = ChunkProcessor()
    
    def get_queries(self, stage: str) -> List[RAGQuery]:
        """Centralized query loading with error handling."""
        return self.query_manager.load_queries(stage)
    
    def approve_queries(self, query_ids: List[str]) -> ApprovalResult:
        """Centralized query approval logic."""
        pass
    
    def generate_queries(self, provider: str, query_type: str) -> GenerationResult:
        """Centralized query generation logic."""
        pass

# services/dimension_project_service.py  
class DimensionProjectService:
    # Similar pattern for dimension-based projects
    pass
```

### 2. **Router Separation**

```python
# routers/rag_projects.py
from fastapi import APIRouter
from services.rag_project_service import RAGProjectService

router = APIRouter(prefix="/api/rag-projects", tags=["rag"])

@router.get("/{name}/queries/{stage}")
async def get_queries(name: str, stage: str):
    service = RAGProjectService(get_project_path(name))
    return service.get_queries(stage)

# routers/dimension_projects.py
# Similar pattern for dimension projects

# main backend.py becomes much smaller
from routers import rag_projects, dimension_projects
app.include_router(rag_projects.router)
app.include_router(dimension_projects.router)
```

### 3. **Dependency Injection Container**

```python
# dependencies.py
from functools import lru_cache

@lru_cache()
def get_rag_service(project_path: str) -> RAGProjectService:
    """Cached service factory."""
    return RAGProjectService(project_path)

def get_project_service(project_name: str, project_type: str):
    """Service factory based on project type."""
    project_path = get_project_path(project_name)
    
    if project_type == "rag":
        return get_rag_service(str(project_path))
    else:
        return get_dimension_service(str(project_path))
```

### 4. **Shared Utilities**

```python
# utils/project_utils.py
def validate_project_exists(project_path: Path, project_type: str) -> None:
    """Centralized project validation."""
    marker_file = ".rag_project" if project_type == "rag" else "config.yml"
    if not project_path.exists() or not (project_path / marker_file).exists():
        raise HTTPException(404, f"{project_type.title()} project not found")

# utils/response_utils.py
def create_success_response(message: str, data: dict = None) -> dict:
    """Standardized success responses."""
    return {"message": message, "success": True, **(data or {})}

def handle_service_error(error: Exception) -> HTTPException:
    """Centralized error handling."""
    if isinstance(error, ValidationError):
        return HTTPException(400, str(error))
    return HTTPException(500, f"Internal error: {str(error)}")
```

### 5. **Background Task Service**

```python
# services/background_service.py
class BackgroundTaskService:
    """Centralized background task management."""
    
    def __init__(self):
        self.status_tracker = StatusTracker()
    
    def start_query_generation(self, project_service: RAGProjectService, 
                             params: GenerationParams) -> str:
        """Start background query generation with unified tracking."""
        task_id = self.status_tracker.create_task("query_generation")
        # Unified background task logic
        return task_id
    
    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get status of any background task."""
        return self.status_tracker.get_status(task_id)
```

---

## 📋 Implementation Plan

### Phase 1: Service Extraction (High Priority)
- [ ] Create `RAGProjectService` class
- [ ] Create `DimensionProjectService` class  
- [ ] Extract common project utilities
- [ ] Update 3-5 endpoints to use services

### Phase 2: Router Separation (Medium Priority)
- [ ] Create separate router files
- [ ] Move RAG endpoints to dedicated router
- [ ] Move dimension endpoints to dedicated router
- [ ] Update main backend.py to use routers

### Phase 3: Dependency Injection (Medium Priority)
- [ ] Create service factory functions
- [ ] Implement caching for service instances
- [ ] Add dependency injection to endpoints
- [ ] Create mock services for testing

### Phase 4: Error Handling & Utils (Low Priority)
- [ ] Standardize error handling patterns
- [ ] Create shared utility functions
- [ ] Implement consistent response formats
- [ ] Add comprehensive logging

### Phase 5: Background Task Refactor (Low Priority)
- [ ] Unify background task management
- [ ] Create task status tracking service
- [ ] Simplify status polling endpoints
- [ ] Add task cancellation support

---

## 🎯 Benefits After Refactor

1. **Maintainability**: Much easier to find and fix issues
2. **Testing**: Can unit test services independently
3. **Scalability**: Easy to add new features and endpoints
4. **Consistency**: Unified patterns across all endpoints
5. **Debugging**: Centralized error handling and logging
6. **Code Reuse**: Shared logic in service layer
7. **Performance**: Service caching and optimization opportunities

---

## 📝 Notes

- Current architecture works but is technical debt
- Refactor can be done incrementally without breaking changes
- Service layer will make adding new features much easier
- Better testing coverage will be possible with this architecture
- Consider using FastAPI dependency injection system for cleaner code

**Priority**: Medium (after core functionality is complete)
**Effort**: ~2-3 days for full refactor
**Risk**: Low (can be done incrementally)