"""
Requirements Analyzer Agent for the SRS to Angular+FastAPI generator.

This agent parses Software Requirements Specification (SRS) documents
and generates separate Software Requirements Documents (SRDs) for
backend and frontend development.
"""

import asyncio
import re
from typing import Dict, List, Optional, Any, Tuple
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import LLMAgent, AgentResult, AgentCapabilities, AgentCategory
from utils.document_parser import ParsedDocument
from utils.logger import get_logger


class RequirementsAnalyzer(LLMAgent):
    """
    Requirements Analyzer Agent.
    
    Analyzes SRS documents and generates separate SRDs for backend and frontend,
    with human-in-the-loop validation and approval workflow.
    """
    
    def __init__(self):
        """Initialize the Requirements Analyzer agent."""
        capabilities = AgentCapabilities(
            name="RequirementsAnalyzer",
            description="Analyzes SRS documents and generates separate backend/frontend SRDs",
            category=AgentCategory.REQUIREMENTS,
            version="1.0.0",
            capabilities=[
                "document_parsing",
                "requirements_extraction", 
                "srd_generation",
                "dependency_analysis",
                "conflict_detection"
            ],
            dependencies=["document_parser"],
            input_requirements=["parsed_document"],
            output_types=["backend_srd", "frontend_srd", "analysis_report"],
            max_execution_time=600,  # 10 minutes
            requires_human_approval=True
        )
        
        super().__init__(capabilities)
        
        # Agent-specific configuration
        self.srd_templates = self._load_srd_templates()
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate input data for the Requirements Analyzer.
        
        Args:
            inputs: Input data containing parsed document
            
        Returns:
            bool: True if inputs are valid
        """
        required_fields = ["parsed_document"]
        
        for field in required_fields:
            if field not in inputs:
                self.logger.error(f"Missing required input field: {field}")
                return False
        
        # Validate parsed document structure
        parsed_doc = inputs["parsed_document"]
        if not isinstance(parsed_doc, dict):
            self.logger.error("parsed_document must be a dictionary")
            return False
        
        required_doc_fields = ["raw_text", "sections", "metadata"]
        for field in required_doc_fields:
            if field not in parsed_doc:
                self.logger.error(f"Missing required document field: {field}")
                return False
        
        return True
    
    async def execute(self, inputs: Dict[str, Any]) -> AgentResult:
        """
        Execute the requirements analysis workflow.
        
        Args:
            inputs: Input data containing parsed document
            
        Returns:
            AgentResult: Analysis results with generated SRDs
        """
        parsed_doc = inputs["parsed_document"]
        options = inputs.get("options", {})
        
        try:
            # Step 1: Analyze document structure and extract requirements
            self.activity_logger.log_decision(
                "start_analysis",
                "Begin requirements analysis",
                "Starting comprehensive analysis of SRS document",
                confidence=0.95
            )
            
            analysis_result = await self._analyze_document_structure(parsed_doc)
            
            # Step 2: Identify technical dependencies and constraints
            dependencies = await self._analyze_dependencies(parsed_doc, analysis_result)
            
            # Step 3: Detect conflicts and ambiguities
            conflicts = await self._detect_conflicts(analysis_result)
            
            # Step 4: Generate backend SRD
            self.activity_logger.log_decision(
                "generate_backend_srd",
                "Generate backend SRD",
                "Creating backend-focused Software Requirements Document",
                confidence=0.9
            )
            
            backend_srd = await self._generate_backend_srd(
                parsed_doc, analysis_result, dependencies
            )
            
            # Step 5: Generate frontend SRD
            self.activity_logger.log_decision(
                "generate_frontend_srd", 
                "Generate frontend SRD",
                "Creating frontend-focused Software Requirements Document",
                confidence=0.9
            )
            
            frontend_srd = await self._generate_frontend_srd(
                parsed_doc, analysis_result, dependencies
            )
            
            # Step 6: Create analysis report
            analysis_report = self._create_analysis_report(
                analysis_result, dependencies, conflicts
            )
            
            # Prepare approval content for human review
            approval_content = {
                "original_document": {
                    "filename": parsed_doc.get("filename", "Unknown"),
                    "sections_count": len(parsed_doc.get("sections", [])),
                    "requirements_count": len(analysis_result.get("requirements", []))
                },
                "backend_srd": {
                    "content": backend_srd,
                    "length": len(backend_srd),
                    "sections": self._extract_srd_sections(backend_srd)
                },
                "frontend_srd": {
                    "content": frontend_srd,
                    "length": len(frontend_srd),
                    "sections": self._extract_srd_sections(frontend_srd)
                },
                "analysis_summary": {
                    "total_requirements": len(analysis_result.get("requirements", [])),
                    "backend_requirements": len([r for r in analysis_result.get("requirements", []) 
                                                if r.get("type") == "backend"]),
                    "frontend_requirements": len([r for r in analysis_result.get("requirements", [])
                                                 if r.get("type") == "frontend"]),
                    "conflicts_found": len(conflicts),
                    "dependencies_identified": len(dependencies)
                },
                "conflicts": conflicts,
                "dependencies": dependencies
            }
            
            # Log performance metrics
            self.activity_logger.log_performance_metric(
                "requirements_extracted", 
                len(analysis_result.get("requirements", [])), 
                "count"
            )
            self.activity_logger.log_performance_metric(
                "backend_srd_length", 
                len(backend_srd), 
                "characters"
            )
            self.activity_logger.log_performance_metric(
                "frontend_srd_length", 
                len(frontend_srd), 
                "characters"
            )
            
            return AgentResult(
                success=True,
                data={
                    "backend_srd": backend_srd,
                    "frontend_srd": frontend_srd,
                    "analysis_result": analysis_result,
                    "dependencies": dependencies,
                    "conflicts": conflicts,
                    "analysis_report": analysis_report
                },
                files_generated=[
                    "output/srd_backend.md",
                    "output/srd_frontend.md",
                    "output/analysis_report.md"
                ],
                metadata={
                    "agent": self.capabilities.name,
                    "requirements_count": len(analysis_result.get("requirements", [])),
                    "conflicts_found": len(conflicts),
                    "dependencies_count": len(dependencies)
                },
                requires_approval=True,
                approval_content=approval_content
            )
            
        except Exception as e:
            self.logger.error(f"Requirements analysis failed: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.capabilities.name}
            )
    
    async def _analyze_document_structure(self, parsed_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze document structure and extract structured requirements.
        
        Args:
            parsed_doc: Parsed document data
            
        Returns:
            Dict containing analysis results
        """
        sections = parsed_doc.get("sections", [])
        raw_text = parsed_doc.get("raw_text", "")
        
        # Extract requirements from sections
        requirements = []
        functional_reqs = []
        non_functional_reqs = []
        
        for section in sections:
            section_title = section.get("title", "").lower()
            section_content = section.get("content", "")
            
            # Identify requirement types based on section titles
            if any(keyword in section_title for keyword in 
                   ["functional", "feature", "capability", "behavior"]):
                reqs = self._extract_functional_requirements(section_content)
                functional_reqs.extend(reqs)
                requirements.extend([{**req, "type": "functional"} for req in reqs])
                
            elif any(keyword in section_title for keyword in 
                     ["non-functional", "performance", "security", "reliability"]):
                reqs = self._extract_non_functional_requirements(section_content)
                non_functional_reqs.extend(reqs)
                requirements.extend([{**req, "type": "non-functional"} for req in reqs])
                
            else:
                # General requirement extraction
                reqs = self._extract_general_requirements(section_content)
                requirements.extend([{**req, "type": "general"} for req in reqs])
        
        # Categorize requirements by system component
        categorized_reqs = self._categorize_requirements(requirements)
        
        return {
            "requirements": requirements,
            "functional_requirements": functional_reqs,
            "non_functional_requirements": non_functional_reqs,
            "categorized_requirements": categorized_reqs,
            "sections_analyzed": len(sections),
            "document_metadata": parsed_doc.get("metadata", {})
        }
    
    def _extract_functional_requirements(self, content: str) -> List[Dict[str, Any]]:
        """Extract functional requirements from content."""
        requirements = []
        
        # Patterns for functional requirements
        patterns = [
            r"(?:The system|Application|Software) (?:shall|must|will|should) (.+?)(?:\.|$)",
            r"(?:REQ|FR)-?\d+:?\s*(.+?)(?:\.|$)",
            r"^\d+\.\s*(.+?)(?:\.|$)",
            r"[•\-\*]\s*(.+?)(?:\.|$)"
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                requirement_text = match.group(1).strip()
                
                if len(requirement_text) > 10:  # Filter out very short matches
                    requirements.append({
                        "id": f"FR-{len(requirements) + 1:03d}",
                        "text": requirement_text,
                        "priority": self._determine_priority(requirement_text),
                        "complexity": self._estimate_complexity(requirement_text),
                        "source": "functional_section"
                    })
        
        return requirements
    
    def _extract_non_functional_requirements(self, content: str) -> List[Dict[str, Any]]:
        """Extract non-functional requirements from content."""
        requirements = []
        
        # Patterns for non-functional requirements
        nfr_patterns = [
            r"(?:Performance|Response time|Throughput|Load):?\s*(.+?)(?:\.|$)",
            r"(?:Security|Authentication|Authorization):?\s*(.+?)(?:\.|$)",
            r"(?:Reliability|Availability|Uptime):?\s*(.+?)(?:\.|$)",
            r"(?:Scalability|Capacity):?\s*(.+?)(?:\.|$)",
            r"(?:Usability|User experience):?\s*(.+?)(?:\.|$)"
        ]
        
        for pattern in nfr_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                requirement_text = match.group(1).strip()
                
                if len(requirement_text) > 10:
                    requirements.append({
                        "id": f"NFR-{len(requirements) + 1:03d}",
                        "text": requirement_text,
                        "category": self._categorize_nfr(requirement_text),
                        "priority": self._determine_priority(requirement_text),
                        "source": "non_functional_section"
                    })
        
        return requirements
    
    def _extract_general_requirements(self, content: str) -> List[Dict[str, Any]]:
        """Extract general requirements from content."""
        requirements = []
        
        # General requirement patterns
        patterns = [
            r"(?:must|shall|will|should|needs? to)\s+(.+?)(?:\.|$)",
            r"(?:requirement|constraint):?\s*(.+?)(?:\.|$)"
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                requirement_text = match.group(1).strip()
                
                if len(requirement_text) > 15:  # Higher threshold for general reqs
                    requirements.append({
                        "id": f"GR-{len(requirements) + 1:03d}",
                        "text": requirement_text,
                        "priority": self._determine_priority(requirement_text),
                        "source": "general_section"
                    })
        
        return requirements
    
    def _categorize_requirements(self, requirements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize requirements by system component."""
        categories = {
            "backend": [],
            "frontend": [],
            "database": [],
            "integration": [],
            "infrastructure": [],
            "security": [],
            "general": []
        }
        
        for req in requirements:
            req_text = req.get("text", "").lower()
            
            # Backend keywords
            if any(keyword in req_text for keyword in 
                   ["api", "server", "backend", "service", "endpoint", "business logic", "processing"]):
                req["component"] = "backend"
                categories["backend"].append(req)
                
            # Frontend keywords
            elif any(keyword in req_text for keyword in 
                     ["ui", "user interface", "frontend", "display", "screen", "view", "form", "button"]):
                req["component"] = "frontend"
                categories["frontend"].append(req)
                
            # Database keywords
            elif any(keyword in req_text for keyword in 
                     ["database", "data", "store", "persist", "record", "table", "query"]):
                req["component"] = "database"
                categories["database"].append(req)
                
            # Integration keywords
            elif any(keyword in req_text for keyword in 
                     ["integration", "external", "third-party", "api call", "webhook"]):
                req["component"] = "integration"
                categories["integration"].append(req)
                
            # Security keywords
            elif any(keyword in req_text for keyword in 
                     ["security", "authentication", "authorization", "access", "permission", "encrypt"]):
                req["component"] = "security"
                categories["security"].append(req)
                
            # Infrastructure keywords
            elif any(keyword in req_text for keyword in 
                     ["deploy", "infrastructure", "server", "hosting", "performance", "scalability"]):
                req["component"] = "infrastructure"
                categories["infrastructure"].append(req)
                
            else:
                req["component"] = "general"
                categories["general"].append(req)
        
        return categories
    
    def _determine_priority(self, requirement_text: str) -> str:
        """Determine requirement priority from text."""
        text = requirement_text.lower()
        
        if any(keyword in text for keyword in ["critical", "must", "essential", "required"]):
            return "high"
        elif any(keyword in text for keyword in ["should", "important", "significant"]):
            return "medium"
        else:
            return "low"
    
    def _estimate_complexity(self, requirement_text: str) -> str:
        """Estimate implementation complexity."""
        text = requirement_text.lower()
        
        # High complexity indicators
        if any(keyword in text for keyword in 
               ["complex", "integration", "algorithm", "machine learning", "real-time", "scalable"]):
            return "high"
        # Medium complexity indicators
        elif any(keyword in text for keyword in 
                 ["process", "workflow", "validation", "calculation", "report"]):
            return "medium"
        else:
            return "low"
    
    def _categorize_nfr(self, requirement_text: str) -> str:
        """Categorize non-functional requirement."""
        text = requirement_text.lower()
        
        if any(keyword in text for keyword in ["performance", "speed", "response", "throughput"]):
            return "performance"
        elif any(keyword in text for keyword in ["security", "authentication", "authorization"]):
            return "security"
        elif any(keyword in text for keyword in ["reliability", "availability", "uptime"]):
            return "reliability"
        elif any(keyword in text for keyword in ["scalability", "capacity", "load"]):
            return "scalability"
        elif any(keyword in text for keyword in ["usability", "user experience", "interface"]):
            return "usability"
        else:
            return "other"
    
    async def _analyze_dependencies(self, parsed_doc: Dict[str, Any], 
                                  analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze technical dependencies and external integrations."""
        dependencies = []
        
        # Extract from document content
        content = parsed_doc.get("raw_text", "")
        
        # Database dependencies
        db_patterns = [
            r"(?:database|DB|MySQL|PostgreSQL|MongoDB|Redis|SQL Server)(\s+\w+)*",
            r"(?:data storage|persistence|CRUD|ORM)"
        ]
        
        for pattern in db_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                dependencies.append({
                    "type": "database",
                    "name": match.group().strip(),
                    "category": "infrastructure",
                    "required": True
                })
        
        # External API dependencies
        api_patterns = [
            r"(?:API|REST|GraphQL|SOAP)\s+(?:integration|service|endpoint)",
            r"(?:third[- ]party|external)\s+(?:service|API|integration)"
        ]
        
        for pattern in api_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                dependencies.append({
                    "type": "external_api",
                    "name": match.group().strip(),
                    "category": "integration",
                    "required": False
                })
        
        # Framework dependencies
        framework_keywords = {
            "Angular": {"type": "frontend_framework", "category": "frontend"},
            "React": {"type": "frontend_framework", "category": "frontend"},
            "Vue": {"type": "frontend_framework", "category": "frontend"},
            "FastAPI": {"type": "backend_framework", "category": "backend"},
            "Django": {"type": "backend_framework", "category": "backend"},
            "Flask": {"type": "backend_framework", "category": "backend"}
        }
        
        for framework, info in framework_keywords.items():
            if framework.lower() in content.lower():
                dependencies.append({
                    "type": info["type"],
                    "name": framework,
                    "category": info["category"],
                    "required": True
                })
        
        return dependencies
    
    async def _detect_conflicts(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect conflicts and ambiguities in requirements."""
        conflicts = []
        requirements = analysis_result.get("requirements", [])
        
        # Check for contradictory requirements
        for i, req1 in enumerate(requirements):
            for j, req2 in enumerate(requirements[i+1:], i+1):
                if self._are_conflicting(req1, req2):
                    conflicts.append({
                        "type": "contradiction",
                        "requirements": [req1["id"], req2["id"]],
                        "description": f"Requirements {req1['id']} and {req2['id']} appear to conflict",
                        "severity": "medium"
                    })
        
        # Check for duplicate requirements
        seen_requirements = {}
        for req in requirements:
            req_text = req.get("text", "").lower().strip()
            if req_text in seen_requirements:
                conflicts.append({
                    "type": "duplicate",
                    "requirements": [seen_requirements[req_text], req["id"]],
                    "description": f"Duplicate requirement detected",
                    "severity": "low"
                })
            else:
                seen_requirements[req_text] = req["id"]
        
        # Check for ambiguous requirements
        for req in requirements:
            if self._is_ambiguous(req):
                conflicts.append({
                    "type": "ambiguity",
                    "requirements": [req["id"]],
                    "description": f"Requirement {req['id']} contains ambiguous language",
                    "severity": "high"
                })
        
        return conflicts
    
    def _are_conflicting(self, req1: Dict[str, Any], req2: Dict[str, Any]) -> bool:
        """Check if two requirements are conflicting."""
        text1 = req1.get("text", "").lower()
        text2 = req2.get("text", "").lower()
        
        # Simple conflict detection based on negation patterns
        conflict_patterns = [
            ("must", "must not"),
            ("shall", "shall not"),
            ("required", "forbidden"),
            ("allow", "prevent"),
            ("enable", "disable")
        ]
        
        for positive, negative in conflict_patterns:
            if positive in text1 and negative in text2:
                return True
            if negative in text1 and positive in text2:
                return True
        
        return False
    
    def _is_ambiguous(self, req: Dict[str, Any]) -> bool:
        """Check if a requirement is ambiguous."""
        text = req.get("text", "").lower()
        
        # Ambiguous language indicators
        ambiguous_words = [
            "might", "maybe", "possibly", "potentially", "somewhat",
            "usually", "generally", "typically", "often", "sometimes",
            "adequate", "reasonable", "appropriate", "suitable"
        ]
        
        return any(word in text for word in ambiguous_words)
    
    async def _generate_backend_srd(self, parsed_doc: Dict[str, Any], 
                                  analysis_result: Dict[str, Any], 
                                  dependencies: List[Dict[str, Any]]) -> str:
        """Generate backend-focused Software Requirements Document."""
        
        backend_reqs = analysis_result["categorized_requirements"]["backend"]
        database_reqs = analysis_result["categorized_requirements"]["database"]
        integration_reqs = analysis_result["categorized_requirements"]["integration"]
        security_reqs = analysis_result["categorized_requirements"]["security"]
        
        system_prompt = """
        You are a senior software architect specializing in backend systems.
        Generate a comprehensive Software Requirements Document (SRD) focused on backend development.
        Include API design, database schema, business logic, integrations, and security requirements.
        Use clear, technical language appropriate for backend developers.
        """
        
        prompt = self.build_prompt(
            self.srd_templates["backend_template"],
            project_name=parsed_doc.get("metadata", {}).get("title", "Generated Project"),
            backend_requirements="\n".join([f"- {req['text']}" for req in backend_reqs]),
            database_requirements="\n".join([f"- {req['text']}" for req in database_reqs]),
            integration_requirements="\n".join([f"- {req['text']}" for req in integration_reqs]),
            security_requirements="\n".join([f"- {req['text']}" for req in security_reqs]),
            dependencies="\n".join([f"- {dep['name']} ({dep['type']})" for dep in dependencies if dep['category'] in ['backend', 'database', 'infrastructure']])
        )
        
        return await self.call_llm(prompt, system_prompt)
    
    async def _generate_frontend_srd(self, parsed_doc: Dict[str, Any], 
                                   analysis_result: Dict[str, Any], 
                                   dependencies: List[Dict[str, Any]]) -> str:
        """Generate frontend-focused Software Requirements Document."""
        
        frontend_reqs = analysis_result["categorized_requirements"]["frontend"]
        general_reqs = analysis_result["categorized_requirements"]["general"]
        
        system_prompt = """
        You are a senior frontend architect specializing in modern web applications.
        Generate a comprehensive Software Requirements Document (SRD) focused on frontend development.
        Include UI/UX requirements, component structure, state management, and user interactions.
        Use clear, technical language appropriate for frontend developers.
        """
        
        prompt = self.build_prompt(
            self.srd_templates["frontend_template"],
            project_name=parsed_doc.get("metadata", {}).get("title", "Generated Project"),
            frontend_requirements="\n".join([f"- {req['text']}" for req in frontend_reqs]),
            ui_requirements="\n".join([f"- {req['text']}" for req in general_reqs if 'ui' in req['text'].lower() or 'interface' in req['text'].lower()]),
            dependencies="\n".join([f"- {dep['name']} ({dep['type']})" for dep in dependencies if dep['category'] in ['frontend']])
        )
        
        return await self.call_llm(prompt, system_prompt)
    
    def _create_analysis_report(self, analysis_result: Dict[str, Any], 
                              dependencies: List[Dict[str, Any]], 
                              conflicts: List[Dict[str, Any]]) -> str:
        """Create a comprehensive analysis report."""
        
        report = f"""# Requirements Analysis Report

## Summary
- Total Requirements: {len(analysis_result.get('requirements', []))}
- Functional Requirements: {len(analysis_result.get('functional_requirements', []))}
- Non-Functional Requirements: {len(analysis_result.get('non_functional_requirements', []))}
- Dependencies Identified: {len(dependencies)}
- Conflicts Found: {len(conflicts)}

## Requirements Distribution
"""
        
        categorized = analysis_result.get("categorized_requirements", {})
        for category, reqs in categorized.items():
            if reqs:
                report += f"- {category.title()}: {len(reqs)} requirements\n"
        
        report += "\n## Identified Dependencies\n"
        for dep in dependencies:
            report += f"- {dep['name']} ({dep['type']}) - {dep['category']}\n"
        
        if conflicts:
            report += "\n## Conflicts and Issues\n"
            for conflict in conflicts:
                report += f"- {conflict['type'].title()}: {conflict['description']} (Severity: {conflict['severity']})\n"
        
        return report
    
    def _extract_srd_sections(self, srd_content: str) -> List[str]:
        """Extract section headers from SRD content."""
        sections = []
        lines = srd_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                sections.append(line.replace('#', '').strip())
        
        return sections
    
    def _load_srd_templates(self) -> Dict[str, str]:
        """Load SRD generation templates."""
        return {
            "backend_template": """
# Backend Software Requirements Document
# Project: {project_name}

## Overview
This document outlines the backend requirements for {project_name}.

## API Requirements
{backend_requirements}

## Database Requirements
{database_requirements}

## Integration Requirements
{integration_requirements}

## Security Requirements
{security_requirements}

## Technical Dependencies
{dependencies}

## Implementation Guidelines
- Use FastAPI framework for REST API development
- Implement proper error handling and logging
- Follow RESTful API design principles
- Include comprehensive input validation
- Implement appropriate security measures

Please expand each section with detailed technical specifications, API endpoint definitions, database schema design, and implementation notes.
""",
            
            "frontend_template": """
# Frontend Software Requirements Document
# Project: {project_name}

## Overview
This document outlines the frontend requirements for {project_name}.

## User Interface Requirements
{frontend_requirements}

## UI/UX Specifications
{ui_requirements}

## Technical Dependencies
{dependencies}

## Component Architecture
- Implement modular component structure
- Use Angular framework with TypeScript
- Implement responsive design principles
- Include proper state management
- Ensure accessibility compliance

## Implementation Guidelines
- Follow Angular best practices and style guide
- Implement lazy loading for optimal performance
- Use NgRx for state management
- Include comprehensive error handling
- Implement proper routing and navigation

Please expand each section with detailed component specifications, user interaction flows, styling guidelines, and implementation notes.
"""
        }