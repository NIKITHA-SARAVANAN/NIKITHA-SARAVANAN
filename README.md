# Multi-Agent SRS Processing System

An intelligent multi-agent system built with AutoGen that processes Software Requirements Specification (SRS) documents and generates complete Angular project code.

## Features

- **Document Processing**: Supports PDF, DOCX, and Markdown SRS documents
- **Multi-Agent Architecture**: 5 specialized sub-agents under Frontend and Backend parent agents
- **Human-in-the-Loop**: Streamlit UI for reviewing and editing generated requirements
- **Code Generation**: Complete Angular project structure with components, services, and state management
- **Test Generation**: Automated unit, integration, and E2E test generation
- **Security & Performance**: Built-in code review and security analysis
- **Observability**: Comprehensive logging and monitoring with MCP servers

## Architecture

### Milestone 2: Requirements Analysis Agent
- Enhanced document parser with type detection
- Requirements analysis with dependency tracking
- SRD generation for frontend and backend
- Human feedback loop via Streamlit UI

### Milestone 3: Agent Workflows
#### Backend Agents
- APIDesignerAgent: FastAPI route generation
- ModelDeveloperAgent: Pydantic model creation
- BusinessLogicAgent: Business rule implementation
- IntegrationAgent: Third-party API integration
- DatabaseMigrationAgent: Alembic migration scripts

#### Frontend Agents
- ComponentDesignerAgent: Angular component generation
- ServiceDeveloperAgent: Angular services with caching
- UIImplementationAgent: Responsive SCSS/HTML
- StateManagementAgent: NgRx store management

### Milestone 4: Test Generation & Critic Workflow
- Automated test scaffolding (pytest, Cypress)
- Code review and security analysis
- Performance optimization recommendations

### Milestone 5: MCP Servers & Observability
- File operations with versioning
- Validation servers for syntax and security
- Knowledge search and dependency tracking
- Comprehensive logging and monitoring

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the Streamlit UI:
   ```bash
   streamlit run ui/main.py
   ```

3. Upload your SRS document and let the agents generate your Angular project!

## Project Structure

```
├── agents/           # Multi-agent implementations
├── utils/           # Document parsing and utilities
├── output/          # Generated SRD and code files
├── mcp_servers/     # MCP server implementations
├── tests/           # Test generation and validation
├── ui/              # Streamlit user interface
└── config/          # Configuration files
```