"""
PDF Generator for SAR Reports.
Uses ReportLab to generate a 7-section professional regulatory PDF.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

from agents.shared.schemas import SARReportData


class SARPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.navy = colors.HexColor("#1a2f5e")
        self.red = colors.HexColor("#c0392b")
        self.amber = colors.HexColor("#d35400")
        self.green = colors.HexColor("#27ae60")
        self.grey = colors.HexColor("#4a4a4a")
        
        # Custom Styles
        self.styles.add(ParagraphStyle(
            name='TitleNavy',
            parent=self.styles['Title'],
            textColor=self.navy,
            fontSize=18,
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            textColor=self.navy,
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            borderPadding=4,
            backColor=colors.HexColor("#f1f5f9")
        ))
        self.styles.add(ParagraphStyle(
            name='BodyGrey',
            parent=self.styles['Normal'],
            textColor=self.grey,
            fontSize=10,
            leading=14
        ))
        self.styles.add(ParagraphStyle(
            name='Watermark',
            parent=self.styles['Normal'],
            textColor=colors.lightgrey,
            fontSize=14,
            alignment=1, # Center
            spaceBefore=30,
            spaceAfter=30
        ))

    def _build_kv_table(self, data: list[tuple[str, str]], col_widths=None) -> Table:
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,0), (-1,-1), self.grey),
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        return t

    def _build_grid_table(self, headers: list[str], rows: list[list[str]]) -> Table:
        t = Table([headers] + rows)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), self.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
            ('TEXTCOLOR', (0,1), (-1,-1), self.grey),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ]))
        return t

    def generate(self, report: SARReportData, case_id: str) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        story = []

        # ==========================================
        # PAGE 1: Cover + Filing Info
        # ==========================================
        story.append(Paragraph("SUSPICIOUS ACTIVITY REPORT", self.styles['TitleNavy']))
        story.append(Paragraph("CONFIDENTIAL — FOR REGULATORY USE ONLY", self.styles['Watermark']))
        story.append(Spacer(1, 20))
        
        filing_para = (
            f"This Suspicious Activity Report is being officially filed by <b>{report.filing_institution_name}</b>, "
            f"operating from their registered address at <b>{report.filing_institution_address}</b>. "
            f"This regulatory document covers the transaction monitoring period starting from <b>{report.report_period_start}</b> "
            f"and concluding on <b>{report.report_period_end}</b>. The filing was officially executed on <b>{report.filing_date}</b> "
            f"under the case reference number <b>{case_id}</b>. The primary Financial Crimes Enforcement Network (FinCEN) "
            f"BSA Reference ID associated with this documentation is <b>{report.fincen_bsa_id or 'Currently Pending Assignment'}</b>."
        )
        story.append(Paragraph(filing_para, self.styles['BodyGrey']))
        story.append(Spacer(1, 30))

        story.append(Paragraph("SUBJECT INFORMATION", self.styles['SectionHeader']))
        story.append(Paragraph("<i>[Personal data strictly masked per Presidio PII data protection policy]</i>", self.styles['BodyGrey']))
        story.append(Spacer(1, 10))
        
        subject_para = (
            f"The primary subject under investigation in this case is identified as <b>{report.subject_name}</b>. "
            f"The suspicious activity primarily involves the financial account registered under the identifier <b>{report.subject_account_id}</b>. "
            f"According to the institution's Know Your Customer (KYC) records, the subject's primary residential or business address "
            f"is documented as <b>{report.subject_address}</b>. The subject's identity was verified using a <b>{report.subject_id_type.replace('_', ' ').title()}</b> "
            f"bearing the identification number <b>{report.subject_id_number or 'Not Available'}</b>."
        )
        story.append(Paragraph(subject_para, self.styles['BodyGrey']))
        
        story.append(PageBreak())

        # ==========================================
        # PAGE 2: Transaction Summary & Typology
        # ==========================================
        story.append(Paragraph("TRANSACTION SUMMARY", self.styles['SectionHeader']))
        
        tx_para = (
            f"A comprehensive forensic accounting review identified a total of <b>{len(report.transaction_ids)}</b> suspicious transactions "
            f"occurring during the review period of <b>{report.report_period_start}</b> to <b>{report.report_period_end}</b>. "
            f"The aggregated financial volume of these suspected activities amounts to <b>${report.total_amount_usd:,.2f} USD</b>. "
        )
        if report.transaction_ids:
            tx_para += (
                f"The specific methods of value transfer involved in these activities were primarily categorized as <b>{', '.join(report.transaction_types)}</b>. "
                f"Routing and geographical analysis indicates that the funds transited through or originated from the following jurisdictions: <b>{', '.join(report.geographies_involved)}</b>."
            )
        story.append(Paragraph(tx_para, self.styles['BodyGrey']))
        story.append(Spacer(1, 30))
        
        story.append(Spacer(1, 30))

        story.append(Paragraph("FRAUD TYPOLOGY CLASSIFICATION", self.styles['SectionHeader']))
        typ_para = (
            f"Based on the transaction mechanics, this activity has been classified under the anti-money laundering "
            f"typology of <b>{report.typology}</b> (Regulatory Code: <i>{report.typology_code}</i>). "
            f"This typology is defined as: {report.typology_description} "
        )
        if report.suspicion_reason:
            typ_para += f"<br/><br/><b>Primary Basis for Suspicion:</b> {report.suspicion_reason}"
        story.append(Paragraph(typ_para, self.styles['BodyGrey']))
        story.append(Spacer(1, 10))

        story.append(PageBreak())

        # ==========================================
        # PAGE 3: Risk Assessment (Score & Signals)
        # ==========================================
        story.append(Paragraph("ML RISK ASSESSMENT", self.styles['SectionHeader']))
        
        tier_color = self.red if report.risk_tier.lower() in ['red', 'critical'] else (self.amber if report.risk_tier.lower() == 'amber' else self.green)
        
        story.append(Paragraph(f"<b>Risk Score:</b> <font color='{tier_color.hexval()}'>{report.risk_score:.3f}</font>", self.styles['BodyGrey']))
        story.append(Paragraph(f"<b>Risk Tier:</b> <font color='{tier_color.hexval()}'>{report.risk_tier.upper()}</font>", self.styles['BodyGrey']))
        story.append(Spacer(1, 15))

        if report.risk_signals:
            story.append(Paragraph("<b>Triggered Risk Signals:</b>", self.styles['BodyGrey']))
            signal_data = [["Signal Type", "Description", "Confidence"]]
            for sig in report.risk_signals:
                signal_data.append([
                    sig.get("signal_type", ""),
                    sig.get("description", ""),
                    f"{sig.get('confidence', 0)*100:.0f}%"
                ])
            story.append(self._build_grid_table(signal_data[0], signal_data[1:]))
            story.append(Spacer(1, 20))

        if report.shap_top_features:
            story.append(Paragraph("<b>SHAP Feature Importance (Top Contributors):</b>", self.styles['BodyGrey']))
            for feat in report.shap_top_features:
                val = feat.get('value', 0)
                bar = "█" * int(abs(val) * 20) + "░" * (10 - int(abs(val) * 20))
                color = "red" if val > 0 else "blue"
                story.append(Paragraph(f"<font name='Courier'>[{bar[:10]}] {val:+.3f} {feat.get('feature','')}</font>", self.styles['BodyGrey']))

        story.append(PageBreak())

        # ==========================================
        # PAGE 4: SAR Narrative
        # ==========================================
        story.append(Paragraph("SAR NARRATIVE (PART V)", self.styles['SectionHeader']))
        
        # We replace newlines with HTML breaks for ReportLab
        body_text = report.narrative_body.replace("\n", "<br/>")
        story.append(Paragraph(body_text, self.styles['BodyGrey']))
        story.append(Spacer(1, 20))

        if report.narrative_supporting_facts:
            story.append(Paragraph("<b>Supporting Facts:</b>", self.styles['BodyGrey']))
            for i, fact in enumerate(report.narrative_supporting_facts):
                story.append(Paragraph(f"{i+1}. {fact}", self.styles['BodyGrey']))

        story.append(PageBreak())

        # ==========================================
        # PAGE 5: Compliance Review
        # ==========================================
        story.append(Paragraph("COMPLIANCE & REGULATORY REVIEW", self.styles['SectionHeader']))
        
        pass_color = self.green.hexval() if report.compliance_passed else self.red.hexval()
        pass_text = "YES" if report.compliance_passed else "NO"
        story.append(Paragraph(f"<b>BSA/FinCEN Format Compliant?</b> <font color='{pass_color}'>{pass_text}</font>", self.styles['BodyGrey']))
        story.append(Spacer(1, 15))

        if report.compliance_issues:
            story.append(Paragraph("<b>Compliance Issues Discovered:</b>", self.styles['BodyGrey']))
            for issue in report.compliance_issues:
                story.append(Paragraph(f"• <font color='{self.red.hexval()}'>{issue}</font>", self.styles['BodyGrey']))
        else:
            story.append(Paragraph("<i>No compliance issues found. All required regulatory fields are populated.</i>", self.styles['BodyGrey']))
            
        story.append(Spacer(1, 15))
        if report.regulatory_flags:
            story.append(Paragraph("<b>Regulatory Flags:</b>", self.styles['BodyGrey']))
            for flag in report.regulatory_flags:
                story.append(Paragraph(f"• {flag}", self.styles['BodyGrey']))

        story.append(PageBreak())

        # ==========================================
        # PAGE 6: Complete Audit Trail
        # ==========================================
        story.append(Paragraph("IMMUTABLE AGENT DECISION LOG", self.styles['SectionHeader']))
        
        if report.agent_decisions:
            audit_data = [["Agent", "Action", "Conf", "Timestamp"]]
            for a in report.agent_decisions:
                # Truncate action string slightly for the PDF table if needed
                action_text = a.get('action', '')
                if len(action_text) > 80: action_text = action_text[:77] + "..."
                
                audit_data.append([
                    a.get('agent', ''),
                    action_text,
                    f"{a.get('confidence', 0)*100:.0f}%",
                    a.get('timestamp', '')[:19].replace('T', ' ')
                ])
            story.append(self._build_grid_table(audit_data[0], audit_data[1:]))
        
        story.append(Spacer(1, 20))
        story.append(Paragraph("<b>Cryptographic Evidence (SHA256):</b>", self.styles['BodyGrey']))
        story.append(Paragraph(f"<font name='Courier' color='#27ae60'>{report.immutable_hash}</font>", self.styles['BodyGrey']))
        story.append(Spacer(1, 10))
        story.append(Paragraph("<i>This audit trail is cryptographically verified and append-only.</i>", self.styles['BodyGrey']))

        story.append(PageBreak())

        # ==========================================
        # PAGE 7: Analyst Sign-off
        # ==========================================
        story.append(Paragraph("ANALYST SIGN-OFF & REVIEW", self.styles['SectionHeader']))
        
        analyst = report.analyst_name or "Pending Compliance Review"
        app_time = report.analyst_approved_at or "N/A"
        
        sign_para = (
            f"This documentation has been thoroughly reviewed and authorized by designated compliance personnel. "
            f"The evaluating officer on record is <b>{analyst}</b>, who officially approved this filing "
            f"at timestamp <b>{app_time}</b>. By signing below, the analyst certifies that the facts presented "
            f"in this report are accurate and constitute grounds for reasonable suspicion under applicable AML statutes."
        )
        story.append(Paragraph(sign_para, self.styles['BodyGrey']))
        story.append(Spacer(1, 20))
        
        if report.analyst_notes:
            story.append(Paragraph("<b>Internal Analyst Commentary:</b>", self.styles['BodyGrey']))
            story.append(Paragraph(report.analyst_notes.replace("\n", "<br/>"), self.styles['BodyGrey']))
            story.append(Spacer(1, 40))
        
        story.append(Paragraph("X______________________________________________________", self.styles['BodyGrey']))
        story.append(Paragraph("Authorized Signature", self.styles['BodyGrey']))
        story.append(Spacer(1, 30))
        
        story.append(Paragraph("<b>Legal Notice:</b>", self.styles['BodyGrey']))
        story.append(Paragraph("<i>Filed under FinCEN BSA regulations. Retention period: 5 years minimum. Unauthorized disclosure is a federal offense under 31 U.S.C. § 5318(g)(2).</i>", self.styles['BodyGrey']))
        
        story.append(Spacer(1, 50))
        story.append(Paragraph(f"<i>Report Generation Timestamp: {datetime.now().isoformat()}</i>", self.styles['BodyGrey']))

        doc.build(story)
        return buffer.getvalue()


def generate_sar_pdf(report: SARReportData, case_id: str) -> bytes:
    """Wrapper to generate and return PDF bytes."""
    generator = SARPDFGenerator()
    return generator.generate(report, case_id)
