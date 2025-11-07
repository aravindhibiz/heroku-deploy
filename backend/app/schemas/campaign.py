from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.models.campaign import CampaignType, CampaignStatus


# Base Campaign Schema
class CampaignBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: CampaignType
    status: CampaignStatus = CampaignStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Decimal = Field(default=Decimal("0.00"), ge=0)
    expected_revenue: Optional[Decimal] = Field(None, ge=0)
    target_audience_size: Optional[int] = Field(None, ge=0)
    target_response_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    target_conversion_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    email_template_id: Optional[UUID] = None
    email_subject: Optional[str] = Field(None, max_length=500)
    email_from_name: Optional[str] = Field(None, max_length=255)
    email_from_email: Optional[str] = Field(None, max_length=255)
    audience_filters: Optional[Dict[str, Any]] = None
    is_automated: bool = False
    automation_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('end_date must be after start_date')
        return v


# Create Campaign Schema
class CampaignCreate(CampaignBase):
    owner_id: Optional[UUID] = None  # Will default to current user if not provided


# Update Campaign Schema
class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    type: Optional[CampaignType] = None
    status: Optional[CampaignStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    budget: Optional[Decimal] = Field(None, ge=0)
    actual_cost: Optional[Decimal] = Field(None, ge=0)
    expected_revenue: Optional[Decimal] = Field(None, ge=0)
    actual_revenue: Optional[Decimal] = Field(None, ge=0)
    target_audience_size: Optional[int] = Field(None, ge=0)
    target_response_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    target_conversion_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    email_template_id: Optional[UUID] = None
    email_subject: Optional[str] = Field(None, max_length=500)
    email_from_name: Optional[str] = Field(None, max_length=255)
    email_from_email: Optional[str] = Field(None, max_length=255)
    audience_filters: Optional[Dict[str, Any]] = None
    is_automated: Optional[bool] = None
    automation_config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


# Campaign Response Schema (returned from API)
class CampaignResponse(CampaignBase):
    id: UUID
    actual_start_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None
    actual_cost: Decimal = Decimal("0.00")
    actual_revenue: Decimal = Decimal("0.00")
    sent_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    responded_count: int = 0
    bounced_count: int = 0
    unsubscribed_count: int = 0
    converted_count: int = 0
    prospects_generated: int = 0
    owner_id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    last_executed_at: Optional[datetime] = None

    # Calculated properties
    roi: Optional[float] = None
    open_rate: Optional[float] = None
    click_rate: Optional[float] = None
    response_rate: Optional[float] = None
    conversion_rate: Optional[float] = None
    delivery_rate: Optional[float] = None
    bounce_rate: Optional[float] = None

    class Config:
        from_attributes = True


# Campaign with Stats (includes calculated metrics)
class CampaignWithStats(CampaignResponse):
    """Campaign response with additional statistics"""
    days_remaining: int = 0
    is_active: bool = False
    is_scheduled: bool = False
    is_draft: bool = False


# Campaign Detail (includes related data)
class CampaignDetail(CampaignWithStats):
    """Full campaign details with relationships"""
    owner_name: Optional[str] = None
    email_template_name: Optional[str] = None
    audience_count: int = 0  # Number of people in campaign_contacts
    prospects_list: List[dict] = []  # Summary of prospects
    recent_metrics: List[dict] = []  # Recent performance snapshots


# Campaign Metrics Response
class CampaignMetrics(BaseModel):
    """Performance metrics for a campaign"""
    campaign_id: UUID
    campaign_name: str

    # Counts
    sent_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    responded_count: int = 0
    bounced_count: int = 0
    converted_count: int = 0
    prospects_generated: int = 0

    # Rates
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    response_rate: float = 0.0
    conversion_rate: float = 0.0
    bounce_rate: float = 0.0

    # Financial
    budget: Decimal = Decimal("0.00")
    actual_cost: Decimal = Decimal("0.00")
    actual_revenue: Decimal = Decimal("0.00")
    roi: float = 0.0

    class Config:
        from_attributes = True


# Campaign Conversion (deals generated)
class CampaignConversion(BaseModel):
    """Deal conversion from campaign"""
    deal_id: UUID
    deal_name: str
    deal_value: Decimal
    contact_id: UUID
    contact_name: str
    converted_at: datetime
    source_prospect_id: Optional[UUID] = None

    class Config:
        from_attributes = True


# Campaign Audience Member
class CampaignAudienceMember(BaseModel):
    """Member of campaign audience (contact or prospect)"""
    id: UUID
    campaign_contact_id: UUID
    recipient_type: str  # "contact" or "prospect"
    recipient_id: UUID
    name: str
    email: str
    status: str  # EngagementStatus
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    engagement_score: int = 0

    class Config:
        from_attributes = True


# Add Contact/Prospect to Campaign
class AddToCampaignRequest(BaseModel):
    """Request to add contacts or prospects to campaign"""
    contact_ids: Optional[List[UUID]] = []
    prospect_ids: Optional[List[UUID]] = []


# Add To Campaign Response
class AddToCampaignResponse(BaseModel):
    """Response after adding members to campaign"""
    campaign_id: UUID
    added_contacts: int = 0
    added_prospects: int = 0
    total_audience: int = 0
    message: str = "Members added to campaign successfully"


# Campaign Execution Request
class CampaignExecuteRequest(BaseModel):
    """Request to execute/send campaign"""
    send_test_email: bool = False
    test_email_recipients: Optional[List[str]] = []
    schedule_for: Optional[datetime] = None  # If provided, schedule for later


# Campaign Execution Response
class CampaignExecuteResponse(BaseModel):
    """Response after executing campaign"""
    campaign_id: UUID
    status: str
    sent_count: int = 0
    scheduled_for: Optional[datetime] = None
    message: str


# Campaign List Filter
class CampaignFilter(BaseModel):
    """Filters for campaign list queries"""
    status: Optional[List[CampaignStatus]] = None
    type: Optional[List[CampaignType]] = None
    owner_id: Optional[UUID] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    start_date_after: Optional[datetime] = None
    start_date_before: Optional[datetime] = None
    end_date_after: Optional[datetime] = None
    end_date_before: Optional[datetime] = None
    min_budget: Optional[Decimal] = None
    max_budget: Optional[Decimal] = None
    search: Optional[str] = None  # Search in name, description


# Campaign Stats Response
class CampaignStats(BaseModel):
    """Overall statistics for campaigns"""
    total_campaigns: int = 0
    draft_campaigns: int = 0
    active_campaigns: int = 0
    completed_campaigns: int = 0
    total_budget: Decimal = Decimal("0.00")
    total_spent: Decimal = Decimal("0.00")
    total_revenue: Decimal = Decimal("0.00")
    overall_roi: float = 0.0
    total_prospects: int = 0
    total_conversions: int = 0
    average_conversion_rate: float = 0.0

    class Config:
        from_attributes = True


# Time-Series Metric Data Point
class MetricDataPoint(BaseModel):
    """Single data point for time-series metrics"""
    date: datetime
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    converted: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0


# Campaign Analytics Response
class CampaignAnalytics(BaseModel):
    """Analytics data for a campaign"""
    campaign_id: UUID
    metrics: CampaignMetrics
    time_series: List[MetricDataPoint] = []
    top_performers: List[dict] = []  # Top performing contacts/prospects
    conversion_funnel: Dict[str, int] = {}  # sent -> delivered -> opened -> clicked -> converted

    class Config:
        from_attributes = True
