"""
Integration Repository - Data access layer for Integration and related entities.
Handles all database queries for integrations, logs, and webhooks.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc

from .base_repository import BaseRepository
from ..models.integration import Integration, IntegrationLog, IntegrationWebhook


class IntegrationRepository(BaseRepository[Integration]):
    """Repository for integration data access."""

    def __init__(self, db: Session):
        super().__init__(Integration, db)

    def get_by_user(
        self,
        user_id: UUID,
        include_logs: bool = False
    ) -> List[Integration]:
        """
        Get all integrations for a specific user.

        Args:
            user_id: User UUID
            include_logs: Whether to eager load logs

        Returns:
            List of integrations
        """
        query = self.db.query(Integration).filter(
            Integration.user_id == user_id
        )

        if include_logs:
            query = query.options(joinedload(Integration.logs))

        return query.order_by(Integration.created_at.desc()).all()

    def get_by_user_and_provider(
        self,
        user_id: UUID,
        provider: str
    ) -> Optional[Integration]:
        """
        Get integration by user and provider.

        Args:
            user_id: User UUID
            provider: Integration provider name

        Returns:
            Integration or None
        """
        return self.db.query(Integration).filter(
            and_(
                Integration.user_id == user_id,
                Integration.provider == provider
            )
        ).first()

    def get_by_status(
        self,
        status: str,
        user_id: Optional[UUID] = None
    ) -> List[Integration]:
        """
        Get integrations by status.

        Args:
            status: Integration status (connected, disconnected, error)
            user_id: Optional user filter

        Returns:
            List of integrations
        """
        query = self.db.query(Integration).filter(
            Integration.status == status
        )

        if user_id:
            query = query.filter(Integration.user_id == user_id)

        return query.order_by(Integration.created_at.desc()).all()

    def get_auto_sync_integrations(self) -> List[Integration]:
        """
        Get all integrations with auto_sync enabled.

        Returns:
            List of auto-sync integrations
        """
        return self.db.query(Integration).filter(
            and_(
                Integration.auto_sync == True,
                Integration.status == 'connected'
            )
        ).all()

    def get_due_for_sync(
        self,
        sync_frequency: Optional[str] = None
    ) -> List[Integration]:
        """
        Get integrations due for sync based on frequency.

        Args:
            sync_frequency: Optional frequency filter

        Returns:
            List of integrations due for sync
        """
        filters = [
            Integration.auto_sync == True,
            Integration.status == 'connected'
        ]

        if sync_frequency:
            filters.append(Integration.sync_frequency == sync_frequency)

        return self.db.query(Integration).filter(and_(*filters)).all()

    def update_tokens(
        self,
        integration_id: UUID,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[Integration]:
        """
        Update integration tokens.

        Args:
            integration_id: Integration UUID
            access_token: New access token
            refresh_token: Optional new refresh token
            expires_at: Token expiry datetime

        Returns:
            Updated integration or None
        """
        integration = self.get(integration_id)
        if not integration:
            return None

        integration.access_token = access_token
        if refresh_token:
            integration.refresh_token = refresh_token
        if expires_at:
            integration.expires_at = expires_at

        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update_status(
        self,
        integration_id: UUID,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[Integration]:
        """
        Update integration status.

        Args:
            integration_id: Integration UUID
            status: New status
            error_message: Optional error message

        Returns:
            Updated integration or None
        """
        integration = self.get(integration_id)
        if not integration:
            return None

        integration.status = status
        if error_message:
            integration.last_error = error_message
            # Increment error count
            try:
                current_count = int(integration.error_count)
                integration.error_count = str(current_count + 1)
            except (ValueError, TypeError):
                integration.error_count = "1"
        else:
            integration.last_error = None
            integration.error_count = "0"

        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update_last_sync(
        self,
        integration_id: UUID,
        sync_time: Optional[datetime] = None
    ) -> Optional[Integration]:
        """
        Update last sync timestamp.

        Args:
            integration_id: Integration UUID
            sync_time: Sync datetime (defaults to now)

        Returns:
            Updated integration or None
        """
        integration = self.get(integration_id)
        if not integration:
            return None

        integration.last_sync = sync_time or datetime.utcnow()
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def get_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get integration statistics.

        Args:
            user_id: Optional user filter

        Returns:
            Statistics dictionary
        """
        query = self.db.query(Integration)

        if user_id:
            query = query.filter(Integration.user_id == user_id)

        all_integrations = query.all()

        return {
            'total': len(all_integrations),
            'connected': len([i for i in all_integrations if i.status == 'connected']),
            'disconnected': len([i for i in all_integrations if i.status == 'disconnected']),
            'error': len([i for i in all_integrations if i.status == 'error']),
            'auto_sync_enabled': len([i for i in all_integrations if i.auto_sync]),
            'by_provider': self._count_by_provider(all_integrations)
        }

    def _count_by_provider(self, integrations: List[Integration]) -> Dict[str, int]:
        """Count integrations by provider."""
        provider_counts = {}
        for integration in integrations:
            provider_counts[integration.provider] = provider_counts.get(
                integration.provider, 0
            ) + 1
        return provider_counts


