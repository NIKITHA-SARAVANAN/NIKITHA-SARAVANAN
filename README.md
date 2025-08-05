# Multi-Agent SRC to Application Generator

A sophisticated multi-agent system that transforms Software Requirements Specification (SRC) documents into fully functional Angular + FastAPI applications using AutoGen, with human-in-the-loop validation.

## Overview

This system employs multiple specialized agent workflows for:
- Requirements analysis and SRD generation
- Backend development (FastAPI)
- Frontend development (Angular)
- Automated testing and code review
- Human-in-the-loop validation

## Tech Stack

- **AutoGen**: Multi-agent orchestration framework
- **FastAPI**: Backend API and workflow orchestration
- **Streamlit**: User interface for document upload and monitoring
- **MCP Servers**: File operations, web search, and knowledge base tools
- **LangSmith**: Agent activity logging and MCP logs tracking
- **Angular**: Frontend framework (generated output)

## Project Structure

```
/project-root/
    /backend/       # FastAPI code
    /frontend/      # Streamlit code
    /agents/        # All agent workflows and logic
    /utils/         # Doc parsing, logging helpers
    /config/        # config.py, sample config, .env
    /logs/          # Log files
    /tests/         # Unit tests
    /output/        # Generated applications
    README.md
    requirements.txt
    .gitignore
```

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your settings
   ```

3. **Run Backend**
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Run Frontend**
   ```bash
   cd frontend
   streamlit run app.py
   ```

5. **Access Applications**
   - Streamlit UI: http://localhost:8501
   - FastAPI Swagger: http://localhost:8000/docs

## Features

### Milestone 1: Project Setup ✅
- Complete project structure
- FastAPI backend with health endpoint
- Streamlit frontend with document upload
- Agent registry system
- Configuration management
- Centralized logging

### Milestone 2: Requirements Analysis Agent
- SRC document parsing (PDF, DOCX, Markdown)
- Dual SRD generation (frontend/backend)
- Dependency and contract analysis
- Human-in-the-loop feedback

### Milestone 3: Agent Workflows
- Backend agent workflow (API, Models, Business Logic, Integration)
- Frontend agent workflow (Components, Services, UI, State)
- Cross-agent validation and rollback
- Exception handling in generated code

### Milestone 4: Test Generation & Critic Workflow
- Automated test coverage (unit, integration, E2E)
- Code and security review agents
- Performance analysis
- Error and exception testing

### Milestone 5: MCP Servers & Observability
- File operations server with versioning
- Validation server with security scanning
- Knowledge/search server
- Enhanced Streamlit UI

### Milestone 6: Cross-Cutting Concerns
- Unit test quality assurance
- Code quality and linting
- Git best practices

## Usage

1. Upload your SRC document through the Streamlit interface
2. Review and approve the generated SRDs
3. Monitor agent workflows in real-time
4. Review and approve generated code
5. Download the complete Angular + FastAPI application

## Development

### Running Tests
```bash
pytest tests/ -v --cov=.
```

### Code Quality
```bash
ruff check .
mypy .
```

### Contributing
1. Create feature branch
2. Implement changes with tests
3. Ensure linting passes
4. Submit PR with description

## License

MIT License - see LICENSE file for details