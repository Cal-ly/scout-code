---
updated: 2025-10-04, 19:30
---

## Cost Tracker Service - Claude Code Instructions

## Context & Objective

You're building the **Cost Tracker Service** for Scout, a critical component that monitors API usage costs across all modules, enforces budget limits, provides analytics, and prevents cost overruns. This service integrates tightly with the LLM Service and other cost-generating components.

## Module Specifications

**Purpose**: Track, analyze, and control costs across all billable services (LLMs, APIs, cloud resources) with real-time monitoring, predictive alerts, and automatic shutoffs to prevent budget overruns.

**Key Responsibilities**:
1. Real-time cost tracking across all services
2. Budget enforcement with hard and soft limits
3. Cost allocation by module, job, and user
4. Predictive cost analysis and alerts
5. Historical cost reporting and analytics
6. Automatic service throttling near limits
7. Cost optimization recommendations

## Technical Requirements

**Dependencies**:
- FastAPI framework
- Pydantic for data validation
- SQLAlchemy for cost history storage
- Redis for real-time counters
- Pandas for cost analytics
- APScheduler for periodic tasks

**File Structure**:
```
scout/
├── app/
│   ├── services/
│   │   ├── cost_tracker.py         # Main cost tracking service
│   │   ├── cost_analyzer.py        # Cost analysis and reporting
│   │   ├── budget_enforcer.py      # Budget limit enforcement
│   │   └── cost_optimizer.py       # Optimization recommendations
│   ├── models/
│   │   └── cost_tracking.py        # Cost tracking models
│   ├── database/
│   │   └── cost_tables.py          # SQLAlchemy cost tables
│   └── schedulers/
│       └── cost_tasks.py           # Scheduled cost tasks
├── data/
│   ├── cost_history/                # Historical cost data
│   └── cost_reports/                # Generated reports
└── tests/
    └── test_cost_tracker.py
```

## Data Models to Implement

Create these models in `app/models/cost_tracking.py`:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta, date
from enum import Enum
from decimal import Decimal
import uuid

class ServiceType(str, Enum):
    LLM = "llm"
    VECTOR_DB = "vector_db"
    WEB_SCRAPING = "web_scraping"
    CLOUD_STORAGE = "cloud_storage"
    COMPUTE = "compute"
    EMAIL = "email"
    SMS = "sms"
    OTHER = "other"

class CostCategory(str, Enum):
    API_CALLS = "api_calls"
    STORAGE = "storage"
    COMPUTE = "compute"
    NETWORK = "network"
    OTHER = "other"