class IntegrationLogRepository(BaseRepository[IntegrationLog]):
    """Repository for integration log data access."""

    def __init__(self, db: Session):
        super().__init__(IntegrationLog, db)

    def get_by_integration(
        self,
        integration_id: UUID,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[IntegrationLog]:
        """
        Get logs for a specific integration.

        Args:
            integration_id: Integration UUID
            limit: Maximum results
            offset: Results offset
            action: Optional action filter
            status: Optional status filter

        Returns:
            List of logs
        """
        query = self.db.query(IntegrationLog).filter(
            IntegrationLog.integration_id == integration_id
        )

        if action:
            query = query.filter(IntegrationLog.action == action)

        if status:
            query = query.filter(IntegrationLog.status == status)

        return query.order_by(
            desc(IntegrationLog.created_at)
        ).offset(offset).limit(limit).all()

    def create_log(
        self,
        integration_id: UUID,
        action: str,
        status: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        records_processed: int = 0,
        records_created: int = 0,
        records_updated: int = 0,
        records_failed: int = 0
    ) -> IntegrationLog:
        """
        Create a new integration log entry.

        Args:
            integration_id: Integration UUID
            action: Action performed
            status: Status of action
            message: Optional message
            details: Optional details dict
            records_processed: Number of records processed
            records_created: Number created
            records_updated: Number updated
            records_failed: Number failed

        Returns:
            Created log entry
        """
        log = IntegrationLog(
            integration_id=integration_id,
            action=action,
            status=status,
            message=message,
            details=details or {},
            records_processed=str(records_processed),
            records_created=str(records_created),
            records_updated=str(records_updated),
            records_failed=str(records_failed)
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_recent_errors(
        self,
        integration_id: UUID,
        limit: int = 10
    ) -> List[IntegrationLog]:
        """
        Get recent error logs for an integration.

        Args:
            integration_id: Integration UUID
            limit: Maximum results

        Returns:
            List of error logs
        """
        return self.db.query(IntegrationLog).filter(
            and_(
                IntegrationLog.integration_id == integration_id,
                IntegrationLog.status == 'error'
            )
        ).order_by(
            desc(IntegrationLog.created_at)
        ).limit(limit).all()

    def get_sync_statistics(
        self,
        integration_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get sync statistics for an integration.

        Args:
            integration_id: Integration UUID
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        since = datetime.utcnow() - timedelta(days=days)

        logs = self.db.query(IntegrationLog).filter(
            and_(
                IntegrationLog.integration_id == integration_id,
                IntegrationLog.action == 'sync',
                IntegrationLog.created_at >= since
            )
        ).all()

        total_processed = 0
        total_created = 0
        total_updated = 0
        total_failed = 0
        successful_syncs = 0
        failed_syncs = 0

        for log in logs:
            if log.status == 'success':
                successful_syncs += 1
            elif log.status == 'error':
                failed_syncs += 1

            try:
                total_processed += int(log.records_processed)
                total_created += int(log.records_created)
                total_updated += int(log.records_updated)
                total_failed += int(log.records_failed)
            except (ValueError, TypeError):
                pass

        return {
            'period_days': days,
            'total_syncs': len(logs),
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'total_records_processed': total_processed,
            'total_records_created': total_created,
            'total_records_updated': total_updated,
            'total_records_failed': total_failed,
            'success_rate': round((successful_syncs / len(logs) * 100) if logs else 0, 2)
        }


class IntegrationWebhookRepository(BaseRepository[IntegrationWebhook]):
    """Repository for integration webhook data access."""

    def __init__(self, db: Session):
        super().__init__(IntegrationWebhook, db)

    def get_by_integration(
        self,
        integration_id: UUID,
        active_only: bool = False
    ) -> List[IntegrationWebhook]:
        """
        Get webhooks for an integration.

        Args:
            integration_id: Integration UUID
            active_only: Whether to return only active webhooks

        Returns:
            List of webhooks
        """
        query = self.db.query(IntegrationWebhook).filter(
            IntegrationWebhook.integration_id == integration_id
        )

        if active_only:
            query = query.filter(IntegrationWebhook.is_active == True)

        return query.all()

    def update_last_received(
        self,
        webhook_id: UUID
    ) -> Optional[IntegrationWebhook]:
        """
        Update webhook last received timestamp.

        Args:
            webhook_id: Webhook UUID

        Returns:
            Updated webhook or None
        """
        webhook = self.get(webhook_id)
        if not webhook:
            return None

        webhook.last_received = datetime.utcnow()
        self.db.commit()
        self.db.refresh(webhook)
        return webhook
