# Import all models so SQLAlchemy can create proper relationships
from models.user import UserProfile
from models.password_reset_token import PasswordResetToken
from models.contact import Contact
from models.company import Company
from models.deal import Deal
from models.activity import Activity
from models.task import Task
from models.deal_document import DealDocument
from models.custom_field import CustomField, CustomFieldValue, FieldType, EntityType, PlacementType
from models.role import Role, Permission
from models.email_template import EmailTemplate, EmailLog, TemplateCategory, TemplateStatus
from models.integration import Integration, IntegrationLog, IntegrationWebhook
from models.note import Note
from models.system_config import SystemConfiguration
from models.prospect import Prospect, ProspectStatus, ProspectSource
from models.campaign import Campaign, CampaignType, CampaignStatus
from models.campaign_contact import CampaignContact, EngagementStatus
from models.campaign_metric import CampaignMetric, LeadScoreHistory

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
