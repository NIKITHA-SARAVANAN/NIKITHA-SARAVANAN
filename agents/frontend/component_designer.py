"""
Component Designer Agent for generating Angular component sketches with lazy loading.
"""

import time
from typing import Dict, Any, List
import re

from ..base_agent import BaseAgent


class ComponentDesignerAgent(BaseAgent):
    """Agent responsible for designing Angular components."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Component Designer agent."""
        super().__init__("ComponentDesignerAgent", config)
        
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SRD and generate Angular component designs.
        
        Args:
            input_data: Dictionary containing frontend SRD and requirements
            
        Returns:
            Generated Angular components with lazy loading
        """
        start_time = time.time()
        
        try:
            # Validate input
            if not self.validate_input(input_data, ['frontend_srd']):
                return self.handle_error(ValueError("Missing required 'frontend_srd' in input"), "input_validation")
            
            frontend_srd = input_data['frontend_srd']
            
            # Extract component requirements
            component_requirements = self._extract_component_requirements(frontend_srd)
            
            # Generate component hierarchy
            component_hierarchy = self._generate_component_hierarchy(component_requirements)
            
            # Generate component templates
            components = self._generate_component_implementations(component_requirements)
            
            # Generate lazy loading configuration
            lazy_loading_config = self._generate_lazy_loading_config(component_requirements)
            
            # Generate routing configuration
            routing_config = self._generate_routing_config(component_requirements)
            
            result = {
                'component_requirements': component_requirements,
                'component_hierarchy': component_hierarchy,
                'components': components,
                'lazy_loading_config': lazy_loading_config,
                'routing_config': routing_config
            }
            
            # Log action
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "design_components",
                {"frontend_srd_length": len(frontend_srd)},
                {"components_count": len(components)},
                success=True,
                execution_time_ms=execution_time
            )
            
            return {
                'success': True,
                'result': result,
                'execution_time_ms': execution_time
            }
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            self.log_action(
                "design_components",
                input_data,
                {},
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            return self.handle_error(e, "component_design")
    
    def _extract_component_requirements(self, frontend_srd: str) -> List[Dict[str, Any]]:
        """Extract component requirements from frontend SRD."""
        requirements = []
        
        # Common UI patterns
        ui_patterns = {
            'header': r'(?i)(header|navigation|nav|menu)',
            'footer': r'(?i)(footer|bottom)',
            'sidebar': r'(?i)(sidebar|side menu|drawer)',
            'dashboard': r'(?i)(dashboard|home|overview)',
            'form': r'(?i)(form|input|create|edit|update)',
            'list': r'(?i)(list|table|grid|data)',
            'detail': r'(?i)(detail|view|show|display)',
            'modal': r'(?i)(modal|dialog|popup)',
            'card': r'(?i)(card|item|summary)',
            'chart': r'(?i)(chart|graph|visualization)',
            'search': r'(?i)(search|filter|find)',
            'pagination': r'(?i)(pagination|paging)',
            'auth': r'(?i)(login|register|auth|signin)',
            'profile': r'(?i)(profile|account|settings)',
            'notification': r'(?i)(notification|alert|message)'
        }
        
        srd_lower = frontend_srd.lower()
        
        for component_type, pattern in ui_patterns.items():
            if re.search(pattern, srd_lower):
                requirements.append({
                    'type': component_type,
                    'name': f"{component_type.title()}Component",
                    'priority': 'high' if component_type in ['header', 'dashboard', 'auth'] else 'medium',
                    'lazy_loadable': component_type not in ['header', 'footer', 'sidebar'],
                    'features': self._extract_component_features(component_type, srd_lower)
                })
        
        # Always include essential components
        essential_components = [
            {'type': 'app', 'name': 'AppComponent', 'priority': 'high', 'lazy_loadable': False},
            {'type': 'layout', 'name': 'LayoutComponent', 'priority': 'high', 'lazy_loadable': False},
            {'type': 'loading', 'name': 'LoadingComponent', 'priority': 'medium', 'lazy_loadable': False},
            {'type': 'error', 'name': 'ErrorComponent', 'priority': 'medium', 'lazy_loadable': False}
        ]
        
        for essential in essential_components:
            if not any(req['type'] == essential['type'] for req in requirements):
                requirements.append(essential)
        
        return requirements
    
    def _extract_component_features(self, component_type: str, srd_text: str) -> List[str]:
        """Extract specific features for component types."""
        feature_patterns = {
            'header': ['navigation', 'logo', 'user menu', 'search'],
            'dashboard': ['metrics', 'charts', 'quick actions', 'recent items'],
            'form': ['validation', 'submit', 'reset', 'file upload'],
            'list': ['sorting', 'filtering', 'pagination', 'selection'],
            'detail': ['actions', 'related items', 'breadcrumbs'],
            'modal': ['close button', 'backdrop', 'keyboard navigation'],
            'auth': ['form validation', 'password strength', 'remember me'],
            'search': ['autocomplete', 'filters', 'results display']
        }
        
        features = []
        component_features = feature_patterns.get(component_type, [])
        
        for feature in component_features:
            if feature.lower() in srd_text:
                features.append(feature)
        
        return features
    
    def _generate_component_hierarchy(self, requirements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate component hierarchy structure."""
        hierarchy = {
            'app': {
                'component': 'AppComponent',
                'children': {
                    'layout': {
                        'component': 'LayoutComponent',
                        'children': {
                            'header': {'component': 'HeaderComponent'},
                            'main': {
                                'component': 'MainContentComponent',
                                'children': {
                                    'router-outlet': {'lazy_loaded_modules': []}
                                }
                            },
                            'footer': {'component': 'FooterComponent'}
                        }
                    }
                }
            }
        }
        
        # Add lazy-loaded components to router outlet
        lazy_components = [req for req in requirements if req.get('lazy_loadable', False)]
        for comp in lazy_components:
            hierarchy['app']['children']['layout']['children']['main']['children']['router-outlet']['lazy_loaded_modules'].append({
                'name': comp['name'],
                'type': comp['type'],
                'route': f"/{comp['type'].replace('_', '-')}"
            })
        
        return hierarchy
    
    def _generate_component_implementations(self, requirements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate component implementation code."""
        components = []
        
        for req in requirements:
            component = {
                'name': req['name'],
                'type': req['type'],
                'typescript': self._generate_component_typescript(req),
                'template': self._generate_component_template(req),
                'styles': self._generate_component_styles(req),
                'spec': self._generate_component_spec(req),
                'module': self._generate_component_module(req) if req.get('lazy_loadable') else None
            }
            components.append(component)
        
        return components
    
    def _generate_component_typescript(self, requirement: Dict[str, Any]) -> str:
        """Generate TypeScript component code."""
        component_name = requirement['name']
        component_type = requirement['type']
        features = requirement.get('features', [])
        
        typescript_code = f'''import {{ Component, OnInit, OnDestroy }} from '@angular/core';
import {{ Subject }} from 'rxjs';
import {{ takeUntil }} from 'rxjs/operators';

@Component({{
  selector: 'app-{component_type.replace("_", "-")}',
  templateUrl: './{component_type.replace("_", "-")}.component.html',
  styleUrls: ['./{component_type.replace("_", "-")}.component.scss']
}})
export class {component_name} implements OnInit, OnDestroy {{
  private destroy$ = new Subject<void>();
  
  // Component properties
  isLoading = false;
  error: string | null = null;
  
  {self._generate_component_properties(component_type, features)}

  constructor(
    {self._generate_component_dependencies(component_type)}
  ) {{}}

  ngOnInit(): void {{
    this.initializeComponent();
  }}

  ngOnDestroy(): void {{
    this.destroy$.next();
    this.destroy$.complete();
  }}

  private initializeComponent(): void {{
    try {{
      this.isLoading = true;
      {self._generate_initialization_logic(component_type)}
      this.isLoading = false;
    }} catch (error) {{
      this.handleError(error);
    }}
  }}

  {self._generate_component_methods(component_type, features)}

  private handleError(error: any): void {{
    console.error('Component error:', error);
    this.error = error.message || 'An unexpected error occurred';
    this.isLoading = false;
  }}
}}'''
        
        return typescript_code
    
    def _generate_component_properties(self, component_type: str, features: List[str]) -> str:
        """Generate component-specific properties."""
        properties = {
            'header': '''
  // Navigation properties
  navigationItems: any[] = [];
  currentUser: any = null;
  isMenuOpen = false;''',
            
            'dashboard': '''
  // Dashboard properties
  metrics: any[] = [];
  charts: any[] = [];
  recentItems: any[] = [];''',
            
            'form': '''
  // Form properties
  formData: any = {};
  validationErrors: any = {};
  isSubmitting = false;''',
            
            'list': '''
  // List properties
  items: any[] = [];
  totalItems = 0;
  currentPage = 1;
  pageSize = 10;
  sortField = '';
  sortDirection = 'asc';
  filters: any = {};''',
            
            'modal': '''
  // Modal properties
  isVisible = false;
  data: any = null;''',
            
            'auth': '''
  // Authentication properties
  credentials: any = {};
  rememberMe = false;
  passwordStrength = 0;'''
        }
        
        return properties.get(component_type, '  // Component-specific properties')
    
    def _generate_component_dependencies(self, component_type: str) -> str:
        """Generate component constructor dependencies."""
        dependencies = {
            'header': '''private router: Router,
    private authService: AuthService''',
            
            'dashboard': '''private dataService: DataService,
    private router: Router''',
            
            'form': '''private formBuilder: FormBuilder,
    private validationService: ValidationService''',
            
            'list': '''private dataService: DataService,
    private router: Router''',
            
            'modal': '''private activeModal: NgbActiveModal''',
            
            'auth': '''private authService: AuthService,
    private router: Router,
    private formBuilder: FormBuilder'''
        }
        
        return dependencies.get(component_type, '// No specific dependencies')
    
    def _generate_initialization_logic(self, component_type: str) -> str:
        """Generate component initialization logic."""
        logic = {
            'header': '''
      this.loadNavigationItems();
      this.loadCurrentUser();''',
            
            'dashboard': '''
      this.loadMetrics();
      this.loadCharts();
      this.loadRecentItems();''',
            
            'form': '''
      this.initializeForm();
      this.setupValidation();''',
            
            'list': '''
      this.loadItems();''',
            
            'auth': '''
      this.setupAuthForm();'''
        }
        
        return logic.get(component_type, '      // Component initialization')
    
    def _generate_component_methods(self, component_type: str, features: List[str]) -> str:
        """Generate component-specific methods."""
        methods = {
            'header': '''
  toggleMenu(): void {
    this.isMenuOpen = !this.isMenuOpen;
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  private loadNavigationItems(): void {
    // Load navigation items
  }

  private loadCurrentUser(): void {
    // Load current user data
  }''',
            
            'dashboard': '''
  refreshData(): void {
    this.initializeComponent();
  }

  navigateToDetail(item: any): void {
    this.router.navigate(['/detail', item.id]);
  }

  private loadMetrics(): void {
    // Load dashboard metrics
  }

  private loadCharts(): void {
    // Load chart data
  }

  private loadRecentItems(): void {
    // Load recent items
  }''',
            
            'form': '''
  onSubmit(): void {
    if (this.isValid()) {
      this.isSubmitting = true;
      // Submit form logic
      this.isSubmitting = false;
    }
  }

  onReset(): void {
    this.formData = {};
    this.validationErrors = {};
  }

  private isValid(): boolean {
    // Form validation logic
    return true;
  }

  private initializeForm(): void {
    // Initialize form
  }

  private setupValidation(): void {
    // Setup validation rules
  }''',
            
            'list': '''
  onSort(field: string): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    this.loadItems();
  }

  onFilter(filters: any): void {
    this.filters = filters;
    this.currentPage = 1;
    this.loadItems();
  }

  onPageChange(page: number): void {
    this.currentPage = page;
    this.loadItems();
  }

  private loadItems(): void {
    // Load list items with pagination and filtering
  }''',
            
            'modal': '''
  close(): void {
    this.activeModal.close();
  }

  save(): void {
    // Save logic
    this.activeModal.close(this.data);
  }''',
            
            'auth': '''
  onLogin(): void {
    if (this.isValidCredentials()) {
      this.isSubmitting = true;
      this.authService.login(this.credentials, this.rememberMe)
        .pipe(takeUntil(this.destroy$))
        .subscribe({
          next: () => {
            this.router.navigate(['/dashboard']);
          },
          error: (error) => {
            this.handleError(error);
          }
        });
    }
  }

  private isValidCredentials(): boolean {
    // Validate login credentials
    return true;
  }

  private setupAuthForm(): void {
    // Setup authentication form
  }'''
        }
        
        return methods.get(component_type, '''
  // Component-specific methods''')
    
    def _generate_component_template(self, requirement: Dict[str, Any]) -> str:
        """Generate component HTML template."""
        component_type = requirement['type']
        component_name = requirement['name']
        
        templates = {
            'app': '''<div class="app-container">
  <app-layout></app-layout>
</div>''',
            
            'layout': '''<div class="layout-container">
  <app-header></app-header>
  <main class="main-content">
    <router-outlet></router-outlet>
  </main>
  <app-footer></app-footer>
</div>''',
            
            'header': '''<header class="header">
  <div class="header-content">
    <div class="logo">
      <h1>App Logo</h1>
    </div>
    <nav class="navigation" [class.open]="isMenuOpen">
      <ul class="nav-items">
        <li *ngFor="let item of navigationItems" class="nav-item">
          <a [routerLink]="item.route" routerLinkActive="active">
            {{ item.label }}
          </a>
        </li>
      </ul>
    </nav>
    <div class="user-menu" *ngIf="currentUser">
      <button class="user-button" (click)="toggleMenu()">
        {{ currentUser.name }}
      </button>
      <div class="dropdown-menu" *ngIf="isMenuOpen">
        <a routerLink="/profile">Profile</a>
        <a routerLink="/settings">Settings</a>
        <button (click)="logout()">Logout</button>
      </div>
    </div>
  </div>
</header>''',
            
            'dashboard': '''<div class="dashboard">
  <div class="dashboard-header">
    <h1>Dashboard</h1>
    <button class="refresh-btn" (click)="refreshData()" [disabled]="isLoading">
      Refresh
    </button>
  </div>
  
  <div class="metrics-grid" *ngIf="metrics.length">
    <div class="metric-card" *ngFor="let metric of metrics">
      <h3>{{ metric.title }}</h3>
      <div class="metric-value">{{ metric.value }}</div>
    </div>
  </div>
  
  <div class="charts-section" *ngIf="charts.length">
    <h2>Analytics</h2>
    <div class="charts-grid">
      <div class="chart-container" *ngFor="let chart of charts">
        <!-- Chart component would go here -->
      </div>
    </div>
  </div>
  
  <div class="recent-items" *ngIf="recentItems.length">
    <h2>Recent Activity</h2>
    <div class="items-list">
      <div class="item" *ngFor="let item of recentItems" (click)="navigateToDetail(item)">
        {{ item.title }}
      </div>
    </div>
  </div>
</div>''',
            
            'form': '''<form class="form-container" (ngSubmit)="onSubmit()" *ngIf="!isLoading">
  <div class="form-header">
    <h2>Form Title</h2>
  </div>
  
  <div class="form-fields">
    <!-- Form fields would be generated based on requirements -->
    <div class="field-group">
      <label for="example">Example Field</label>
      <input type="text" id="example" [(ngModel)]="formData.example" name="example">
      <div class="error" *ngIf="validationErrors.example">
        {{ validationErrors.example }}
      </div>
    </div>
  </div>
  
  <div class="form-actions">
    <button type="button" class="btn-secondary" (click)="onReset()">Reset</button>
    <button type="submit" class="btn-primary" [disabled]="isSubmitting">
      {{ isSubmitting ? 'Submitting...' : 'Submit' }}
    </button>
  </div>
</form>''',
            
            'list': '''<div class="list-container">
  <div class="list-header">
    <h2>Items</h2>
    <div class="list-controls">
      <!-- Search and filters -->
    </div>
  </div>
  
  <div class="list-content" *ngIf="!isLoading">
    <table class="data-table">
      <thead>
        <tr>
          <th *ngFor="let column of columns" 
              (click)="onSort(column.field)"
              [class.sortable]="column.sortable">
            {{ column.label }}
            <i class="sort-icon" 
               [class.asc]="sortField === column.field && sortDirection === 'asc'"
               [class.desc]="sortField === column.field && sortDirection === 'desc'">
            </i>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr *ngFor="let item of items">
          <td *ngFor="let column of columns">
            {{ item[column.field] }}
          </td>
        </tr>
      </tbody>
    </table>
    
    <!-- Pagination -->
    <div class="pagination" *ngIf="totalItems > pageSize">
      <!-- Pagination controls -->
    </div>
  </div>
</div>''',
            
            'loading': '''<div class="loading-container">
  <div class="spinner"></div>
  <p>Loading...</p>
</div>''',
            
            'error': '''<div class="error-container">
  <div class="error-icon">⚠️</div>
  <h2>Something went wrong</h2>
  <p>{{ error || 'An unexpected error occurred' }}</p>
  <button class="retry-btn" (click)="retry()">Try Again</button>
</div>'''
        }
        
        return templates.get(component_type, f'''<div class="{component_type}-container">
  <h2>{component_name}</h2>
  <p>Component content goes here</p>
</div>''')
    
    def _generate_component_styles(self, requirement: Dict[str, Any]) -> str:
        """Generate component SCSS styles."""
        component_type = requirement['type']
        
        styles = {
            'app': '''.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}''',
            
            'layout': '''.layout-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  padding: 20px;
}

@media (max-width: 768px) {
  .main-content {
    padding: 10px;
  }
}''',
            
            'header': '''.header {
  background-color: var(--primary-color);
  color: white;
  padding: 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  height: 60px;
}

.logo h1 {
  margin: 0;
  font-size: 1.5rem;
}

.navigation {
  display: flex;
  align-items: center;
}

.nav-items {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-item {
  margin-left: 20px;
}

.nav-item a {
  color: white;
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 4px;
  transition: background-color 0.3s;
  
  &:hover, &.active {
    background-color: rgba(255,255,255,0.1);
  }
}

.user-menu {
  position: relative;
}

.user-button {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px 16px;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  color: black;
  border-radius: 4px;
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  min-width: 150px;
  
  a, button {
    display: block;
    width: 100%;
    padding: 8px 16px;
    text-decoration: none;
    color: black;
    border: none;
    background: none;
    text-align: left;
    cursor: pointer;
    
    &:hover {
      background-color: #f5f5f5;
    }
  }
}

@media (max-width: 768px) {
  .header-content {
    padding: 0 10px;
  }
  
  .navigation {
    display: none;
    
    &.open {
      display: block;
      position: absolute;
      top: 60px;
      left: 0;
      right: 0;
      background: var(--primary-color);
      padding: 20px;
    }
  }
  
  .nav-items {
    flex-direction: column;
  }
  
  .nav-item {
    margin: 5px 0;
  }
}''',
            
            'dashboard': '''.dashboard {
  padding: 20px;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.refresh-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  
  h3 {
    margin: 0 0 10px 0;
    color: #666;
    font-size: 0.9rem;
  }
  
  .metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: var(--primary-color);
  }
}

.charts-section, .recent-items {
  margin-bottom: 30px;
  
  h2 {
    margin-bottom: 20px;
  }
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  height: 300px;
}

.items-list {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.item {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  
  &:hover {
    background-color: #f5f5f5;
  }
  
  &:last-child {
    border-bottom: none;
  }
}''',
            
            'form': '''.form-container {
  max-width: 600px;
  margin: 0 auto;
  background: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.form-header {
  margin-bottom: 30px;
  
  h2 {
    margin: 0;
    color: #333;
  }
}

.form-fields {
  margin-bottom: 30px;
}

.field-group {
  margin-bottom: 20px;
  
  label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #333;
  }
  
  input, select, textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    
    &:focus {
      outline: none;
      border-color: var(--primary-color);
      box-shadow: 0 0 0 3px rgba(var(--primary-color-rgb), 0.1);
    }
    
    &.error {
      border-color: #e74c3c;
    }
  }
  
  .error {
    color: #e74c3c;
    font-size: 12px;
    margin-top: 5px;
  }
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-primary, .btn-secondary {
  padding: 12px 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-secondary {
  background: #f8f9fa;
  color: #666;
  border: 1px solid #ddd;
}'''
        }
        
        return styles.get(component_type, f'''.{component_type}-container {{
  padding: 20px;
}}''')
    
    def _generate_component_spec(self, requirement: Dict[str, Any]) -> str:
        """Generate component test specification."""
        component_name = requirement['name']
        component_type = requirement['type']
        
        return f'''import {{ ComponentFixture, TestBed }} from '@angular/core/testing';
import {{ {component_name} }} from './{component_type.replace("_", "-")}.component';

describe('{component_name}', () => {{
  let component: {component_name};
  let fixture: ComponentFixture<{component_name}>;

  beforeEach(async () => {{
    await TestBed.configureTestingModule({{
      declarations: [ {component_name} ]
    }})
    .compileComponents();

    fixture = TestBed.createComponent({component_name});
    component = fixture.componentInstance;
    fixture.detectChanges();
  }});

  it('should create', () => {{
    expect(component).toBeTruthy();
  }});

  it('should initialize component properties', () => {{
    expect(component.isLoading).toBeDefined();
    expect(component.error).toBeNull();
  }});

  it('should handle errors gracefully', () => {{
    const error = new Error('Test error');
    component['handleError'](error);
    expect(component.error).toBe('Test error');
    expect(component.isLoading).toBeFalsy();
  }});

  // Add component-specific tests
  {self._generate_specific_tests(component_type)}
}});'''
    
    def _generate_specific_tests(self, component_type: str) -> str:
        """Generate component-specific test cases."""
        tests = {
            'header': '''
  it('should toggle menu', () => {
    expect(component.isMenuOpen).toBeFalsy();
    component.toggleMenu();
    expect(component.isMenuOpen).toBeTruthy();
  });''',
            
            'form': '''
  it('should reset form data', () => {
    component.formData = { test: 'value' };
    component.onReset();
    expect(component.formData).toEqual({});
  });''',
            
            'list': '''
  it('should sort items', () => {
    component.onSort('name');
    expect(component.sortField).toBe('name');
    expect(component.sortDirection).toBe('asc');
  });'''
        }
        
        return tests.get(component_type, '''
  // Add component-specific tests here''')
    
    def _generate_component_module(self, requirement: Dict[str, Any]) -> str:
        """Generate lazy-loaded module for component."""
        if not requirement.get('lazy_loadable'):
            return None
        
        component_name = requirement['name']
        component_type = requirement['type']
        module_name = f"{component_type.title()}Module"
        
        return f'''import {{ NgModule }} from '@angular/core';
import {{ CommonModule }} from '@angular/common';
import {{ RouterModule, Routes }} from '@angular/router';
import {{ FormsModule, ReactiveFormsModule }} from '@angular/forms';

import {{ {component_name} }} from './{component_type.replace("_", "-")}.component';

const routes: Routes = [
  {{
    path: '',
    component: {component_name}
  }}
];

@NgModule({{
  declarations: [
    {component_name}
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule.forChild(routes)
  ],
  exports: [
    {component_name}
  ]
}})
export class {module_name} {{ }}'''
    
    def _generate_lazy_loading_config(self, requirements: List[Dict[str, Any]]) -> str:
        """Generate lazy loading configuration."""
        lazy_routes = []
        
        for req in requirements:
            if req.get('lazy_loadable'):
                route_path = req['type'].replace('_', '-')
                module_path = f"./{req['type'].replace('_', '-')}/{req['type'].replace('_', '-')}.module"
                module_name = f"{req['type'].title()}Module"
                
                lazy_routes.append(f'''  {{
    path: '{route_path}',
    loadChildren: () => import('{module_path}').then(m => m.{module_name})
  }}''')
        
        return f'''// Lazy loading configuration
export const LAZY_ROUTES = [
{chr(10).join(lazy_routes)}
];'''
    
    def _generate_routing_config(self, requirements: List[Dict[str, Any]]) -> str:
        """Generate main routing configuration."""
        routes = []
        
        # Add default routes
        routes.append("  { path: '', redirectTo: '/dashboard', pathMatch: 'full' }")
        
        # Add component routes
        for req in requirements:
            if req.get('lazy_loadable'):
                route_path = req['type'].replace('_', '-')
                routes.append(f"  {{ path: '{route_path}', loadChildren: () => import('./{route_path}/{route_path}.module').then(m => m.{req['type'].title()}Module) }}")
        
        # Add wildcard route
        routes.append("  { path: '**', redirectTo: '/dashboard' }")
        
        return f'''import {{ NgModule }} from '@angular/core';
import {{ RouterModule, Routes }} from '@angular/router';

const routes: Routes = [
{chr(10).join(routes)}
];

@NgModule({{
  imports: [RouterModule.forRoot(routes, {{
    enableTracing: false, // Set to true for debugging
    preloadingStrategy: PreloadAllModules
  }})],
  exports: [RouterModule]
}})
export class AppRoutingModule {{ }}'''