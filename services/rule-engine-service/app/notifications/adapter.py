"""Notification adapter layer for multi-channel alerting.

This module provides adapter interfaces for different notification
channels. Actual provider SDK implementations will be added in future.
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime

from app.models.rule import Rule
from app.config import settings

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    async def send(
        self,
        message: str,
        rule: Rule,
        device_id: str,
        **kwargs: Any,
    ) -> bool:
        """Send notification through this channel.
        
        Args:
            message: Notification message
            rule: Rule that triggered the notification
            device_id: Device identifier
            **kwargs: Additional channel-specific parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def send_alert(
        self,
        subject: str,
        message: str,
        rule: Rule,
        device_id: str,
        alert_type: str = "threshold_alert",
        **kwargs: Any,
    ) -> bool:
        """Send formatted alert notification.
        
        Args:
            subject: Email subject
            message: Alert message body
            rule: Rule that triggered
            device_id: Device identifier
            alert_type: Type of alert (rule_created, threshold_alert)
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if channel is healthy and available.
        
        Returns:
            True if channel is healthy
        """
        pass


class EmailAdapter(NotificationChannel):
    """Email notification adapter with SMTP support."""
    
    def __init__(self):
        self._enabled = settings.EMAIL_ENABLED
        self._smtp_host = settings.EMAIL_SMTP_HOST
        self._smtp_port = settings.EMAIL_SMTP_PORT
        self._smtp_username = settings.EMAIL_SMTP_USERNAME
        self._smtp_password = settings.EMAIL_SMTP_PASSWORD
        self._from_address = settings.EMAIL_FROM_ADDRESS
        self._to_address = settings.EMAIL_TO_ADDRESS
    
    async def send(
        self,
        message: str,
        rule: Rule,
        device_id: str,
        **kwargs: Any,
    ) -> bool:
        """Send email notification."""
        device_names = kwargs.get("device_names")
        return await self.send_alert(
            subject=f"Alert: {rule.rule_name}",
            message=message,
            rule=rule,
            device_id=device_id,
            alert_type="threshold_alert",
            device_names=device_names
        )
    
    async def send_alert(
        self,
        subject: str,
        message: str,
        rule: Rule,
        device_id: str,
        alert_type: str = "threshold_alert",
        device_names: str = None,
        **kwargs: Any,
    ) -> bool:
        """Send formatted email alert."""
        if not self._enabled:
            logger.info(
                "Email notifications disabled",
                extra={"channel": "email"}
            )
            return True
        
        if not self._smtp_username or not self._smtp_password:
            logger.warning(
                "Email not configured - SMTP credentials missing",
                extra={"channel": "email"}
            )
            return False
        
        recipients = [r.strip() for r in self._to_address.split(",") if r.strip()]
        if not recipients:
            logger.warning(
                "Email not configured - no recipients",
                extra={"channel": "email"}
            )
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_address
            msg["To"] = ", ".join(recipients)
            
            if alert_type == "rule_created":
                html_content = self._format_rule_created_message(rule, device_id, message, device_names)
            else:
                html_content = self._format_alert_message(rule, device_id, message)
            
            text_part = MIMEText(message, "plain")
            html_part = MIMEText(html_content, "html")
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls(context=context)
                server.login(self._smtp_username, self._smtp_password)
                server.sendmail(self._from_address, recipients, msg.as_string())
            
            logger.info(
                "Email sent successfully",
                extra={
                    "channel": "email",
                    "to": recipients,
                    "subject": subject,
                    "rule_id": str(rule.rule_id) if rule.rule_id else None,
                    "device_id": device_id,
                    "alert_type": alert_type,
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                extra={
                    "channel": "email",
                    "error": str(e),
                    "rule_id": str(rule.rule_id) if rule.rule_id else None,
                    "device_id": device_id,
                }
            )
            return False
    
    def _format_alert_message(self, rule: Rule, device_id: str, message: str) -> str:
        """Format threshold alert email."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f8f9fa; }}
        .alert-box {{ background: white; border-left: 4px solid #dc3545; padding: 15px; margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .label {{ font-weight: bold; color: #555; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 Energy Alert</h2>
        </div>
        <div class="content">
            <div class="alert-box">
                <p><span class="label">Rule:</span> {rule.rule_name}</p>
                <p><span class="label">Device ID:</span> {device_id}</p>
                <p><span class="label">Property:</span> {rule.property}</p>
                <p><span class="label">Condition:</span> {rule.condition} {rule.threshold}</p>
                <p><span class="label">Message:</span> {message}</p>
                <p><span class="label">Time:</span> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
        </div>
        <div class="footer">
            <p>This is an automated alert from Energy Platform</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _format_rule_created_message(self, rule: Rule, device_id: str, message: str, device_names: str = None) -> str:
        """Format rule created confirmation email."""
        status_value = rule.status.value if hasattr(rule.status, 'value') else str(rule.status)
        
        devices_display = device_names if device_names else device_id
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #28a745; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background: #f8f9fa; }}
        .info-box {{ background: white; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .label {{ font-weight: bold; color: #555; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>✅ Rule Created Successfully</h2>
        </div>
        <div class="content">
            <p>A new monitoring rule has been created in the Energy Platform.</p>
            
            <div class="info-box">
                <p><span class="label">Rule Name:</span> {rule.rule_name}</p>
                <p><span class="label">Rule ID:</span> {rule.rule_id}</p>
                <p><span class="label">Devices:</span> {devices_display}</p>
                <p><span class="label">Status:</span> {status_value}</p>
                <p><span class="label">Property:</span> {rule.property}</p>
                <p><span class="label">Condition:</span> {rule.condition} {rule.threshold}</p>
                <p><span class="label">Notification Channels:</span> {', '.join(rule.notification_channels) if rule.notification_channels else 'None'}</p>
                <p><span class="label">Created:</span> {rule.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if rule.created_at else datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <p>{message}</p>
        </div>
        <div class="footer">
            <p>This is a confirmation email from Energy Platform</p>
        </div>
    </div>
</body>
</html>
"""
    
    async def health_check(self) -> bool:
        """Check email service health."""
        if not self._enabled:
            return False
        
        try:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_username, self._smtp_password)
            return True
        except Exception as e:
            logger.error(f"Email health check failed: {e}")
            return False


