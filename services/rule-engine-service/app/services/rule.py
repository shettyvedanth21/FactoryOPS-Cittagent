"""Rule service layer - business logic."""

from typing import Optional, List
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus, RuleScope, ConditionOperator, Alert
from app.repositories.rule import RuleRepository, AlertRepository
from app.schemas.rule import RuleCreate, RuleUpdate, RuleStatus as RuleStatusEnum

logger = logging.getLogger(__name__)


class RuleService:
    """Service layer for rule management business logic."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repository = RuleRepository(session)

    async def create_rule(self, rule_data: RuleCreate) -> Rule:

        if rule_data.scope == RuleScope.SELECTED_DEVICES and not rule_data.device_ids:
            raise ValueError("device_ids is required when scope is 'selected_devices'")

        if not rule_data.notification_channels:
            raise ValueError("At least one notification channel is required")

        rule = Rule(
            tenant_id=rule_data.tenant_id,
            rule_name=rule_data.rule_name,
            description=rule_data.description,

            # store STRING in DB
            scope=rule_data.scope.value,
            device_ids=rule_data.device_ids,
            property=rule_data.property,

            # store STRING in DB
            condition=rule_data.condition.value,

            threshold=rule_data.threshold,

            # store STRING in DB
            status=RuleStatus.ACTIVE.value,

            notification_channels=[ch.value for ch in rule_data.notification_channels],
            cooldown_minutes=rule_data.cooldown_minutes,
        )

        created_rule = await self._repository.create(rule)
        await self._session.commit()

        logger.info(
            "Rule created successfully",
            extra={
                "rule_id": str(created_rule.rule_id),
                "rule_name": created_rule.rule_name,
                "scope": created_rule.scope,
                "device_count": len(created_rule.device_ids),
            }
        )

        return created_rule

    async def get_rule(
        self,
        rule_id: UUID,
        tenant_id: Optional[str] = None
    ) -> Optional[Rule]:

        return await self._repository.get_by_id(rule_id, tenant_id)

    async def list_rules(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[RuleStatusEnum] = None,
        device_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Rule], int]:

        status_value = status.value if status else None

        return await self._repository.list_rules(
            tenant_id=tenant_id,
            status=status_value,
            device_id=device_id,
            page=page,
            page_size=page_size,
        )

    async def update_rule(
        self,
        rule_id: UUID,
        rule_data: RuleUpdate,
        tenant_id: Optional[str] = None,
    ) -> Optional[Rule]:

        rule = await self._repository.get_by_id(rule_id, tenant_id)
        if not rule:
            logger.warning(
                "Attempted to update non-existent rule",
                extra={"rule_id": str(rule_id)}
            )
            return None

        update_data = rule_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():

            if field == "scope" and value:
                value = value.value

            elif field == "condition" and value:
                value = value.value

            elif field == "notification_channels" and value:
                value = [ch.value for ch in value]

            setattr(rule, field, value)

        if rule.scope == RuleScope.SELECTED_DEVICES.value and not rule.device_ids:
            raise ValueError("device_ids is required when scope is 'selected_devices'")

        updated_rule = await self._repository.update(rule)
        await self._session.commit()

        logger.info(
            "Rule updated successfully",
            extra={"rule_id": str(updated_rule.rule_id)}
        )

        return updated_rule

    async def update_rule_status(
        self,
        rule_id: UUID,
        status: RuleStatusEnum,
        tenant_id: Optional[str] = None,
    ) -> Optional[Rule]:

        rule = await self._repository.update_status(
            rule_id,
            status.value
        )

        if rule:
            await self._session.commit()
            logger.info(
                "Rule status updated",
                extra={
                    "rule_id": str(rule_id),
                    "new_status": status.value,
                }
            )
        return rule

    async def delete_rule(
        self,
        rule_id: UUID,
        tenant_id: Optional[str] = None,
        soft: bool = True,
    ) -> bool:

        rule = await self._repository.get_by_id(rule_id, tenant_id)
        if not rule:
            return False

        await self._repository.delete(rule, soft=soft)
        await self._session.commit()

        logger.info(
            "Rule deleted successfully",
            extra={
                "rule_id": str(rule_id),
                "soft_delete": soft,
            }
        )

        return True

    async def get_active_rules_for_device(
        self,
        device_id: str,
        tenant_id: Optional[str] = None,
    ) -> List[Rule]:

        return await self._repository.get_active_rules_for_device(device_id, tenant_id)


class AlertService:
    """Service layer for alert management."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repository = AlertRepository(session)

    async def create_alert(
        self,
        rule: Rule,
        device_id: str,
        actual_value: float,
        severity: str = "medium",
    ) -> Alert:

        message = (
            f"Rule '{rule.rule_name}' triggered for device {device_id}: "
            f"{rule.property} {rule.condition} {rule.threshold} "
            f"(actual: {actual_value})"
        )

        alert = Alert(
            tenant_id=rule.tenant_id,
            rule_id=rule.rule_id,
            device_id=device_id,
            severity=severity,
            message=message,
            actual_value=actual_value,
            threshold_value=rule.threshold,
            status="open",
        )

        created_alert = await self._repository.create(alert)
        await self._session.commit()

        logger.info(
            "Alert created",
            extra={
                "alert_id": str(created_alert.alert_id),
                "rule_id": str(rule.rule_id),
                "device_id": device_id,
            }
        )

        return created_alert