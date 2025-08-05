#!/usr/bin/env python3
"""
Main orchestrator for the Multi-Agent SRS Processing System.

This system processes Software Requirements Specification documents and generates
complete Angular project code using a multi-agent architecture.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import argparse

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.logging import setup_logging
from agents import RequirementsAnalyzer
from agents.backend import (
    APIDesignerAgent, ModelDeveloperAgent, BusinessLogicAgent,
    IntegrationAgent, DatabaseMigrationAgent
)
from agents.frontend import ComponentDesignerAgent


class MultiAgentOrchestrator:
    """Main orchestrator for the multi-agent system."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the orchestrator."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize agents
        self.requirements_analyzer = RequirementsAnalyzer()
        
        # Backend agents
        self.api_designer = APIDesignerAgent()
        self.model_developer = ModelDeveloperAgent()
        self.business_logic = BusinessLogicAgent()
        self.integration_agent = IntegrationAgent()
        self.database_migration = DatabaseMigrationAgent()
        
        # Frontend agents
        self.component_designer = ComponentDesignerAgent()
        
        self.logger.info("Multi-agent orchestrator initialized")
    
    async def process_srs_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process an SRS document through the multi-agent pipeline.
        
        Args:
            file_path: Path to the SRS document
            
        Returns:
            Complete processing results
        """
        try:
            self.logger.info(f"Starting SRS processing for: {file_path}")
            
            # Stage 1: Requirements Analysis
            self.logger.info("Stage 1: Analyzing requirements...")
            requirements_result = self.requirements_analyzer.process({
                'file_path': file_path
            })
            
            if not requirements_result['success']:
                raise ValueError(f"Requirements analysis failed: {requirements_result.get('error')}")
            
            analysis_data = requirements_result['analysis_result']
            
            # Stage 2: Backend Code Generation
            self.logger.info("Stage 2: Generating backend code...")
            backend_results = await self._generate_backend_code(analysis_data)
            
            # Stage 3: Frontend Code Generation
            self.logger.info("Stage 3: Generating frontend code...")
            frontend_results = await self._generate_frontend_code(analysis_data)
            
            # Stage 4: Integration and Final Assembly
            self.logger.info("Stage 4: Final integration...")
            final_result = self._assemble_final_project(
                analysis_data, backend_results, frontend_results
            )
            
            self.logger.info("SRS processing completed successfully")
            
            return {
                'success': True,
                'requirements_analysis': requirements_result,
                'backend_generation': backend_results,
                'frontend_generation': frontend_results,
                'final_project': final_result
            }
            
        except Exception as e:
            self.logger.error(f"SRS processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'orchestration'
            }
    
    async def _generate_backend_code(self, analysis_data) -> Dict[str, Any]:
        """Generate backend code using backend agents."""
        backend_srd = analysis_data.backend_srd
        dependencies = analysis_data.dependencies
        
        # API Design
        api_result = self.api_designer.process({
            'backend_srd': backend_srd,
            'dependencies': dependencies
        })
        
        if not api_result['success']:
            raise ValueError(f"API design failed: {api_result.get('error')}")
        
        # Model Development
        model_result = self.model_developer.process({
            'backend_srd': backend_srd,
            'api_requirements': api_result['result'].get('api_requirements', [])
        })
        
        if not model_result['success']:
            raise ValueError(f"Model development failed: {model_result.get('error')}")
        
        # Business Logic
        business_result = self.business_logic.process({
            'backend_srd': backend_srd,
            'models': model_result['result']['models']
        })
        
        if not business_result['success']:
            raise ValueError(f"Business logic generation failed: {business_result.get('error')}")
        
        # Integration Services
        integration_result = self.integration_agent.process({
            'backend_srd': backend_srd,
            'dependencies': dependencies
        })
        
        if not integration_result['success']:
            raise ValueError(f"Integration generation failed: {integration_result.get('error')}")
        
        # Database Migrations
        migration_result = self.database_migration.process({
            'models': model_result['result']['models']
        })
        
        if not migration_result['success']:
            raise ValueError(f"Migration generation failed: {migration_result.get('error')}")
        
        return {
            'api_design': api_result['result'],
            'models': model_result['result'],
            'business_logic': business_result['result'],
            'integrations': integration_result['result'],
            'migrations': migration_result['result']
        }
    
    async def _generate_frontend_code(self, analysis_data) -> Dict[str, Any]:
        """Generate frontend code using frontend agents."""
        frontend_srd = analysis_data.frontend_srd
        
        # Component Design
        component_result = self.component_designer.process({
            'frontend_srd': frontend_srd
        })
        
        if not component_result['success']:
            raise ValueError(f"Component design failed: {component_result.get('error')}")
        
        # TODO: Add other frontend agents (ServiceDeveloper, UIImplementation, StateManagement)
        
        return {
            'components': component_result['result']
        }
    
    def _assemble_final_project(self, analysis_data, backend_results: Dict[str, Any], 
                               frontend_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble the final project structure."""
        
        project_structure = {
            'backend': {
                'fastapi_app': backend_results['api_design']['app_file'],
                'models': backend_results['models']['pydantic_models'],
                'database': backend_results['models']['db_models'],
                'business_logic': backend_results['business_logic']['services'],
                'integrations': backend_results['integrations']['services'],
                'migrations': backend_results['migrations']['initial_migration']
            },
            'frontend': {
                'components': frontend_results['components']['components'],
                'routing': frontend_results['components']['routing_config'],
                'lazy_loading': frontend_results['components']['lazy_loading_config']
            },
            'metadata': {
                'dependencies_count': len(analysis_data.dependencies),
                'issues_count': len(analysis_data.issues),
                'frontend_components': len(frontend_results['components']['components']),
                'backend_services': len(backend_results['business_logic']['services'])
            }
        }
        
        # Generate project files
        self._generate_project_files(project_structure)
        
        return project_structure
    
    def _generate_project_files(self, project_structure: Dict[str, Any]):
        """Generate actual project files in the output directory."""
        output_dir = Path("output/generated_project")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Backend files
        backend_dir = output_dir / "backend"
        backend_dir.mkdir(exist_ok=True)
        
        # Frontend files
        frontend_dir = output_dir / "frontend"
        frontend_dir.mkdir(exist_ok=True)
        
        # Generate package.json for frontend
        package_json = {
            "name": "generated-angular-app",
            "version": "1.0.0",
            "scripts": {
                "ng": "ng",
                "start": "ng serve",
                "build": "ng build",
                "test": "ng test"
            },
            "dependencies": {
                "@angular/animations": "^17.0.0",
                "@angular/common": "^17.0.0",
                "@angular/compiler": "^17.0.0",
                "@angular/core": "^17.0.0",
                "@angular/forms": "^17.0.0",
                "@angular/platform-browser": "^17.0.0",
                "@angular/platform-browser-dynamic": "^17.0.0",
                "@angular/router": "^17.0.0",
                "rxjs": "~7.5.0",
                "tslib": "^2.3.0",
                "zone.js": "~0.14.0"
            }
        }
        
        with open(frontend_dir / "package.json", 'w') as f:
            import json
            json.dump(package_json, f, indent=2)
        
        # Generate requirements.txt for backend
        backend_requirements = [
            "fastapi>=0.104.0",
            "uvicorn>=0.24.0",
            "pydantic>=2.5.0",
            "sqlalchemy>=2.0.0",
            "alembic>=1.13.0",
            "python-multipart>=0.0.6"
        ]
        
        with open(backend_dir / "requirements.txt", 'w') as f:
            f.write('\n'.join(backend_requirements))
        
        self.logger.info(f"Project files generated in: {output_dir}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Multi-Agent SRS Processing System")
    parser.add_argument("--srs-file", required=True, help="Path to SRS document")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--config", help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator()
    
    # Process SRS document
    result = await orchestrator.process_srs_document(args.srs_file)
    
    if result['success']:
        print("✅ SRS processing completed successfully!")
        print(f"📊 Generated {result['final_project']['metadata']['frontend_components']} Angular components")
        print(f"🔧 Generated {result['final_project']['metadata']['backend_services']} backend services")
        print(f"📄 Check output/generated_project/ for generated code")
    else:
        print("❌ SRS processing failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())