class WhatsAppAdapter(NotificationChannel):
    """WhatsApp notification adapter (placeholder for Twilio)."""
    
    def __init__(self):
        self._enabled = settings.WHATSAPP_ENABLED
        self._from_number = "whatsapp:+14155238886"
    
    async def send(
        self,
        message: str,
        rule: Rule,
        device_id: str,
        **kwargs: Any,
    ) -> bool:
        """Send WhatsApp notification."""
        return await self.send_alert(
            subject=f"Alert: {rule.rule_name}",
            message=message,
            rule=rule,
            device_id=device_id,
            alert_type="threshold_alert"
        )
    
    async def send_alert(
        self,
        subject: str,
        message: str,
        rule: Rule,
        device_id: str,
        alert_type: str = "threshold_alert",
        **kwargs: Any,
    ) -> bool:
        """Send WhatsApp notification."""
        logger.info(
            "WhatsApp notification placeholder",
            extra={
                "channel": "whatsapp",
                "rule_id": str(rule.rule_id),
                "device_id": device_id,
                "alert_type": alert_type,
            }
        )
        return True
    
    async def health_check(self) -> bool:
        """Check WhatsApp service health."""
        return self._enabled


class TelegramAdapter(NotificationChannel):
    """Telegram notification adapter (placeholder for Bot API)."""
    
    def __init__(self):
        self._enabled = settings.TELEGRAM_ENABLED
    
    async def send(
        self,
        message: str,
        rule: Rule,
        device_id: str,
        **kwargs: Any,
    ) -> bool:
        """Send Telegram notification."""
        return await self.send_alert(
            subject=f"Alert: {rule.rule_name}",
            message=message,
            rule=rule,
            device_id=device_id,
            alert_type="threshold_alert"
        )
    
    async def send_alert(
        self,
        subject: str,
        message: str,
        rule: Rule,
        device_id: str,
        alert_type: str = "threshold_alert",
        **kwargs: Any,
    ) -> bool:
        """Send Telegram notification."""
        logger.info(
            "Telegram notification placeholder",
            extra={
                "channel": "telegram",
                "rule_id": str(rule.rule_id),
                "device_id": device_id,
                "alert_type": alert_type,
            }
        )
        return True
    
    async def health_check(self) -> bool:
        """Check Telegram service health."""
        return self._enabled


class NotificationAdapter:
    """Main notification adapter that routes to appropriate channels."""
    
    def __init__(self):
        self._adapters: Dict[str, NotificationChannel] = {
            "email": EmailAdapter(),
            "whatsapp": WhatsAppAdapter(),
            "telegram": TelegramAdapter(),
        }
    
    async def send(
        self,
        channel: str,
        message: str,
        rule: Rule,
        device_id: str,
        **kwargs: Any,
    ) -> bool:
        """Send notification through specified channel."""
        if channel not in self._adapters:
            raise ValueError(f"Unsupported notification channel: {channel}")
        
        adapter = self._adapters[channel]
        return await adapter.send(message, rule, device_id, **kwargs)
    
    async def send_alert(
        self,
        channel: str,
        subject: str,
        message: str,
        rule: Rule,
        device_id: str,
        alert_type: str = "threshold_alert",
        **kwargs: Any,
    ) -> bool:
        """Send formatted alert through specified channel."""
        if channel not in self._adapters:
            raise ValueError(f"Unsupported notification channel: {channel}")
        
        adapter = self._adapters[channel]
        return await adapter.send_alert(subject, message, rule, device_id, alert_type, **kwargs)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all notification channels."""
        results = {}
        for channel_name, adapter in self._adapters.items():
            try:
                results[channel_name] = await adapter.health_check()
            except Exception as e:
                logger.error(
                    f"Health check failed for {channel_name}",
                    extra={"error": str(e)}
                )
                results[channel_name] = False
        
        return results
    
    def get_supported_channels(self) -> list:
        """Get list of supported notification channels."""
        return list(self._adapters.keys())


notification_adapter = NotificationAdapter()