class BillingPeriod(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class CostEntry(BaseModel):
    """Individual cost entry"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Service identification
    service_type: ServiceType
    service_name: str  # e.g., "anthropic", "openai", "chromadb"
    category: CostCategory
    
    # Cost details
    amount: Decimal = Field(decimal_places=6)  # Support micro-transactions
    currency: str = "USD"
    
    # Usage details
    units: float  # tokens, requests, bytes, etc.
    unit_type: str  # "tokens", "requests", "GB", etc.
    unit_cost: Decimal  # Cost per unit
    
    # Attribution
    module: Optional[str] = None  # Which Scout module
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = {}
    tags: List[str] = []
    
    # Billing
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    invoice_id: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError("Cost amount cannot be negative")
        return v

class CostSummary(BaseModel):
    """Cost summary for a period"""
    period_start: datetime
    period_end: datetime
    
    # Totals
    total_cost: Decimal
    total_units: Dict[str, float]  # unit_type: total_units
    transaction_count: int
    
    # Breakdown by service
    by_service: Dict[ServiceType, Decimal]
    by_service_name: Dict[str, Decimal]
    by_category: Dict[CostCategory, Decimal]
    by_module: Dict[str, Decimal]
    
    # Top consumers
    top_jobs: List[Dict[str, Any]]  # job_id, cost, percentage
    top_modules: List[Dict[str, Any]]
    
    # Trends
    cost_trend: float  # Percentage change from previous period
    projection: Decimal  # Projected cost for full period
    
    # Budget status
    budget_limit: Decimal
    budget_used: Decimal
    budget_remaining: Decimal
    budget_percentage: float

class BudgetConfig(BaseModel):
    """Budget configuration"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    active: bool = True
    
    # Limits
    amount: Decimal
    period: BillingPeriod
    
    # Scope
    service_types: Optional[List[ServiceType]] = None  # None = all
    services: Optional[List[str]] = None  # Specific service names
    modules: Optional[List[str]] = None
    
    # Actions
    soft_limit_percentage: float = 80.0  # Warning threshold
    hard_limit_percentage: float = 100.0  # Stop threshold
    
    # Notifications
    alert_emails: List[str] = []
    alert_webhooks: List[str] = []
    
    # Override settings
    allow_override: bool = False
    override_password: Optional[str] = None
    override_expiry: Optional[datetime] = None
    
    # Current usage
    current_usage: Decimal = Decimal("0")
    last_reset: datetime = Field(default_factory=datetime.now)
    
    @validator('soft_limit_percentage')
    def validate_soft_limit(cls, v, values):
        if 'hard_limit_percentage' in values:
            if v >= values['hard_limit_percentage']:
                raise ValueError("Soft limit must be less than hard limit")
        return v

class CostAlert(BaseModel):
    """Cost alert notification"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    
    severity: AlertSeverity
    budget_id: str
    budget_name: str
    
    # Alert details
    message: str
    current_cost: Decimal
    budget_limit: Decimal
    percentage_used: float
    
    # Projection
    projected_overrun: Optional[Decimal] = None
    projected_overrun_date: Optional[datetime] = None
    
    # Action taken
    action_taken: str  # "notification_sent", "service_throttled", "service_stopped"
    services_affected: List[str] = []
    
    # Acknowledgment
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

class CostProjection(BaseModel):
    """Cost projection analysis"""
    projection_date: datetime
    period: BillingPeriod
    
    # Historical data
    historical_costs: List[Decimal]
    historical_dates: List[datetime]
    
    # Projections
    projected_cost: Decimal
    confidence_interval: tuple[Decimal, Decimal]  # (low, high)
    confidence_level: float = 0.95
    
    # Trend analysis
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_percentage: float
    seasonality_detected: bool
    
    # Risk assessment
    budget_overrun_probability: float
    expected_overrun_date: Optional[datetime]
    expected_overrun_amount: Optional[Decimal]
    
    # Recommendations
    recommended_daily_limit: Decimal
    recommended_throttle_percentage: float
    optimization_potential: Decimal  # Potential savings

class OptimizationRecommendation(BaseModel):
    """Cost optimization recommendation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Recommendation details
    title: str
    description: str
    category: str  # "model_selection", "caching", "batch_processing", etc.
    
    # Impact
    potential_savings: Decimal
    savings_percentage: float
    implementation_effort: str  # "low", "medium", "high"
    
    # Specifics
    affected_service: ServiceType
    affected_modules: List[str]
    
    # Implementation
    action_items: List[str]
    code_changes_required: bool
    estimated_implementation_time: str  # "1 hour", "1 day", etc.
    
    # Status
    status: str = "pending"  # "pending", "implemented", "rejected"
    implemented_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None

class ServiceUsageMetrics(BaseModel):
    """Detailed service usage metrics"""
    service_type: ServiceType
    service_name: str
    period: BillingPeriod
    
    # Usage metrics
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    # Cost metrics
    total_cost: Decimal
    average_cost_per_request: Decimal
    median_cost_per_request: Decimal
    
    # Performance metrics
    average_latency: float  # seconds
    p95_latency: float
    p99_latency: float
    
    # Efficiency metrics
    cache_hit_rate: float
    error_rate: float
    retry_rate: float
    
    # Patterns
    peak_usage_hour: int  # 0-23
    peak_usage_day: str  # Day of week
    usage_pattern: str  # "steady", "bursty", "growing"

class CostReport(BaseModel):
    """Generated cost report"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = Field(default_factory=datetime.now)
    
    # Report parameters
    report_type: str  # "daily", "weekly", "monthly", "custom"
    period_start: datetime
    period_end: datetime
    
    # Content
    summary: CostSummary
    service_metrics: List[ServiceUsageMetrics]
    projections: CostProjection
    recommendations: List[OptimizationRecommendation]
    alerts: List[CostAlert]
    
    # Visualizations (base64 encoded)
    charts: Dict[str, str] = {}  # chart_name: base64_image
    
    # Export
    export_format: str = "json"  # "json", "csv", "pdf", "html"
    export_path: Optional[str] = None
    
    # Distribution
    recipients: List[str] = []
    sent_at: Optional[datetime] = None
```

## Cost Tracker Implementation

Create the main service in `app/services/cost_tracker.py`:

```python
import asyncio
import json
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta, date
from decimal import Decimal
import logging
from collections import defaultdict
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from redis import Redis
import pickle

from app.models.cost_tracking import (
    CostEntry, CostSummary, BudgetConfig, CostAlert,
    CostProjection, OptimizationRecommendation, ServiceUsageMetrics,
    CostReport, ServiceType, CostCategory, BillingPeriod,
    AlertSeverity
)
from app.database.cost_tables import CostEntryDB, BudgetDB
from app.services.cost_analyzer import CostAnalyzer
from app.services.budget_enforcer import BudgetEnforcer
from app.services.cost_optimizer import CostOptimizer
from app.config.settings import settings
from app.database.session import get_db

logger = logging.getLogger(__name__)

class CostTracker:
    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        db_session: Optional[Session] = None
    ):
        # Initialize storage
        self.redis = redis_client or Redis.from_url(
            settings.redis_url or "redis://localhost:6379"
        )
        self.db = db_session
        
        # Initialize components
        self.analyzer = CostAnalyzer()
        self.enforcer = BudgetEnforcer()
        self.optimizer = CostOptimizer()
        
        # Cache for real-time tracking
        self.current_costs = defaultdict(Decimal)  # service -> cost
        self.current_period_start = self._get_period_start(BillingPeriod.DAILY)
        
        # Budget configurations
        self.budgets: List[BudgetConfig] = []
        self.load_budgets()
        
        # Alert queue
        self.pending_alerts: List[CostAlert] = []
        
        # Service rate limiters
        self.service_limiters = {}
        
        # Metrics
        self.metrics = defaultdict(lambda: {
            'requests': 0,
            'costs': Decimal('0'),
            'errors': 0,
            'last_reset': datetime.now()
        })
    
    async def track_cost(
        self,
        service_type: ServiceType,
        service_name: str,
        amount: Union[float, Decimal],
        units: float,
        unit_type: str,
        category: CostCategory = CostCategory.API_CALLS,
        module: Optional[str] = None,
        job_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> CostEntry:
        """Track a cost entry"""
        
        # Create cost entry
        amount_decimal = Decimal(str(amount))
        unit_cost = amount_decimal / Decimal(str(units)) if units > 0 else Decimal('0')
        
        entry = CostEntry(
            service_type=service_type,
            service_name=service_name,
            category=category,
            amount=amount_decimal,
            units=units,
            unit_type=unit_type,
            unit_cost=unit_cost,
            module=module,
            job_id=job_id,
            metadata=metadata or {}
        )
        
        # Update real-time counters
        await self._update_realtime_counters(entry)
        
        # Check budgets
        budget_status = await self._check_budgets(entry)
        
        # Handle budget violations
        if budget_status['hard_limit_exceeded']:
            await self._handle_hard_limit(entry, budget_status)
            raise Exception(f"Budget hard limit exceeded for {service_name}")
        
        elif budget_status['soft_limit_exceeded']:
            await self._handle_soft_limit(entry, budget_status)
        
        # Store entry
        await self._store_entry(entry)
        
        # Update metrics
        self._update_metrics(entry)
        
        # Check for optimization opportunities
        if self.metrics[service_name]['requests'] % 100 == 0:
            asyncio.create_task(self._check_optimizations(service_name))
        
        return entry
    
    async def _update_realtime_counters(self, entry: CostEntry):
        """Update Redis counters for real-time tracking"""
        # Update total cost
        key_total = f"cost:total:{datetime.now().strftime('%Y%m%d')}"
        await self.redis.incrbyfloat(key_total, float(entry.amount))
        
        # Update by service
        key_service = f"cost:service:{entry.service_name}:{datetime.now().strftime('%Y%m%d')}"
        await self.redis.incrbyfloat(key_service, float(entry.amount))
        
        # Update by module
        if entry.module:
            key_module = f"cost:module:{entry.module}:{datetime.now().strftime('%Y%m%d')}"
            await self.redis.incrbyfloat(key_module, float(entry.amount))
        
        # Set expiry (7 days)
        for key in [key_total, key_service]:
            await self.redis.expire(key, 7 * 24 * 3600)
    
    async def _check_budgets(self, entry: CostEntry) -> Dict[str, Any]:
        """Check if entry violates any budgets"""
        status = {
            'soft_limit_exceeded': False,
            'hard_limit_exceeded': False,
            'budgets_affected': [],
            'current_usage': {}
        }
        
        for budget in self.budgets:
            if not budget.active:
                continue
            
            # Check if budget applies to this entry
            if not self._budget_applies(budget, entry):
                continue
            
            # Get current usage for this budget
            current_usage = await self.get_budget_usage(budget)
            new_usage = current_usage + entry.amount
            
            # Calculate percentage
            usage_percentage = float(new_usage / budget.amount * 100)
            
            status['current_usage'][budget.name] = {
                'amount': float(new_usage),
                'percentage': usage_percentage
            }
            
            # Check limits
            if usage_percentage >= budget.hard_limit_percentage:
                status['hard_limit_exceeded'] = True
                status['budgets_affected'].append(budget)
            elif usage_percentage >= budget.soft_limit_percentage:
                status['soft_limit_exceeded'] = True
                status['budgets_affected'].append(budget)
            
            # Update budget usage
            budget.current_usage = new_usage
        
        return status
    
    def _budget_applies(self, budget: BudgetConfig, entry: CostEntry) -> bool:
        """Check if budget applies to entry"""
        # Check service type
        if budget.service_types and entry.service_type not in budget.service_types:
            return False
        
        # Check service name
        if budget.services and entry.service_name not in budget.services:
            return False
        
        # Check module
        if budget.modules and entry.module and entry.module not in budget.modules:
            return False
        
        return True
    
    async def get_budget_usage(self, budget: BudgetConfig) -> Decimal:
        """Get current usage for a budget"""
        # Determine period start
        period_start = self._get_period_start(budget.period)
        
        # Build Redis key pattern
        if budget.service_types:
            # Sum across specific services
            total = Decimal('0')
            for service_type in budget.service_types:
                key = f"cost:service:*:{period_start.strftime('%Y%m%d')}"
                keys = await self.redis.keys(key)
                for k in keys:
                    value = await self.redis.get(k)
                    if value:
                        total += Decimal(value)
            return total
        else:
            # Get total for period
            key = f"cost:total:{period_start.strftime('%Y%m%d')}"
            value = await self.redis.get(key)
            return Decimal(value) if value else Decimal('0')
    
    async def _handle_hard_limit(self, entry: CostEntry, budget_status: Dict):
        """Handle hard limit exceeded"""
        for budget in budget_status['budgets_affected']:
            # Create alert
            alert = CostAlert(
                severity=AlertSeverity.EMERGENCY,
                budget_id=budget.id,
                budget_name=budget.name,
                message=f"EMERGENCY: Budget '{budget.name}' hard limit exceeded!",
                current_cost=budget.current_usage,
                budget_limit=budget.amount,
                percentage_used=float(budget.current_usage / budget.amount * 100),
                action_taken="service_stopped",
                services_affected=[entry.service_name]
            )
            
            # Send immediate notification
            await self._send_alert(alert)
            
            # Stop service
            await self._stop_service(entry.service_name)
            
            # Log critical event
            logger.critical(
                f"Budget hard limit exceeded - Service: {entry.service_name}, "
                f"Budget: {budget.name}, Usage: ${budget.current_usage:.2f}/${budget.amount:.2f}"
            )
    
    async def _handle_soft_limit(self, entry: CostEntry, budget_status: Dict):
        """Handle soft limit exceeded"""
        for budget in budget_status['budgets_affected']:
            # Check if alert already sent recently
            alert_key = f"alert:soft:{budget.id}:{datetime.now().strftime('%Y%m%d')}"
            if await self.redis.exists(alert_key):
                continue
            
            # Create alert
            alert = CostAlert(
                severity=AlertSeverity.WARNING,
                budget_id=budget.id,
                budget_name=budget.name,
                message=f"Warning: Budget '{budget.name}' approaching limit",
                current_cost=budget.current_usage,
                budget_limit=budget.amount,
                percentage_used=float(budget.current_usage / budget.amount * 100),
                action_taken="notification_sent",
                projected_overrun=await self._project_overrun(budget)
            )
            
            # Send notification
            await self._send_alert(alert)
            
            # Mark alert as sent
            await self.redis.setex(alert_key, 3600, '1')  # Don't resend for 1 hour
            
            # Consider throttling
            if budget.current_usage / budget.amount > 0.9:
                await self._throttle_service(entry.service_name, 0.5)  # 50% throttle
    
    async def _store_entry(self, entry: CostEntry):
        """Store cost entry in database"""
        if self.db:
            db_entry = CostEntryDB(
                id=entry.id,
                timestamp=entry.timestamp,
                service_type=entry.service_type.value,
                service_name=entry.service_name,
                category=entry.category.value,
                amount=float(entry.amount),
                units=entry.units,
                unit_type=entry.unit_type,
                module=entry.module,
                job_id=entry.job_id,
                metadata=json.dumps(entry.metadata)
            )
            
            self.db.add(db_entry)
            await self.db.commit()
        
        # Also store in Redis for quick access (24 hour TTL)
        entry_key = f"entry:{entry.id}"
        await self.redis.setex(
            entry_key,
            86400,
            pickle.dumps(entry)
        )
    
    def _update_metrics(self, entry: CostEntry):
        """Update service metrics"""
        metrics = self.metrics[entry.service_name]
        metrics['requests'] += 1
        metrics['costs'] += entry.amount
        
        # Update hourly metrics
        hour_key = datetime.now().strftime('%Y%m%d%H')
        hourly = metrics.get('hourly', {})
        if hour_key not in hourly:
            hourly[hour_key] = {'requests': 0, 'cost': Decimal('0')}
        hourly[hour_key]['requests'] += 1
        hourly[hour_key]['cost'] += entry.amount
        metrics['hourly'] = hourly
    
    async def get_summary(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> CostSummary:
        """Get cost summary for period"""
        # Fetch entries from database
        entries = await self._fetch_entries(period_start, period_end)
        
        # Calculate totals
        total_cost = sum(e.amount for e in entries)
        
        # Group by dimensions
        by_service = defaultdict(Decimal)
        by_category = defaultdict(Decimal)
        by_module = defaultdict(Decimal)
        units = defaultdict(float)
        
        for entry in entries:
            by_service[entry.service_type] += entry.amount
            by_category[entry.category] += entry.amount
            if entry.module:
                by_module[entry.module] += entry.amount
            units[entry.unit_type] += entry.units
        
        # Get top consumers
        job_costs = defaultdict(Decimal)
        for entry in entries:
            if entry.job_id:
                job_costs[entry.job_id] += entry.amount
        
        top_jobs = sorted(
            [{'job_id': k, 'cost': float(v), 'percentage': float(v/total_cost*100)}
             for k, v in job_costs.items()],
            key=lambda x: x['cost'],
            reverse=True
        )[:10]
        
        # Calculate trend
        previous_period_start = period_start - (period_end - period_start)
        previous_entries = await self._fetch_entries(previous_period_start, period_start)
        previous_total = sum(e.amount for e in previous_entries)
        
        if previous_total > 0:
            cost_trend = float((total_cost - previous_total) / previous_total * 100)
        else:
            cost_trend = 0
        
        # Get budget status
        main_budget = self.budgets[0] if self.budgets else None
        
        return CostSummary(
            period_start=period_start,
            period_end=period_end,
            total_cost=total_cost,
            total_units=dict(units),
            transaction_count=len(entries),
            by_service={k: v for k, v in by_service.items()},
            by_service_name={},  # TODO: Implement
            by_category={k: v for k, v in by_category.items()},
            by_module={k: v for k, v in by_module.items()},
            top_jobs=top_jobs,
            top_modules=[],  # TODO: Implement
            cost_trend=cost_trend,
            projection=await self._project_cost(entries, period_end),
            budget_limit=main_budget.amount if main_budget else Decimal('0'),
            budget_used=main_budget.current_usage if main_budget else Decimal('0'),
            budget_remaining=(main_budget.amount - main_budget.current_usage) if main_budget else Decimal('0'),
            budget_percentage=float(main_budget.current_usage / main_budget.amount * 100) if main_budget and main_budget.amount > 0 else 0
        )
    
    async def generate_report(
        self,
        report_type: str = "daily",
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None
    ) -> CostReport:
        """Generate comprehensive cost report"""
        # Determine period
        if report_type == "daily":
            period_end = datetime.now()
            period_start = period_end - timedelta(days=1)
        elif report_type == "weekly":
            period_end = datetime.now()
            period_start = period_end - timedelta(days=7)
        elif report_type == "monthly":
            period_end = datetime.now()
            period_start = period_end - timedelta(days=30)
        else:
            period_start = custom_start
            period_end = custom_end
        
        # Get summary
        summary = await self.get_summary(period_start, period_end)
        
        # Get service metrics
        service_metrics = await self._get_service_metrics(period_start, period_end)
        
        # Get projections
        projections = await self.analyzer.project_costs(
            period_start,
            period_end,
            BillingPeriod.MONTHLY
        )
        
        # Get recommendations
        recommendations = await self.optimizer.get_recommendations(
            summary,
            service_metrics
        )
        
        # Get recent alerts
        alerts = await self._get_recent_alerts(period_start)
        
        # Generate charts
        charts = await self._generate_charts(summary, service_metrics)
        
        # Create report
        report = CostReport(
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            service_metrics=service_metrics,
            projections=projections,
            recommendations=recommendations,
            alerts=alerts,
            charts=charts
        )
        
        # Export if needed
        await self._export_report(report)
        
        return report
    
    async def optimize_costs(self) -> List[OptimizationRecommendation]:
        """Analyze and recommend cost optimizations"""
        # Get last 7 days of data
        period_end = datetime.now()
        period_start = period_end - timedelta(days=7)
        
        summary = await self.get_summary(period_start, period_end)
        metrics = await self._get_service_metrics(period_start, period_end)
        
        recommendations = []
        
        # Check for model optimization opportunities
        for metric in metrics:
            if metric.service_type == ServiceType.LLM:
                # Check if using expensive models for simple tasks
                if metric.average_cost_per_request > Decimal('0.05'):
                    rec = OptimizationRecommendation(
                        title="Consider using cheaper model",
                        description=f"Service {metric.service_name} has high average cost per request",
                        category="model_selection",
                        potential_savings=metric.total_cost * Decimal('0.3'),
                        savings_percentage=30.0,
                        implementation_effort="low",
                        affected_service=ServiceType.LLM,
                        affected_modules=[],
                        action_items=[
                            f"Switch from expensive model to Claude 3.5 Haiku",
                            "Test quality with cheaper model",
                            "Implement fallback for complex queries"
                        ],
                        code_changes_required=True,
                        estimated_implementation_time="2 hours"
                    )
                    recommendations.append(rec)
                
                # Check cache hit rate
                if metric.cache_hit_rate < 0.3:
                    potential_savings = metric.total_cost * (0.5 - metric.cache_hit_rate)
                    rec = OptimizationRecommendation(
                        title="Improve caching strategy",
                        description=f"Low cache hit rate ({metric.cache_hit_rate:.1%}) for {metric.service_name}",
                        category="caching",
                        potential_savings=potential_savings,
                        savings_percentage=float(potential_savings / metric.total_cost * 100),
                        implementation_effort="medium",
                        affected_service=ServiceType.LLM,
                        affected_modules=[],
                        action_items=[
                            "Increase cache TTL for stable queries",
                            "Implement semantic similarity caching",
                            "Pre-cache common queries"
                        ],
                        code_changes_required=True,
                        estimated_implementation_time="4 hours"
                    )
                    recommendations.append(rec)
        
        # Check for batch processing opportunities
        hourly_patterns = await self._analyze_hourly_patterns()
        if hourly_patterns['burstiness'] > 0.7:
            rec = OptimizationRecommendation(
                title="Implement batch processing",
                description="Detected bursty usage pattern - batch processing could reduce costs",
                category="batch_processing",
                potential_savings=summary.total_cost * Decimal('0.15'),
                savings_percentage=15.0,
                implementation_effort="high",
                affected_service=ServiceType.LLM,
                affected_modules=[],
                action_items=[
                    "Implement request queuing",
                    "Batch similar requests",
                    "Process batches during off-peak hours"
                ],
                code_changes_required=True,
                estimated_implementation_time="1 day"
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _project_cost(
        self,
        historical_entries: List[CostEntry],
        target_date: datetime
    ) -> Decimal:
        """Project cost to target date"""
        if not historical_entries:
            return Decimal('0')
        
        # Simple linear projection
        daily_costs = defaultdict(Decimal)
        for entry in historical_entries:
            day = entry.timestamp.date()
            daily_costs[day] += entry.amount
        
        if daily_costs:
            avg_daily = sum(daily_costs.values()) / len(daily_costs)
            days_remaining = (target_date - datetime.now()).days
            return avg_daily * days_remaining
        
        return Decimal('0')
    
    async def _project_overrun(self, budget: BudgetConfig) -> Optional[Decimal]:
        """Project budget overrun amount"""
        # Get recent usage rate
        recent_usage = await self._get_usage_rate(budget.period)
        
        # Calculate remaining period
        period_end = self._get_period_end(budget.period)
        time_remaining = period_end - datetime.now()
        
        # Project usage
        projected_usage = budget.current_usage + (recent_usage * time_remaining.total_seconds() / 3600)
        
        if projected_usage > budget.amount:
            return projected_usage - budget.amount
        
        return None
    
    def _get_period_start(self, period: BillingPeriod) -> datetime:
        """Get start of billing period"""
        now = datetime.now()
        
        if period == BillingPeriod.HOURLY:
            return now.replace(minute=0, second=0, microsecond=0)
        elif period == BillingPeriod.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == BillingPeriod.WEEKLY:
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == BillingPeriod.MONTHLY:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == BillingPeriod.YEARLY:
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return now
    
    def _get_period_end(self, period: BillingPeriod) -> datetime:
        """Get end of billing period"""
        start = self._get_period_start(period)
        
        if period == BillingPeriod.HOURLY:
            return start + timedelta(hours=1)
        elif period == BillingPeriod.DAILY:
            return start + timedelta(days=1)
        elif period == BillingPeriod.WEEKLY:
            return start + timedelta(weeks=1)
        elif period == BillingPeriod.MONTHLY:
            # Handle month end properly
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1)
            else:
                return start.replace(month=start.month + 1)
        elif period == BillingPeriod.YEARLY:
            return start.replace(year=start.year + 1)
        
        return start + timedelta(days=1)
    
    async def _send_alert(self, alert: CostAlert):
        """Send alert notification"""
        # Add to queue
        self.pending_alerts.append(alert)
        
        # Send email notifications
        # TODO: Implement email sending
        
        # Send webhook notifications
        # TODO: Implement webhook calls
        
        # Log alert
        logger.warning(f"Cost Alert: {alert.message}")
    
    async def _stop_service(self, service_name: str):
        """Stop a service due to budget limit"""
        # Set service as unavailable
        stop_key = f"service:stopped:{service_name}"
        await self.redis.set(stop_key, '1')
        
        # Notify LLM service or other components
        # TODO: Implement service stopping mechanism
    
    async def _throttle_service(self, service_name: str, rate: float):
        """Throttle service to reduce costs"""
        throttle_key = f"service:throttle:{service_name}"
        await self.redis.set(throttle_key, str(rate))
        
        # Update rate limiter
        self.service_limiters[service_name] = rate
    
    async def is_service_available(self, service_name: str) -> bool:
        """Check if service is available (not stopped)"""
        stop_key = f"service:stopped:{service_name}"
        return not await self.redis.exists(stop_key)
    
    async def get_service_throttle_rate(self, service_name: str) -> float:
        """Get throttle rate for service"""
        throttle_key = f"service:throttle:{service_name}"
        rate = await self.redis.get(throttle_key)
        return float(rate) if rate else 1.0
    
    def load_budgets(self):
        """Load budget configurations"""
        # Load from settings
        if settings.max_daily_spend > 0:
            self.budgets.append(BudgetConfig(
                name="Daily LLM Budget",
                amount=Decimal(str(settings.max_daily_spend)),
                period=BillingPeriod.DAILY,
                service_types=[ServiceType.LLM]
            ))
        
        if settings.max_monthly_spend > 0:
            self.budgets.append(BudgetConfig(
                name="Monthly Total Budget",
                amount=Decimal(str(settings.max_monthly_spend)),
                period=BillingPeriod.MONTHLY
            ))
    
    async def _fetch_entries(
        self,
        start: datetime,
        end: datetime
    ) -> List[CostEntry]:
        """Fetch cost entries from database"""
        # TODO: Implement database query
        return []
    
    async def _get_service_metrics(
        self,
        start: datetime,
        end: datetime
    ) -> List[ServiceUsageMetrics]:
        """Get detailed service metrics"""
        # TODO: Implement metrics calculation
        return []
    
    async def _get_recent_alerts(self, since: datetime) -> List[CostAlert]:
        """Get recent cost alerts"""
        return [a for a in self.pending_alerts if a.timestamp >= since]
    
    async def _generate_charts(
        self,
        summary: CostSummary,
        metrics: List[ServiceUsageMetrics]
    ) -> Dict[str, str]:
        """Generate visualization charts"""
        # TODO: Implement chart generation
        return {}
    
    async def _export_report(self, report: CostReport):
        """Export report to file"""
        # TODO: Implement report export
        pass
    
    async def _get_usage_rate(self, period: BillingPeriod) -> Decimal:
        """Get current usage rate per hour"""
        # TODO: Implement usage rate calculation
        return Decimal('0')
    
    async def _analyze_hourly_patterns(self) -> Dict[str, float]:
        """Analyze hourly usage patterns"""
        # TODO: Implement pattern analysis
        return {'burstiness': 0.5}
    
    async def _check_optimizations(self, service_name: str):
        """Check for optimization opportunities"""
        # TODO: Implement optimization checking
        pass
```

## Test Implementation Requirements

Create `tests/test_cost_tracker.py`:

1. **Cost Tracking Tests**:
   - Test cost entry creation
   - Test real-time counter updates
   - Test cost aggregation
   - Test multi-service tracking

2. **Budget Enforcement Tests**:
   - Test soft limit warnings
   - Test hard limit stops
   - Test budget period resets
   - Test multiple budget configurations

3. **Alert System Tests**:
   - Test alert generation
   - Test alert deduplication
   - Test notification sending
   - Test alert acknowledgment

4. **Projection Tests**:
   - Test cost projection accuracy
   - Test overrun prediction
   - Test trend analysis

5. **Optimization Tests**:
   - Test recommendation generation
   - Test savings calculation
   - Test pattern detection

## Success Criteria

1. **Accuracy**: Cost tracking accurate to $0.001
2. **Real-time**: Updates within 100ms of cost event
3. **Budget Protection**: 100% prevention of hard limit overruns
4. **Alert Latency**: Alerts sent within 1 second
5. **Projection Accuracy**: Within 10% of actual costs
6. **Optimization Impact**: Identify >20% potential savings
7. **Reporting**: Daily reports generated automatically

## Edge Cases to Handle

1. **Service outages**: Handle Redis/database unavailability
2. **Budget resets**: Proper period boundary handling
3. **Concurrent updates**: Thread-safe counter updates
4. **Time zone issues**: Consistent period calculations
5. **Decimal precision**: Accurate micro-transaction handling
6. **Alert storms**: Prevent alert flooding
7. **Service recovery**: Resume after budget stop
8. **Retroactive entries**: Handle backdated costs
9. **Currency conversion**: Multi-currency support
10. **Report failures**: Graceful handling of report generation errors

---

**44. Should we implement cost allocation tags for better departmental billing?**
*Recommendation: Yes - Add flexible tagging system to allocate costs to different projects, teams, or clients for better cost accountability.*

This completes the Cost Tracker Service specifications. The service provides comprehensive cost monitoring, budget enforcement, and optimization recommendations to keep Scout financially sustainable.