# Import all models so SQLAlchemy can create proper relationships
from user import UserProfile
from password_reset_token import PasswordResetToken
from contact import Contact
from company import Company
from deal import Deal
from activity import Activity
from task import Task
from deal_document import DealDocument
from custom_field import CustomField, CustomFieldValue, FieldType, EntityType, PlacementType
from role import Role, Permission
from email_template import EmailTemplate, EmailLog, TemplateCategory, TemplateStatus
from integration import Integration, IntegrationLog, IntegrationWebhook
from note import Note
from system_config import SystemConfiguration
from prospect import Prospect, ProspectStatus, ProspectSource
from campaign import Campaign, CampaignType, CampaignStatus
from campaign_contact import CampaignContact, EngagementStatus
from campaign_metric import CampaignMetric, LeadScoreHistory

__all__ = ['UserProfile', 'PasswordResetToken', 'Contact', 'Company',
           'Deal', 'Activity', 'Task', 'DealDocument',
           'CustomField', 'CustomFieldValue', 'FieldType', 'EntityType', 'PlacementType',
           'Role', 'Permission',
           'EmailTemplate', 'EmailLog', 'TemplateCategory', 'TemplateStatus',
           'Integration', 'IntegrationLog', 'IntegrationWebhook',
           'Note', 'SystemConfiguration',
           'Prospect', 'ProspectStatus', 'ProspectSource',
           'Campaign', 'CampaignType', 'CampaignStatus',
           'CampaignContact', 'EngagementStatus',
           'CampaignMetric', 'LeadScoreHistory']
