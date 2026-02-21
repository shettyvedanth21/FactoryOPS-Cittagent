"""File generator service for creating reports in various formats."""

import io
import json
from datetime import datetime
from typing import Any, Dict, List
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)

from src.models.report import ReportFormat
from src.utils.exceptions import FileGenerationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FileGenerator:
    """Generates reports in PDF, Excel, or JSON format."""
    
    async def generate(
        self,
        format_type: ReportFormat,
        telemetry_data: pd.DataFrame,
        anomaly_data: pd.DataFrame,
        prediction_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        summary: dict,
        report_metadata: dict
    ) -> bytes:
        """Generate report in specified format.
        
        Args:
            format_type: Output format (pdf, excel, json)
            telemetry_data: Telemetry data DataFrame
            anomaly_data: Anomaly results DataFrame
            prediction_data: Prediction results DataFrame
            forecast_data: Forecast results DataFrame
            summary: Report summary statistics
            report_metadata: Report metadata (title, dates, etc.)
            
        Returns:
            Report as bytes
            
        Raises:
            FileGenerationError: If generation fails
        """
        logger.info(
            "Generating report",
            format=format_type.value,
            telemetry_rows=len(telemetry_data),
            anomaly_rows=len(anomaly_data),
            prediction_rows=len(prediction_data),
            forecast_rows=len(forecast_data)
        )
        
        try:
            if format_type == ReportFormat.PDF:
                return await self._generate_pdf(
                    telemetry_data, anomaly_data, prediction_data,
                    forecast_data, summary, report_metadata
                )
            elif format_type == ReportFormat.EXCEL:
                return await self._generate_excel(
                    telemetry_data, anomaly_data, prediction_data,
                    forecast_data, summary, report_metadata
                )
            elif format_type == ReportFormat.JSON:
                return await self._generate_json(
                    telemetry_data, anomaly_data, prediction_data,
                    forecast_data, summary, report_metadata
                )
            else:
                raise FileGenerationError(f"Unsupported format: {format_type}")
                
        except Exception as e:
            logger.error("Failed to generate report", error=str(e), format=format_type.value)
            raise FileGenerationError(f"Report generation failed: {str(e)}", format_type=format_type.value)
    
    async def _generate_pdf(
        self,
        telemetry_data: pd.DataFrame,
        anomaly_data: pd.DataFrame,
        prediction_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        summary: dict,
        metadata: dict
    ) -> bytes:
        """Generate PDF report."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        story.append(Paragraph("Energy Intelligence Report", title_style))
        story.append(Spacer(1, 12))
        
        # Metadata
        story.append(Paragraph(f"<b>Generated:</b> {metadata.get('generated_at', datetime.utcnow().isoformat())}", styles["Normal"]))
        story.append(Paragraph(f"<b>Period:</b> {metadata.get('start_time')} to {metadata.get('end_time')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Devices:</b> {', '.join(metadata.get('device_ids', []))}", styles["Normal"]))
        story.append(Spacer(1, 20))
        
        # Summary Section
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        story.append(Spacer(1, 12))
        
        summary_data = [
            ["Metric", "Value"],
            ["Total Devices", str(summary.get("total_devices", 0))],
            ["Total Records", str(summary.get("total_records", 0))],
            ["Anomalies Detected", str(summary.get("anomaly_summary", {}).get("total_anomalies", 0))],
            ["High Risk Devices", str(summary.get("prediction_summary", {}).get("high_risk_count", 0))]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Telemetry Summary
        if not telemetry_data.empty:
            story.append(PageBreak())
            story.append(Paragraph("Telemetry Summary", styles["Heading2"]))
            story.append(Spacer(1, 12))
            
            metrics = summary.get("telemetry_summary", {}).get("metrics", {})
            if metrics:
                metric_rows = [["Metric", "Mean", "Min", "Max", "Std Dev"]]
                for metric, stats in metrics.items():
                    metric_rows.append([
                        metric.capitalize(),
                        f"{stats.get('mean', 0):.2f}",
                        f"{stats.get('min', 0):.2f}",
                        f"{stats.get('max', 0):.2f}",
                        f"{stats.get('std', 0):.2f}"
                    ])
                
                metric_table = Table(metric_rows)
                metric_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(metric_table)
        
        # Anomaly Section
        if not anomaly_data.empty:
            story.append(PageBreak())
            story.append(Paragraph("Anomaly Detection Results", styles["Heading2"]))
            story.append(Spacer(1, 12))
            
            # Show top anomalies
            top_anomalies = anomaly_data[anomaly_data["is_anomaly"] == True].head(10)
            if not top_anomalies.empty:
                anomaly_rows = [["Timestamp", "Device", "Score", "Severity"]]
                for _, row in top_anomalies.iterrows():
                    anomaly_rows.append([
                        str(row.get("timestamp", ""))[:19],
                        row.get("device_id", ""),
                        f"{row.get('anomaly_score', 0):.3f}",
                        row.get("severity", "")
                    ])
                
                anomaly_table = Table(anomaly_rows)
                anomaly_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(anomaly_table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    async def _generate_excel(
        self,
        telemetry_data: pd.DataFrame,
        anomaly_data: pd.DataFrame,
        prediction_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        summary: dict,
        metadata: dict
    ) -> bytes:
        """Generate Excel report with multiple sheets."""
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([
                {"Metric": "Total Devices", "Value": summary.get("total_devices", 0)},
                {"Metric": "Total Records", "Value": summary.get("total_records", 0)},
                {"Metric": "Time Range Start", "Value": metadata.get("start_time")},
                {"Metric": "Time Range End", "Value": metadata.get("end_time")},
                {"Metric": "Generated At", "Value": metadata.get("generated_at")}
            ])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Telemetry data sheet
            if not telemetry_data.empty:
                # Limit columns for Excel
                display_df = telemetry_data.head(10000)  # Limit rows
                display_df.to_excel(writer, sheet_name='Telemetry', index=False)
            
            # Anomalies sheet
            if not anomaly_data.empty:
                anomaly_display = anomaly_data[anomaly_data["is_anomaly"] == True] if "is_anomaly" in anomaly_data.columns else anomaly_data
                anomaly_display.head(5000).to_excel(writer, sheet_name='Anomalies', index=False)
            
            # Predictions sheet
            if not prediction_data.empty:
                prediction_data.head(5000).to_excel(writer, sheet_name='Predictions', index=False)
            
            # Forecasts sheet
            if not forecast_data.empty:
                forecast_data.head(5000).to_excel(writer, sheet_name='Forecasts', index=False)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    async def _generate_json(
        self,
        telemetry_data: pd.DataFrame,
        anomaly_data: pd.DataFrame,
        prediction_data: pd.DataFrame,
        forecast_data: pd.DataFrame,
        summary: dict,
        metadata: dict
    ) -> bytes:
        """Generate JSON report."""
        report = {
            "metadata": metadata,
            "summary": summary,
            "data": {
                "telemetry": telemetry_data.to_dict('records') if not telemetry_data.empty else [],
                "anomalies": anomaly_data.to_dict('records') if not anomaly_data.empty else [],
                "predictions": prediction_data.to_dict('records') if not prediction_data.empty else [],
                "forecasts": forecast_data.to_dict('records') if not forecast_data.empty else []
            }
        }
        
        return json.dumps(report, indent=2, default=str).encode('utf-8')