from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.models.prospect import ProspectStatus, ProspectSource


# Base Prospect Schema
class ProspectBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    company_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    notes: Optional[str] = None
    source: ProspectSource = ProspectSource.OTHER
    source_details: Optional[str] = None
    status: ProspectStatus = ProspectStatus.NEW
    lead_score: int = Field(default=0, ge=0, le=100)
    linkedin_url: Optional[str] = Field(None, max_length=255)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    @validator('email', pre=True)
    def empty_email_to_none(cls, v):
        """Convert empty string to None for email"""
        if v == '' or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @validator('status', pre=True)
    def normalize_status(cls, v):
        """Convert status to uppercase to match database enum"""
        if isinstance(v, str):
            return v.upper()
        return v

    @validator('source', pre=True)
    def normalize_source(cls, v):
        """Convert source to uppercase to match database enum"""
        if isinstance(v, str):
            return v.upper()
        return v

    @validator('phone')
    def check_contact_info(cls, phone, values):
        """Ensure at least one of email or phone is provided"""
        email = values.get('email')
        # Check if both are empty/None
        if not email and not phone:
            raise ValueError('Either email or phone number must be provided')
        return phone


# Create Prospect Schema
class ProspectCreate(ProspectBase):
    campaign_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


# Update Prospect Schema
class ProspectUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    company_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[ProspectSource] = None
    source_details: Optional[str] = None
    status: Optional[ProspectStatus] = None
    lead_score: Optional[int] = Field(None, ge=0, le=100)
    assigned_to: Optional[UUID] = None
    linkedin_url: Optional[str] = Field(None, max_length=255)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    @validator('email', pre=True)
    def empty_email_to_none(cls, v):
        """Convert empty string to None for email"""
        if v == '' or (isinstance(v, str) and not v.strip()):
            return None
        return v

    @validator('status', pre=True)
    def normalize_status(cls, v):
        """Convert status to uppercase to match database enum"""
        if isinstance(v, str):
            return v.upper()
        return v

    @validator('source', pre=True)
    def normalize_source(cls, v):
        """Convert source to uppercase to match database enum"""
        if isinstance(v, str):
            return v.upper()
        return v


# Prospect Response Schema (returned from API)
class ProspectResponse(ProspectBase):
    id: UUID
    campaign_id: Optional[UUID] = None
    converted_to_contact_id: Optional[UUID] = None
    converted_at: Optional[datetime] = None
    assigned_to: Optional[UUID] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    last_contacted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

        @staticmethod
        def schema_extra(schema, model):
            # Return enum values as lowercase for frontend compatibility
            for prop in schema.get('properties', {}).values():
                if 'allOf' in prop and len(prop['allOf']) > 0:
                    ref = prop['allOf'][0].get('$ref', '')
                    if 'ProspectStatus' in ref or 'ProspectSource' in ref:
                        prop['type'] = 'string'


# Prospect with Campaign Info
class ProspectWithCampaign(ProspectResponse):
    campaign_name: Optional[str] = None
    campaign_type: Optional[str] = None


# Prospect with Engagement Data
class ProspectWithEngagement(ProspectResponse):
    engagement_count: int = 0  # Number of campaigns they're in
    total_opens: int = 0
    total_clicks: int = 0
    last_engagement_at: Optional[datetime] = None


# Prospect Conversion Request
class ProspectConversionRequest(BaseModel):
    """Data for converting prospect to contact"""
    notes: Optional[str] = None  # Additional notes for the conversion
    create_activity: bool = True  # Whether to create an activity log for the conversion
    assign_to: Optional[UUID] = None  # Optionally assign the new contact to a user


# Prospect Conversion Response
class ProspectConversionResponse(BaseModel):
    """Response after converting prospect to contact"""
    prospect_id: UUID
    contact_id: UUID
    message: str = "Prospect successfully converted to contact"
    activity_id: Optional[UUID] = None  # If activity was created

    class Config:
        from_attributes = True


# Prospect List Filter
class ProspectFilter(BaseModel):
    """Filters for prospect list queries"""
    status: Optional[List[ProspectStatus]] = None
    source: Optional[List[ProspectSource]] = None
    campaign_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    min_lead_score: Optional[int] = Field(None, ge=0, le=100)
    max_lead_score: Optional[int] = Field(None, ge=0, le=100)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    search: Optional[str] = None  # Search in name, email, company


# Prospect Stats Response
class ProspectStats(BaseModel):
    """Statistics for prospects"""
    total_prospects: int = 0
    new_prospects: int = 0
    contacted_prospects: int = 0
    qualified_prospects: int = 0
    converted_prospects: int = 0
    rejected_prospects: int = 0
    average_lead_score: float = 0.0
    conversion_rate: float = 0.0  # Percentage

    class Config:
        from_attributes = True


# Prospect Detail (includes related data)
class ProspectDetail(ProspectResponse):
    """Full prospect details with relationships"""
    campaign_name: Optional[str] = None
    assigned_user_name: Optional[str] = None
    converted_contact_name: Optional[str] = None
    engagement_history: List[dict] = []  # Campaign engagement records
    lead_score_changes: List[dict] = []  # Score change history


# Bulk Prospect Create
class BulkProspectCreate(BaseModel):
    """Schema for bulk prospect import"""
    prospects: List[ProspectCreate]
    campaign_id: Optional[UUID] = None
    skip_duplicates: bool = True  # Whether to skip duplicates or fail


# Bulk Prospect Response
class BulkProspectResponse(BaseModel):
    """Response for bulk prospect creation"""
    created_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    created_ids: List[UUID] = []
    errors: List[dict] = []  # {"row": 1, "error": "Duplicate email"}
