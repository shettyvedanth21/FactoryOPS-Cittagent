"""Rule evaluation engine for real-time telemetry processing."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.schemas.rule import EvaluationResult, TelemetryPayload
from app.schemas.telemetry import TelemetryIn
from app.services.rule import RuleService, AlertService
from app.repositories.rule import RuleRepository
from app.notifications.adapter import NotificationAdapter

logger = logging.getLogger(__name__)


class RuleEvaluator:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._rule_service = RuleService(session)
        self._alert_service = AlertService(session)
        self._rule_repository = RuleRepository(session)
        self._notification_adapter = NotificationAdapter()

    async def evaluate_telemetry(
        self,
        telemetry: TelemetryPayload,
        tenant_id: Optional[str] = None,
    ) -> tuple[int, int, List[EvaluationResult]]:

        device_id = telemetry.device_id

        rules = await self._rule_service.get_active_rules_for_device(
            device_id=device_id,
            tenant_id=tenant_id,
        )

        if not rules:
            logger.debug(
                "No active rules for device",
                extra={"device_id": device_id},
            )
            return 0, 0, []

        triggered_rules: List[EvaluationResult] = []

        for rule in rules:

            if rule.is_in_cooldown():
                continue

            result = await self._evaluate_single_rule(rule, telemetry)

            if result.triggered:
                triggered_rules.append(result)

                await self._alert_service.create_alert(
                    rule=rule,
                    device_id=device_id,
                    actual_value=result.actual_value,
                    severity=self._determine_severity(rule, result.actual_value),
                )

                await self._rule_repository.update_last_triggered(rule.rule_id)

                await self._send_notifications(rule, device_id, result)

        await self._session.commit()

        logger.info(
            "Rule evaluation completed",
            extra={
                "device_id": device_id,
                "rules_evaluated": len(rules),
                "rules_triggered": len(triggered_rules),
            },
        )

        return len(rules), len(triggered_rules), triggered_rules

    async def _evaluate_single_rule(
        self,
        rule: Rule,
        telemetry: TelemetryPayload,
    ) -> EvaluationResult:

        actual_value = self._extract_property_value(telemetry, rule.property)

        triggered = self._evaluate_condition(
            actual_value=actual_value,
            threshold=rule.threshold,
            operator=rule.condition,
        )

        message = None
        if triggered:
            message = (
                f"{rule.property} is {actual_value} "
                f"(threshold: {rule.condition} {rule.threshold})"
            )

        return EvaluationResult(
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            triggered=triggered,
            actual_value=actual_value,
            threshold=rule.threshold,
            condition=rule.condition,
            message=message,
        )

    def _extract_property_value(
        self,
        telemetry: TelemetryPayload,
        property_name: str,
    ) -> float:
        
        dynamic_fields = telemetry.get_dynamic_fields()
        
        if property_name in dynamic_fields:
            return dynamic_fields[property_name]
        
        value = getattr(telemetry, property_name, None)
        if value is not None and isinstance(value, (int, float)):
            return float(value)
        
        raise ValueError(f"Unknown property: {property_name}")

    def _evaluate_condition(
        self,
        actual_value: float,
        threshold: float,
        operator: str,
    ) -> bool:

        operators = {
            ">": lambda a, t: a > t,
            "<": lambda a, t: a < t,
            "==": lambda a, t: a == t,
            "=": lambda a, t: a == t,
            "!=": lambda a, t: a != t,
            ">=": lambda a, t: a >= t,
            "<=": lambda a, t: a <= t,
        }

        if operator not in operators:
            raise ValueError(f"Unknown operator: {operator}")

        return operators[operator](actual_value, threshold)

    def _determine_severity(self, rule: Rule, actual_value: float) -> str:

        if rule.threshold == 0:
            deviation = abs(actual_value)
        else:
            deviation = abs((actual_value - rule.threshold) / rule.threshold)

        if deviation > 0.5:
            return "critical"
        elif deviation > 0.25:
            return "high"
        elif deviation > 0.1:
            return "medium"
        else:
            return "low"

    async def _send_notifications(
        self,
        rule: Rule,
        device_id: str,
        result: EvaluationResult,
    ) -> None:

        if not rule.notification_channels:
            return

        message = (
            f"🚨 Alert: {rule.rule_name}\n"
            f"Device: {device_id}\n"
            f"Condition: {rule.property} {rule.condition} {rule.threshold}\n"
            f"Actual: {result.actual_value}\n"
            f"Time: {datetime.utcnow().isoformat()}"
        )

        for channel in rule.notification_channels:
            try:
                await self._notification_adapter.send(
                    channel=channel,
                    message=message,
                    rule=rule,
                    device_id=device_id,
                )
                logger.info(
                    "Notification sent",
                    extra={
                        "channel": channel,
                        "rule_id": str(rule.rule_id),
                        "device_id": device_id,
                    },
                )
            except Exception as e:
                logger.error(
                    "Failed to send notification",
                    extra={
                        "channel": channel,
                        "rule_id": str(rule.rule_id),
                        "error": str(e),
                    },
                )

    async def evaluate(
        self,
        telemetry: TelemetryIn,
    ) -> List[Rule]:

        device_id = telemetry.device_id
        metric = telemetry.metric
        value = telemetry.value

        rules = await self._rule_repository.get_active_rules_for_device(device_id)

        matched_rules: List[Rule] = []

        for rule in rules:

            if rule.property != metric:
                continue

            if self._evaluate_condition(value, rule.threshold, rule.condition):
                matched_rules.append(rule)

        logger.debug(
            "Simple evaluation completed",
            extra={
                "device_id": device_id,
                "metric": metric,
                "value": value,
                "rules_evaluated": len(rules),
                "rules_matched": len(matched_rules),
            },
        )

        return matched_rules
