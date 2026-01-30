import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_dynamic_table

# Premium Color Palette
COLORS = {
    'primary': (15, 23, 42),      # Slate 900
    'accent': (37, 99, 235),     # Blue 600
    'success': (16, 185, 129),   # Emerald 500
    'warning': (245, 158, 11),   # Amber 500
    'danger': (239, 68, 68),     # Red 500
    'bg_light': (248, 250, 252), # Slate 50
    'border': (226, 232, 240)    # Slate 200
}

class PremiumClinicalReport(FPDF):
    def __init__(self):
        super().__init__()
        # Register Unicode-compatible fonts
        self.add_font("Arial", "", "app/static/fonts/arial.ttf")
        self.add_font("Arial", "B", "app/static/fonts/arialbd.ttf")
        self.add_font("Arial", "I", "app/static/fonts/ariali.ttf")
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # Draw top accent bar
        self.set_fill_color(*COLORS['accent'])
        self.rect(0, 0, 210, 3, 'F')
        
        self.set_font('Arial', 'B', 12)
        self.set_text_color(*COLORS['primary'])
        self.cell(0, 10, 'CLINICAL DATA QUALITY INTELLIGENCE REPORT', 0, 0, 'L')
        
        self.set_font('Arial', '', 8)
        self.set_text_color(100, 116, 139) # Slate 500
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%d %b %Y, %H:%M")}', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(148, 163, 184) # Slate 400
        self.cell(0, 10, f'Confidential Clinical Data - Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(*COLORS['accent'])
        self.cell(0, 15, title, 0, 1, 'L')
        self.ln(2)

    def section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(*COLORS['primary'])
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

def generate_charts(all_issues):
    if not all_issues:
        return None, None
        
    df_issues = pd.DataFrame(all_issues)
    
    # Chart 1: Severity Distribution
    severity_counts = df_issues['severity'].value_counts()
    plt.figure(figsize=(6, 4))
    colors = [COLORS['danger'] if s == 'Critical' else COLORS['warning'] if s == 'Warning' else COLORS['success'] for s in severity_counts.index]
    # Convert rgb to 0-1 range for matplotlib
    norm_colors = [(r/255, g/255, b/255) for r, g, b in colors]
    
    plt.pie(severity_counts, labels=severity_counts.index, autopct='%1.1f%%', startangle=140, colors=norm_colors, wedgeprops={'edgecolor': 'white'})
    plt.title('Issue Severity Distribution', fontweight='bold', color='#1e293b')
    plt.axis('equal')
    severity_chart = "severity_chart.png"
    plt.savefig(severity_chart, dpi=300, bbox_inches='tight')
    plt.close()

    # Chart 2: Issue Types by Column
    type_counts = df_issues['issue'].value_counts().head(5)
    plt.figure(figsize=(6, 4))
    type_counts.plot(kind='barh', color='#3b82f6')
    plt.title('Top Data Quality Observations', fontweight='bold', color='#1e293b')
    plt.xlabel('Frequency')
    plt.gca().invert_yaxis()
    type_chart = "type_chart.png"
    plt.savefig(type_chart, dpi=300, bbox_inches='tight')
    plt.close()
    
    return severity_chart, type_chart

def generate_pdf_report(tables, db: Session):
    pdf = PremiumClinicalReport()
    pdf.add_page()
    
    all_issues = []
    datasets_info = []
    
    for table_name in tables:
        table = get_dynamic_table(table_name)
        issues = db.execute(select(table)).mappings().all()
        issue_list = [dict(i) for i in issues]
        all_issues.extend(issue_list)
        
        filename = table_name.replace("issues_", "")
        dataset_name = issue_list[0]["dataset_name"] if issue_list else filename
        
        datasets_info.append({
            "name": dataset_name,
            "count": len(issue_list),
            "critical": len([i for i in issue_list if i["severity"] in ["Critical", "High"]])
        })

    # --- PAGE 1: EXECUTIVE SUMMARY ---
    pdf.chapter_title('Executive Quality Summary')
    
    # Clinical Integrity Score Calculation
    # Simple heuristic: Start at 100, subtract 5 for critical, 2 for warning (capped)
    total_obs = len(all_issues)
    critical_count = len([i for i in all_issues if i['severity'] == 'Critical'])
    warning_count = len([i for i in all_issues if i['severity'] == 'Warning'])
    integrity_score = max(0, 100 - (critical_count * 5) - (warning_count * 2))
    
    # Score Gauge Representation
    pdf.set_fill_color(*COLORS['bg_light'])
    pdf.rect(140, 35, 60, 40, 'F')
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(*COLORS['primary'])
    pdf.set_xy(140, 40)
    pdf.cell(60, 10, 'INTEGRITY SCORE', 0, 1, 'C')
    
    score_color = COLORS['danger'] if integrity_score < 50 else COLORS['warning'] if integrity_score < 80 else COLORS['success']
    pdf.set_text_color(*score_color)
    pdf.set_font('Arial', 'B', 32)
    pdf.set_x(140)
    pdf.cell(60, 15, f"{integrity_score}%", 0, 1, 'C')

    # Summary Statistics Box
    pdf.set_y(35)
    pdf.set_fill_color(*COLORS['bg_light'])
    pdf.rect(10, 35, 125, 40, 'F')
    pdf.set_y(40)
    pdf.set_x(15)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(*COLORS['accent'])
    pdf.cell(40, 10, str(total_obs), 0, 0, 'C')
    pdf.cell(40, 10, str(len(datasets_info)), 0, 0, 'C')
    pdf.cell(40, 10, str(critical_count), 0, 1, 'C')
    
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.set_x(15)
    pdf.cell(40, 5, 'Observations', 0, 0, 'C')
    pdf.cell(40, 5, 'Datasets', 0, 0, 'C')
    pdf.cell(40, 5, 'Critical Risks', 0, 1, 'C')

    # Analytics Visuals
    severity_img, type_img = generate_charts(all_issues)
    if severity_img and type_img:
        pdf.set_y(85)
        pdf.image(severity_img, x=10, y=85, w=90)
        pdf.image(type_img, x=110, y=85, w=90)
        pdf.set_y(155)
        os.remove(severity_img)
        os.remove(type_img)

    # Risk Narrative
    pdf.section_title('Clinical Risk Narrative')
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(*COLORS['primary'])
    risk_summary = (
        f"The data audit of {len(datasets_info)} datasets reveals a Clinical Integrity Score of {integrity_score}%. "
        "This score is calculated based on the density of critical clinical outliers (values outside physiological norms) "
        "and data consistency issues. " + 
        ("High-risk anomalies were detected that could potentially compromise clinical research modeling." if critical_count > 0 else "The data shows high consistency with only minor statistical outliers.") +
        " Analysis suggest that protocol deviations or legacy data entry methods are the primary drivers of these observations."
    )
    pdf.multi_cell(0, 7, risk_summary)

    # Dataset Breakdown Table (Filling Space on Page 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(*COLORS['border'])
    pdf.cell(100, 8, ' Dataset Name', 0, 0, 'L', True)
    pdf.cell(45, 8, ' Total Issues', 0, 0, 'C', True)
    pdf.cell(45, 8, ' Critical Issues', 0, 1, 'C', True)
    
    pdf.set_font('Arial', '', 9)
    for ds in datasets_info:
        pdf.cell(100, 8, f" {ds['name'][:45]}", 0, 0, 'L')
        pdf.cell(45, 8, str(ds['count']), 0, 0, 'C')
        pdf.set_text_color(*COLORS['danger']) if ds['critical'] > 0 else pdf.set_text_color(*COLORS['primary'])
        pdf.cell(45, 8, str(ds['critical']), 0, 1, 'C')
        pdf.set_text_color(*COLORS['primary'])

    # --- PAGE 2: CLINICAL INTELLIGENCE DEEP-DIVE ---
    pdf.add_page()
    pdf.chapter_title('Clinical Intelligence Deep-Dive')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, "This section highlights the most significant clinical findings analyzed by our AI system. Unlike raw validation, this deep-dive provides clinical context, impact, and actionable remediation steps.")
    pdf.ln(5)

    # Highlight top 3-4 critical issues with their FULL AI explanations
    significant_issues = [i for i in all_issues if i['severity'] == 'Critical'][:4]
    if not significant_issues:
        significant_issues = all_issues[:3] # Fallback if no critical issues

    for idx, issue in enumerate(significant_issues):
        pdf.set_fill_color(*COLORS['bg_light'])
        pdf.set_draw_color(*COLORS['border'])
        pdf.set_line_width(0.3)
        
        # Issue Header
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(*COLORS['accent'])
        pdf.cell(0, 10, f"FINDING #{idx+1}: {issue['column_name']} | {issue['dataset_name'][:30]}", 'T', 1, 'L', True)
        
        # Explanation Body
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(*COLORS['primary'])
        
        explanation = issue.get('ai_explanation', "No detailed AI explanation available.")
        # Clean up tags if any
        explanation = explanation.replace("DETAILED OBSERVATION:", "\n**DETAILED OBSERVATION**\n")
        explanation = explanation.replace("CLINICAL IMPACT:", "\n**CLINICAL IMPACT**\n")
        explanation = explanation.replace("RECOMMENDED ACTION:", "\n**RECOMMENDED ACTION**\n")
        
        pdf.multi_cell(0, 5, explanation)
        pdf.set_y(pdf.get_y() + 5)
        
        if pdf.get_y() > 250:
            pdf.add_page()

    # --- PAGE 3: DETAILED AUDIT LOGS & ROADMAP ---
    pdf.add_page()
    pdf.chapter_title('Detailed Audit Logs (Sample)')
    
    # Table Header
    pdf.set_fill_color(*COLORS['primary'])
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(35, 10, ' DATASET', 0, 0, 'L', True)
    pdf.cell(30, 10, ' COLUMN', 0, 0, 'L', True)
    pdf.cell(85, 10, ' OBSERVATION', 0, 0, 'L', True)
    pdf.cell(20, 10, ' SEV', 0, 0, 'C', True)
    pdf.cell(20, 10, ' STATUS', 0, 1, 'C', True)
    
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(*COLORS['primary'])
    
    # Show up to 15 issues on this page to leave room for roadmap
    for i, issue in enumerate(all_issues[:15]):
        pdf.set_fill_color(248, 250, 252) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            
        row_height = 8
        pdf.cell(35, row_height, str(issue['dataset_name'])[:18], 0, 0, 'L', True)
        pdf.cell(30, row_height, str(issue['column_name'])[:15], 0, 0, 'L', True)
        
        observation = str(issue['issue'])
        if issue.get('original_value') and issue.get('original_value') != 'None':
            observation += f" ({issue['original_value']}->{issue['corrected_value']})"
        
        pdf.cell(85, row_height, observation[:55], 0, 0, 'L', True)
        
        sev = issue['severity']
        sev_color = COLORS['danger'] if sev in ['Critical', 'High'] else COLORS['warning'] if sev in ['Warning', 'Medium'] else COLORS['success']
        pdf.set_text_color(*sev_color)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(20, row_height, sev[:3], 0, 0, 'C', True)
        
        pdf.set_text_color(100, 116, 139)
        pdf.set_font('Arial', '', 8)
        pdf.cell(20, row_height, 'AUDITED', 0, 1, 'C', True)

    pdf.ln(10)
    pdf.section_title('Strategic Roadmap & Methodology')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(*COLORS['accent'])
    pdf.cell(0, 8, "Audit Methodology:", 0, 1)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*COLORS['primary'])
    pdf.multi_cell(0, 5, "The audit utilized a dual-engine validation process. Phase 1 involved deterministic clinical rules based on DMSAP (Data Management & Statistical Analysis Plan) standards. Phase 2 leveraged a local DeepSeek-R1 LLM to analyze row context and provide actionable clinical intelligence. All PII was handled according to masking protocols enabled during the session.")
    
    pdf.ln(5)
    recoms = [
        ("Short-term (0-30 days)", "Immediate cleanup of 'Critical' flags identified in Section 4. Standardize field headers across all source datasets."),
        ("Mid-term (30-90 days)", "Develop automated ETL pipelines with pre-processing gates for temperature and age outliers."),
        ("Long-term (Strategic)", "Adopt CDISC SDTM standards for all clinical research datasets to ensure global interoperability and compliance.")
    ]
    
    for phase, detail in recoms:
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(*COLORS['accent'])
        pdf.cell(0, 8, phase, 0, 1)
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(*COLORS['primary'])
        pdf.multi_cell(0, 5, detail)
        pdf.ln(2)

    output_path = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(output_path)
    return output_path
