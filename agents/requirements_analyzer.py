"""
Requirements Analysis Agent for processing SRS documents and generating SRDs.
"""

import re
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set
from dataclasses import dataclass, field

from .base_agent import BaseAgent
from utils import DocumentParser, ParsedDocument, ParsedSection


@dataclass
class TechnicalDependency:
    """Represents a technical dependency identified in requirements."""
    name: str
    type: str  # 'database', 'api', 'framework', 'library', 'service'
    version: str = ""
    description: str = ""
    is_external: bool = True
    migration_notes: str = ""


@dataclass
class RequirementIssue:
    """Represents an issue found in requirements."""
    issue_type: str  # 'contradiction', 'duplicate', 'ambiguous', 'missing'
    severity: str  # 'high', 'medium', 'low'
    description: str
    affected_sections: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Results of requirements analysis."""
    frontend_srd: str
    backend_srd: str
    dependencies: List[TechnicalDependency]
    issues: List[RequirementIssue]
    metadata: Dict[str, Any]


class RequirementsAnalyzer(BaseAgent):
    """Main agent for analyzing SRS documents and generating SRDs."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Requirements Analyzer agent."""
        super().__init__("RequirementsAnalyzer", config)
        self.parser = DocumentParser()
        
        # Patterns for identifying technical dependencies
        self.dependency_patterns = {
            'database': r'(?i)(database|mysql|postgresql|mongodb|sqlite|redis|cassandra|oracle)',
            'api': r'(?i)(api|rest|graphql|soap|endpoint|service)',
            'framework': r'(?i)(angular|react|vue|django|flask|fastapi|spring|express)',
            'library': r'(?i)(library|package|npm|pip|maven|gradle)',
            'service': r'(?i)(aws|azure|gcp|docker|kubernetes|microservice)'
        }
        
        # Patterns for identifying requirement issues
        self.issue_patterns = {
            'contradiction': [
                r'(?i)(but|however|except|unless|contradicts)',
                r'(?i)(shall not.*shall|must not.*must)',
            ],
            'ambiguous': [
                r'(?i)(maybe|perhaps|possibly|might|could|sometimes)',
                r'(?i)(appropriate|suitable|reasonable|adequate)',
            ],
            'duplicate': [
                r'(?i)(also|again|duplicate|repeat|same as)',
            ]
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SRS document and generate analysis results.
        
        Args:
            input_data: Dictionary containing 'file_path' key
            
        Returns:
            Analysis results with SRDs and metadata
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['file_path']):
                return self.handle_error(ValueError("Missing required 'file_path' in input"), "input_validation")
            
            file_path = Path(input_data['file_path'])
            
            # Parse document
            self.logger.info(f"Parsing document: {file_path}")
            parsed_doc = self.parser.parse_document(file_path)
            
            if not parsed_doc.is_valid:
                return self.handle_error(
                    ValueError(f"Document parsing failed: {parsed_doc.parsing_errors}"),
                    "document_parsing"
                )
            
            # Analyze requirements
            analysis_result = self._analyze_requirements(parsed_doc)
            
            # Generate SRD files
            self._generate_srd_files(analysis_result)
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "analyze_requirements",
                {"file_path": str(file_path)},
                {
                    "frontend_srd_length": len(analysis_result.frontend_srd),
                    "backend_srd_length": len(analysis_result.backend_srd),
                    "dependencies_count": len(analysis_result.dependencies),
                    "issues_count": len(analysis_result.issues)
                },
                success=True,
                execution_time_ms=execution_time
            )
            
            return {
                'success': True,
                'analysis_result': analysis_result,
                'execution_time_ms': execution_time,
                'log_summary': self.get_log_summary()
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "analyze_requirements",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "requirements_analysis")
    
    def _analyze_requirements(self, parsed_doc: ParsedDocument) -> AnalysisResult:
        """Analyze parsed document and extract requirements."""
        
        # Separate frontend and backend sections
        frontend_sections, backend_sections = self._categorize_sections(parsed_doc.sections)
        
        # Generate SRDs
        frontend_srd = self._generate_frontend_srd(frontend_sections, parsed_doc.metadata)
        backend_srd = self._generate_backend_srd(backend_sections, parsed_doc.metadata)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(parsed_doc.raw_text)
        
        # Identify issues
        issues = self._identify_issues(parsed_doc.raw_text, parsed_doc.sections)
        
        # Add decisions to log
        self.add_decision(
            "srd_generation_approach",
            ["section_based", "content_based", "hybrid"],
            "hybrid",
            "Using hybrid approach to combine section classification with content analysis for better SRD generation"
        )
        
        return AnalysisResult(
            frontend_srd=frontend_srd,
            backend_srd=backend_srd,
            dependencies=dependencies,
            issues=issues,
            metadata={
                'source_file': parsed_doc.file_path,
                'analysis_timestamp': time.time(),
                'sections_analyzed': len(parsed_doc.sections),
                'frontend_sections': len(frontend_sections),
                'backend_sections': len(backend_sections)
            }
        )
    
    def _categorize_sections(self, sections: List[ParsedSection]) -> Tuple[List[ParsedSection], List[ParsedSection]]:
        """Categorize sections into frontend and backend."""
        frontend_keywords = [
            'ui', 'user interface', 'frontend', 'client', 'component', 'view', 'screen',
            'form', 'button', 'navigation', 'responsive', 'angular', 'react', 'vue'
        ]
        
        backend_keywords = [
            'api', 'server', 'backend', 'database', 'service', 'endpoint', 'logic',
            'authentication', 'authorization', 'validation', 'processing', 'storage'
        ]
        
        frontend_sections = []
        backend_sections = []
        
        for section in sections:
            content_lower = (section.title + " " + section.content).lower()
            
            frontend_score = sum(1 for keyword in frontend_keywords if keyword in content_lower)
            backend_score = sum(1 for keyword in backend_keywords if keyword in content_lower)
            
            if frontend_score > backend_score:
                frontend_sections.append(section)
            elif backend_score > frontend_score:
                backend_sections.append(section)
            else:
                # If equal or no clear categorization, add to both
                frontend_sections.append(section)
                backend_sections.append(section)
        
        return frontend_sections, backend_sections
    
    def _generate_frontend_srd(self, sections: List[ParsedSection], metadata: Dict[str, Any]) -> str:
        """Generate frontend Software Requirements Document."""
        srd_content = [
            "# Frontend Software Requirements Document (SRD)",
            "",
            f"**Generated from:** {metadata.get('file_name', 'Unknown')}",
            f"**Generation Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Table of Contents",
            "1. [User Interface Requirements](#user-interface-requirements)",
            "2. [Component Architecture](#component-architecture)",
            "3. [User Experience Requirements](#user-experience-requirements)",
            "4. [Frontend Technical Requirements](#frontend-technical-requirements)",
            "5. [Responsive Design Requirements](#responsive-design-requirements)",
            "",
            "## User Interface Requirements",
            ""
        ]
        
        # Extract UI-related content
        ui_sections = [s for s in sections if any(
            keyword in s.title.lower() or keyword in s.content.lower() 
            for keyword in ['ui', 'interface', 'screen', 'form', 'view', 'component']
        )]
        
        for section in ui_sections:
            srd_content.extend([
                f"### {section.title}",
                "",
                section.content,
                ""
            ])
        
        srd_content.extend([
            "## Component Architecture",
            "",
            "### Angular Components Required",
            "- Main application component",
            "- Navigation component",
            "- Authentication components",
            "- Feature-specific components (based on requirements)",
            "",
            "### Component Hierarchy",
            "```",
            "AppComponent",
            "├── HeaderComponent",
            "├── NavigationComponent",
            "├── MainContentComponent",
            "└── FooterComponent",
            "```",
            "",
            "## User Experience Requirements",
            "",
            "### Usability Requirements",
            "- Intuitive navigation",
            "- Responsive design for all device sizes",
            "- Accessible design (WCAG 2.1 AA compliance)",
            "- Loading states and error handling",
            "",
            "### Performance Requirements",
            "- Initial page load time < 3 seconds",
            "- Smooth animations and transitions",
            "- Optimized bundle sizes",
            "",
            "## Frontend Technical Requirements",
            "",
            "### Technology Stack",
            "- Angular (latest stable version)",
            "- TypeScript",
            "- SCSS for styling",
            "- NgRx for state management",
            "- Angular Material or Bootstrap for UI components",
            "",
            "### Browser Support",
            "- Chrome (latest 2 versions)",
            "- Firefox (latest 2 versions)",
            "- Safari (latest 2 versions)",
            "- Edge (latest 2 versions)",
            "",
            "## Responsive Design Requirements",
            "",
            "### Breakpoints",
            "- Mobile: 320px - 767px",
            "- Tablet: 768px - 1023px",
            "- Desktop: 1024px and above",
            "",
            "### Mobile-First Design",
            "- Progressive enhancement approach",
            "- Touch-friendly interface elements",
            "- Optimized for mobile performance",
            ""
        ])
        
        return "\n".join(srd_content)
    
    def _generate_backend_srd(self, sections: List[ParsedSection], metadata: Dict[str, Any]) -> str:
        """Generate backend Software Requirements Document."""
        srd_content = [
            "# Backend Software Requirements Document (SRD)",
            "",
            f"**Generated from:** {metadata.get('file_name', 'Unknown')}",
            f"**Generation Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Table of Contents",
            "1. [API Requirements](#api-requirements)",
            "2. [Database Requirements](#database-requirements)",
            "3. [Business Logic Requirements](#business-logic-requirements)",
            "4. [Security Requirements](#security-requirements)",
            "5. [Performance Requirements](#performance-requirements)",
            "6. [Integration Requirements](#integration-requirements)",
            "",
            "## API Requirements",
            ""
        ]
        
        # Extract API-related content
        api_sections = [s for s in sections if any(
            keyword in s.title.lower() or keyword in s.content.lower() 
            for keyword in ['api', 'endpoint', 'service', 'rest', 'graphql']
        )]
        
        for section in api_sections:
            srd_content.extend([
                f"### {section.title}",
                "",
                section.content,
                ""
            ])
        
        srd_content.extend([
            "### API Design Principles",
            "- RESTful architecture",
            "- JSON request/response format",
            "- Consistent error handling",
            "- Proper HTTP status codes",
            "- API versioning support",
            "",
            "### Core Endpoints",
            "- Authentication endpoints",
            "- User management endpoints",
            "- Business logic endpoints (based on requirements)",
            "- Data retrieval and manipulation endpoints",
            "",
            "## Database Requirements",
            "",
            "### Database Design",
            "- Relational database (PostgreSQL recommended)",
            "- Normalized schema design",
            "- Proper indexing for performance",
            "- Data integrity constraints",
            "",
            "### Data Models",
            "- User model with authentication",
            "- Business entity models (based on requirements)",
            "- Audit logging tables",
            "- Configuration tables",
            "",
            "## Business Logic Requirements",
            "",
            "### Core Business Rules",
            "- Data validation rules",
            "- Business process workflows",
            "- Calculation logic",
            "- State management rules",
            "",
            "### Error Handling",
            "- Comprehensive exception handling",
            "- Proper error logging",
            "- User-friendly error messages",
            "- Rollback mechanisms",
            "",
            "## Security Requirements",
            "",
            "### Authentication & Authorization",
            "- JWT-based authentication",
            "- Role-based access control (RBAC)",
            "- Secure password policies",
            "- Session management",
            "",
            "### Data Security",
            "- Data encryption at rest and in transit",
            "- Input validation and sanitization",
            "- SQL injection prevention",
            "- XSS protection",
            "",
            "## Performance Requirements",
            "",
            "### Response Time Requirements",
            "- API response time < 500ms for simple queries",
            "- Database query optimization",
            "- Caching strategy implementation",
            "- Connection pooling",
            "",
            "### Scalability Requirements",
            "- Horizontal scaling capability",
            "- Load balancing support",
            "- Database connection management",
            "- Resource optimization",
            "",
            "## Integration Requirements",
            "",
            "### External Service Integration",
            "- Third-party API integration",
            "- Error handling and retry logic",
            "- Circuit breaker pattern",
            "- Rate limiting compliance",
            "",
            "### Technology Stack",
            "- FastAPI framework",
            "- Python 3.9+",
            "- PostgreSQL database",
            "- Alembic for migrations",
            "- Pydantic for data validation",
            ""
        ])
        
        return "\n".join(srd_content)
    
    def _extract_dependencies(self, text: str) -> List[TechnicalDependency]:
        """Extract technical dependencies from text."""
        dependencies = []
        seen_dependencies = set()
        
        for dep_type, pattern in self.dependency_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                dep_name = match.group(0).lower()
                
                # Avoid duplicates
                if dep_name not in seen_dependencies:
                    seen_dependencies.add(dep_name)
                    
                    # Extract version if mentioned nearby
                    context = text[max(0, match.start() - 50):match.end() + 50]
                    version_match = re.search(r'(\d+\.?\d*\.?\d*)', context)
                    version = version_match.group(1) if version_match else ""
                    
                    # Check for migration notes
                    migration_notes = ""
                    if re.search(r'(?i)(migrat|upgrad|transition)', context):
                        migration_notes = "Migration/upgrade mentioned in requirements"
                    
                    dependencies.append(TechnicalDependency(
                        name=dep_name,
                        type=dep_type,
                        version=version,
                        description=f"Identified {dep_type} dependency",
                        is_external=True,
                        migration_notes=migration_notes
                    ))
        
        return dependencies
    
    def _identify_issues(self, text: str, sections: List[ParsedSection]) -> List[RequirementIssue]:
        """Identify potential issues in requirements."""
        issues = []
        
        # Check for ambiguous language
        for issue_type, patterns in self.issue_patterns.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, text, re.IGNORECASE))
                
                if matches:
                    # Find which sections contain these issues
                    affected_sections = []
                    for section in sections:
                        if re.search(pattern, section.content, re.IGNORECASE):
                            affected_sections.append(section.title)
                    
                    issues.append(RequirementIssue(
                        issue_type=issue_type,
                        severity="medium",
                        description=f"Found {len(matches)} instances of {issue_type} language",
                        affected_sections=affected_sections,
                        suggestions=[
                            f"Review and clarify {issue_type} statements",
                            "Use more specific and measurable language",
                            "Consider adding acceptance criteria"
                        ]
                    ))
        
        # Check for missing critical sections
        critical_sections = ['security', 'performance', 'testing', 'deployment']
        existing_section_types = {s.section_type for s in sections}
        
        for critical_section in critical_sections:
            if critical_section not in existing_section_types:
                issues.append(RequirementIssue(
                    issue_type="missing",
                    severity="high",
                    description=f"Missing {critical_section} requirements section",
                    affected_sections=[],
                    suggestions=[
                        f"Add dedicated {critical_section} requirements section",
                        f"Define specific {critical_section} criteria and constraints"
                    ]
                ))
        
        return issues
    
    def _generate_srd_files(self, analysis_result: AnalysisResult):
        """Generate and save SRD files to output directory."""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Save frontend SRD
        frontend_path = output_dir / "srd_frontend.md"
        with open(frontend_path, 'w', encoding='utf-8') as f:
            f.write(analysis_result.frontend_srd)
        
        # Save backend SRD
        backend_path = output_dir / "srd_backend.md"
        with open(backend_path, 'w', encoding='utf-8') as f:
            f.write(analysis_result.backend_srd)
        
        self.logger.info(f"Generated SRD files: {frontend_path}, {backend_path}")