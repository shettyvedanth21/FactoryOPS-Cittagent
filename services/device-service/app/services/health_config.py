"""Health configuration service layer - business logic for parameter health management and scoring."""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.device import ParameterHealthConfig, Device
from app.schemas.device import ParameterHealthConfigCreate, ParameterHealthConfigUpdate
import logging

logger = logging.getLogger(__name__)


class HealthConfigService:
    """Service layer for parameter health configuration and score calculation."""
    
    VALID_MACHINE_STATES = ["RUNNING", "OFF", "IDLE", "UNLOAD", "POWER CUT"]
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def create_health_config(
        self, 
        config_data: ParameterHealthConfigCreate
    ) -> ParameterHealthConfig:
        """Create a new parameter health configuration.
        
        Args:
            config_data: Health configuration data
            
        Returns:
            Created ParameterHealthConfig instance
        """
        result = await self._session.execute(
            select(Device).where(Device.device_id == config_data.device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise ValueError(f"Device '{config_data.device_id}' not found")
        
        config = ParameterHealthConfig(
            device_id=config_data.device_id,
            tenant_id=config_data.tenant_id,
            parameter_name=config_data.parameter_name,
            normal_min=config_data.normal_min,
            normal_max=config_data.normal_max,
            max_min=config_data.max_min,
            max_max=config_data.max_max,
            weight=config_data.weight,
            ignore_zero_value=config_data.ignore_zero_value,
            is_active=config_data.is_active,
        )
        
        self._session.add(config)
        
        try:
            await self._session.commit()
            await self._session.refresh(config)
            logger.info(
                "Health config created",
                extra={
                    "config_id": config.id,
                    "device_id": config.device_id,
                    "parameter": config.parameter_name,
                }
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.error("Failed to create health config", extra={"error": str(e)})
            raise
        
        return config
    
    async def get_health_configs_by_device(
        self,
        device_id: str,
        tenant_id: Optional[str] = None
    ) -> List[ParameterHealthConfig]:
        """Get all health configurations for a device.
        
        Args:
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            List of ParameterHealthConfig instances
        """
        query = select(ParameterHealthConfig).where(
            ParameterHealthConfig.device_id == device_id
        )
        
        if tenant_id:
            query = query.where(ParameterHealthConfig.tenant_id == tenant_id)
        
        query = query.order_by(ParameterHealthConfig.parameter_name)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def get_health_config(
        self,
        config_id: int,
        device_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[ParameterHealthConfig]:
        """Get a specific health configuration by ID.
        
        Args:
            config_id: Configuration ID
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            ParameterHealthConfig instance or None
        """
        query = select(ParameterHealthConfig).where(
            ParameterHealthConfig.id == config_id,
            ParameterHealthConfig.device_id == device_id
        )
        
        if tenant_id:
            query = query.where(ParameterHealthConfig.tenant_id == tenant_id)
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_health_config(
        self,
        config_id: int,
        device_id: str,
        tenant_id: Optional[str],
        config_data: ParameterHealthConfigUpdate
    ) -> Optional[ParameterHealthConfig]:
        """Update an existing health configuration.
        
        Args:
            config_id: Configuration ID
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            config_data: Update data
            
        Returns:
            Updated ParameterHealthConfig instance or None
        """
        config = await self.get_health_config(config_id, device_id, tenant_id)
        
        if not config:
            return None
        
        update_data = config_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(config, field, value)
        
        try:
            await self._session.commit()
            await self._session.refresh(config)
            logger.info(
                "Health config updated",
                extra={"config_id": config.id}
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.error("Failed to update health config", extra={"error": str(e)})
            raise
        
        return config
    
    async def delete_health_config(
        self,
        config_id: int,
        device_id: str,
        tenant_id: Optional[str]
    ) -> bool:
        """Delete a health configuration.
        
        Args:
            config_id: Configuration ID
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            True if deleted, False if not found
        """
        config = await self.get_health_config(config_id, device_id, tenant_id)
        
        if not config:
            return False
        
        await self._session.delete(config)
        await self._session.commit()
        
        logger.info(
            "Health config deleted",
            extra={"config_id": config_id}
        )
        
        return True
    
    async def validate_weights(
        self,
        device_id: str,
        tenant_id: Optional[str] = None
    ) -> dict:
        """Validate that weights sum to 100%.
        
        Args:
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Dictionary with validation results
        """
        configs = await self.get_health_configs_by_device(device_id, tenant_id)
        active_configs = [c for c in configs if c.is_active]
        
        total_weight = sum(c.weight for c in active_configs)
        
        parameters = [
            {
                "parameter_name": c.parameter_name,
                "weight": c.weight,
                "is_active": c.is_active
            }
            for c in configs
        ]
        
        is_valid = abs(total_weight - 100.0) < 0.01
        
        return {
            "is_valid": is_valid,
            "total_weight": round(total_weight, 2),
            "message": "Weights sum to 100%" if is_valid else f"Weights sum to {total_weight}%, must equal 100%",
            "parameters": parameters
        }
    
    async def bulk_create_or_update(
        self,
        device_id: str,
        tenant_id: Optional[str],
        configs: List[dict]
    ) -> List[ParameterHealthConfig]:
        """Bulk create or update health configurations.
        
        Args:
            device_id: Device ID
            tenant_id: Optional tenant ID
            configs: List of configuration dictionaries
            
        Returns:
            List of created/updated configurations
        """
        result = []
        
        for config_dict in configs:
            param_name = config_dict.get("parameter_name")
            
            existing_query = select(ParameterHealthConfig).where(
                ParameterHealthConfig.device_id == device_id,
                ParameterHealthConfig.parameter_name == param_name
            )
            
            if tenant_id:
                existing_query = existing_query.where(
                    ParameterHealthConfig.tenant_id == tenant_id
                )
            
            existing_result = await self._session.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                for key, value in config_dict.items():
                    if value is not None and hasattr(existing, key):
                        setattr(existing, key, value)
                result.append(existing)
            else:
                new_config = ParameterHealthConfig(
                    device_id=device_id,
                    tenant_id=tenant_id,
                    **config_dict
                )
                self._session.add(new_config)
                result.append(new_config)
        
        await self._session.commit()
        
        for config in result:
            await self._session.refresh(config)
        
        return result
    
    def _calculate_raw_score(
        self,
        value: float,
        normal_min: Optional[float],
        normal_max: Optional[float],
        max_min: Optional[float],
        max_max: Optional[float]
    ) -> float:
        """Calculate raw health score for a parameter value.
        
        Case 1: Inside Normal Range (70-100)
        Case 2: Outside Normal Range, Within Max (25-69)
        Case 3: Beyond Maximum Range (0-25)
        
        Args:
            value: Actual parameter value
            normal_min: Normal range minimum
            normal_max: Normal range maximum
            max_min: Maximum range minimum
            max_max: Maximum range maximum
            
        Returns:
            Raw score (0-100)
        """
        if normal_min is None or normal_max is None:
            return 100.0
        
        ideal_center = (normal_min + normal_max) / 2
        half_range = (normal_max - normal_min) / 2
        
        if half_range == 0:
            half_range = 1
        
        if normal_min <= value <= normal_max:
            deviation = abs(value - ideal_center)
            raw_score = 100 - (deviation / half_range) * 30
            return max(70, min(100, raw_score))
        
        if max_min is not None and max_max is not None:
            if value < normal_min:
                if value < max_min:
                    return max(0, 25 - (max_min - value) * 10)
                overshoot = normal_min - value
                tolerance = normal_min - max_min
                if tolerance == 0:
                    tolerance = 1
                raw_score = 70 - (overshoot / tolerance) * 45
                return max(25, min(69, raw_score))
            else:
                if value > max_max:
                    return max(0, 25 - (value - max_max) * 10)
                overshoot = value - normal_max
                tolerance = max_max - normal_max
                if tolerance == 0:
                    tolerance = 1
                raw_score = 70 - (overshoot / tolerance) * 45
                return max(25, min(69, raw_score))
        
        if value < normal_min:
            deviation = normal_min - value
            raw_score = 70 - deviation * 10
            return max(25, min(69, raw_score))
        else:
            deviation = value - normal_max
            raw_score = 70 - deviation * 10
            return max(25, min(69, raw_score))
    
    def _get_status_and_color(self, score: float) -> tuple[str, str]:
        """Get status label and color based on score.
        
        Args:
            score: Raw score (0-100)
            
        Returns:
            Tuple of (status, color)
        """
        if score >= 85:
            return "Healthy", "🟢"
        elif score >= 70:
            return "Slight Warning", "🟡"
        elif score >= 40:
            return "Warning", "🟠"
        else:
            return "Critical", "🔴"
    
    def _get_health_status_and_color(self, score: float) -> tuple[str, str]:
        """Get overall health status label and color based on score.
        
        Args:
            score: Health score (0-100)
            
        Returns:
            Tuple of (status, color)
        """
        if score >= 90:
            return "Excellent", "🟢"
        elif score >= 75:
            return "Good", "🟡"
        elif score >= 50:
            return "At Risk", "🟠"
        else:
            return "Critical", "🔴"
    
    async def calculate_health_score(
        self,
        device_id: str,
        telemetry_values: Dict[str, float],
        machine_state: str = "RUNNING",
        tenant_id: Optional[str] = None
    ) -> dict:
        """Calculate device health score based on telemetry values.
        
        Args:
            device_id: Device ID
            telemetry_values: Dictionary of parameter names to values
            machine_state: Current machine operational state
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Dictionary with health score calculation results
        """
        machine_state = machine_state.upper() if machine_state else "RUNNING"
        
        if machine_state != "RUNNING":
            return {
                "device_id": device_id,
                "health_score": None,
                "status": "Standby",
                "status_color": "⚪",
                "message": f"Machine is {machine_state}. Health scoring only active when RUNNING.",
                "machine_state": machine_state,
                "parameter_scores": [],
                "total_weight_configured": 0.0,
                "parameters_included": 0,
                "parameters_skipped": 0
            }
        
        configs = await self.get_health_configs_by_device(device_id, tenant_id)
        active_configs = [c for c in configs if c.is_active]
        
        if not active_configs:
            return {
                "device_id": device_id,
                "health_score": None,
                "status": "Not Configured",
                "status_color": "⚪",
                "message": "No health parameters configured. Please configure parameter ranges and weights.",
                "machine_state": machine_state,
                "parameter_scores": [],
                "total_weight_configured": 0.0,
                "parameters_included": 0,
                "parameters_skipped": 0
            }
        
        weight_validation = await self.validate_weights(device_id, tenant_id)
        
        if not weight_validation["is_valid"]:
            return {
                "device_id": device_id,
                "health_score": None,
                "status": "Invalid Configuration",
                "status_color": "⚪",
                "message": f"Weight validation failed: {weight_validation['message']}",
                "machine_state": machine_state,
                "parameter_scores": [],
                "total_weight_configured": weight_validation["total_weight"],
                "parameters_included": 0,
                "parameters_skipped": 0
            }
        
        parameter_scores = []
        total_weighted_score = 0.0
        total_weight = 0.0
        parameters_included = 0
        parameters_skipped = 0
        
        for config in active_configs:
            param_name = config.parameter_name
            value = telemetry_values.get(param_name)
            
            if value is None:
                parameters_skipped += 1
                continue
            
            if value == 0 and config.ignore_zero_value:
                parameters_skipped += 1
                continue
            
            raw_score = self._calculate_raw_score(
                value,
                config.normal_min,
                config.normal_max,
                config.max_min,
                config.max_max
            )
            
            weighted_score = raw_score * (config.weight / 100.0)
            
            status, status_color = self._get_status_and_color(raw_score)
            
            parameter_scores.append({
                "parameter_name": param_name,
                "value": value,
                "raw_score": round(raw_score, 2),
                "weighted_score": round(weighted_score, 2),
                "weight": config.weight,
                "status": status,
                "status_color": status_color
            })
            
            total_weighted_score += weighted_score
            total_weight += config.weight
            parameters_included += 1
        
        if parameters_included == 0:
            return {
                "device_id": device_id,
                "health_score": None,
                "status": "No Data",
                "status_color": "⚪",
                "message": "No matching telemetry parameters found for configured health metrics.",
                "machine_state": machine_state,
                "parameter_scores": [],
                "total_weight_configured": total_weight,
                "parameters_included": 0,
                "parameters_skipped": parameters_skipped
            }
        
        health_score = round(total_weighted_score, 2)
        health_status, health_color = self._get_health_status_and_color(health_score)
        
        return {
            "device_id": device_id,
            "health_score": health_score,
            "status": health_status,
            "status_color": health_color,
            "message": f"Health score calculated from {parameters_included} parameter(s)",
            "machine_state": machine_state,
            "parameter_scores": parameter_scores,
            "total_weight_configured": total_weight,
            "parameters_included": parameters_included,
            "parameters_skipped": parameters_skipped
        }
