# Multi-Agent SRS to Angular+FastAPI Generator

## Overview

A sophisticated multi-agent system that transforms Software Requirements Specification (SRS) documents into fully functional Angular + FastAPI applications. The system employs multiple specialized agent workflows for requirements analysis, backend development, frontend development, testing, and code review with human-in-the-loop validation.

## Architecture

The system uses AutoGen framework for multi-agent orchestration with the following components:

- **Requirements Analyzer Agent**: Parses SRS documents and generates separate frontend/backend SRDs
- **Backend Agent Workflows**: 5 specialized agents for API design, models, business logic, integration, and database migrations
- **Frontend Agent Workflows**: 5 specialized agents for components, services, UI implementation, and state management
- **Test Generation & Critic Workflow**: Automated test generation with code review and security analysis
- **Human-in-the-Loop**: Validation and approval workflows at key stages

## Tech Stack

- **AutoGen**: Multi-agent orchestration framework
- **FastAPI**: Backend API and workflow orchestration
- **Streamlit**: User interface for document upload and monitoring
- **PostgreSQL**: Document storage and workflow state management
- **MCP Servers**: File operations, web search, and knowledge base tools
- **LangSmith**: Agent activity logging and MCP logs tracking
- **Angular**: Generated frontend framework

## Project Structure

```
/project-root/
    /backend/        # FastAPI application
    /frontend/       # Streamlit interface
    /agents/         # Agent workflows and logic
    /utils/          # Document parsing, logging helpers
    /config/         # Configuration management
    /logs/           # Log files
    /tests/          # Unit tests
    /output/         # Generated code output
    README.md
    requirements.txt
    .gitignore
```

## Quick Start

1. **Setup Environment**:
   ```bash
   pip install -r requirements.txt
   cp config/.env.example config/.env
   # Edit config/.env with your settings
   ```

2. **Start Backend**:
   ```bash
   cd backend
   python main.py
   ```

3. **Start Frontend**:
   ```bash
   cd frontend
   streamlit run app.py
   ```

4. **Access Applications**:
   - Streamlit UI: http://localhost:8501
   - FastAPI Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Features

### Phase 1: Document Processing
- Upload SRS documents (PDF/DOCX/MD)
- Automated parsing and structure extraction
- Generation of separate backend/frontend SRDs
- Human-in-the-loop review and editing

### Phase 2: Code Generation
- **Backend**: FastAPI routes, Pydantic models, business logic, integrations, DB migrations
- **Frontend**: Angular components, services, state management, responsive UI
- Cross-agent validation and conflict resolution
- Automated rollback capabilities

### Phase 3: Quality Assurance
- Automated test generation (unit, integration, E2E)
- Code review and security analysis
- Performance optimization recommendations
- Edge case discovery and handling

### Phase 4: Observability
- Comprehensive logging and monitoring
- Agent decision tree tracking
- Workflow state management
- Export capabilities (ZIP, Docker, Git)

## Agent Workflows

### Requirements Analysis
- **RequirementsAnalyzer**: Primary agent for SRS parsing and SRD generation

### Backend Agents
- **APIDesignerAgent**: FastAPI route design and OpenAPI schemas
- **ModelDeveloperAgent**: Pydantic models with validation
- **BusinessLogicAgent**: Core business rule implementation
- **IntegrationAgent**: Third-party API integration with resilience
- **DatabaseMigrationAgent**: Alembic migration scripts

### Frontend Agents
- **ComponentDesignerAgent**: Angular component architecture
- **ServiceDeveloperAgent**: Angular services with caching/retry
- **UIImplementationAgent**: Responsive SCSS/HTML implementation
- **StateManagementAgent**: NgRx store and effects
- **RouterAgent**: Angular routing and navigation

### Quality Assurance Agents
- **TestGeneratorAgent**: Comprehensive test suite creation
- **CodeReviewAgent**: Code quality and standards review
- **SecurityAgent**: Security vulnerability analysis
- **PerformanceAnalyzerAgent**: Performance optimization recommendations

## Configuration

Key configuration options in `config/.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/srs_generator
REDIS_URL=redis://localhost:6379

# LLM Configuration
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
LLM_PROVIDER=openai

# Agent Configuration
MAX_AGENT_RETRIES=3
HUMAN_APPROVAL_TIMEOUT=300
ENABLE_AUTO_ROLLBACK=true

# Logging
LOG_LEVEL=INFO
LANGSMITH_API_KEY=your_key_here
```

## Development

### Running Tests
```bash
pytest tests/ -v --cov=.
```

### Code Quality
```bash
ruff check .
black .
mypy .
```

### Database Migrations
```bash
cd backend
alembic upgrade head
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with proper tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details