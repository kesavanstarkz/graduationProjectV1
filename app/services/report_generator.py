import os
import pandas as pd
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
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # Draw top accent bar
        self.set_fill_color(*COLORS['accent'])
        self.rect(0, 0, 210, 3, 'F')
        
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*COLORS['primary'])
        self.cell(0, 10, 'CLINICAL DATA QUALITY INTELLIGENCE REPORT', 0, 0, 'L')
        
        self.set_font('Helvetica', '', 8)
        self.set_text_color(100, 116, 139) # Slate 500
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%d %b %Y, %H:%M")}', 0, 1, 'R')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184) # Slate 400
        self.cell(0, 10, f'Confidential Clinical Data - Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*COLORS['accent'])
        self.cell(0, 15, title, 0, 1, 'L')
        self.ln(2)

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 12)
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
    colors = [COLORS['danger'] if s == 'High' else COLORS['warning'] if s == 'Medium' else COLORS['success'] for s in severity_counts.index]
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
            "high": len([i for i in issue_list if i["severity"] == "High"])
        })

    # 1. Dashboard Cover
    pdf.chapter_title('Executive Quality Summary')
    
    # Summary Box
    pdf.set_fill_color(*COLORS['bg_light'])
    pdf.rect(10, pdf.get_y(), 190, 40, 'F')
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_x(15)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(*COLORS['accent'])
    pdf.cell(60, 15, str(len(all_issues)), 0, 0, 'C')
    pdf.cell(60, 15, str(len(datasets_info)), 0, 0, 'C')
    pdf.cell(60, 15, str(len([i for i in all_issues if i['severity'] == 'High'])), 0, 1, 'C')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 116, 139)
    pdf.set_x(15)
    pdf.cell(60, 5, 'Total Observations', 0, 0, 'C')
    pdf.cell(60, 5, 'Datasets Audited', 0, 0, 'C')
    pdf.cell(60, 5, 'High Severity Flags', 0, 1, 'C')
    pdf.ln(20)

    # 2. Analytics Visuals
    severity_img, type_img = generate_charts(all_issues)
    if severity_img and type_img:
        pdf.set_y(pdf.get_y())
        pdf.image(severity_img, x=10, y=pdf.get_y(), w=90)
        pdf.image(type_img, x=110, y=pdf.get_y(), w=90)
        pdf.set_y(pdf.get_y() + 70)
        # Cleanup charts
        os.remove(severity_img)
        os.remove(type_img)

    # 3. Clinical Impact Analysis
    pdf.ln(10)
    pdf.chapter_title('Clinical Risk Analysis')
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*COLORS['primary'])
    risk_summary = (
        "Based on the AI-driven validation, the primary risks identified relate to "
        f"{'high-severity clinical anomalies' if any(i['severity'] == 'High' for i in all_issues) else 'minor data inconsistencies'}. "
        "These observations often stem from legacy data entry rituals or missing interoperability checks. "
        "Immediate attention to 'High' severity flags is recommended to ensure patient safety and diagnostic accuracy."
    )
    pdf.multi_cell(0, 7, risk_summary)
    pdf.ln(10)

    # 4. Detailed Data Audit Table
    pdf.add_page()
    pdf.chapter_title('Detailed Audit Logs')
    
    # Table Header
    pdf.set_fill_color(*COLORS['primary'])
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(40, 10, ' DATASET', 0, 0, 'L', True)
    pdf.cell(30, 10, ' COLUMN', 0, 0, 'L', True)
    pdf.cell(80, 10, ' OBSERVATION', 0, 0, 'L', True)
    pdf.cell(20, 10, ' SEVERITY', 0, 0, 'C', True)
    pdf.cell(20, 10, ' STATUS', 0, 1, 'C', True)
    
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(*COLORS['primary'])
    
    for i, issue in enumerate(all_issues):
        # Zebra striping
        if i % 2 == 0:
            pdf.set_fill_color(248, 250, 252)
        else:
            pdf.set_fill_color(255, 255, 255)
            
        row_height = 8
        # Calculate height if multi-line needed (simplified here)
        pdf.cell(40, row_height, str(issue['dataset_name'])[:20], 0, 0, 'L', True)
        pdf.cell(30, row_height, str(issue['column_name']), 0, 0, 'L', True)
        pdf.cell(80, row_height, str(issue['issue'])[:50], 0, 0, 'L', True)
        
        # Severity Mini-badge
        sev = issue['severity']
        sev_color = COLORS['danger'] if sev == 'High' else COLORS['warning'] if sev == 'Medium' else COLORS['success']
        pdf.set_text_color(*sev_color)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(20, row_height, sev, 0, 0, 'C', True)
        
        pdf.set_text_color(100, 116, 139)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(20, row_height, 'AUDITED', 0, 1, 'C', True)
        
        if pdf.get_y() > 260:
            pdf.add_page()
            # Redraw header if wanted, but FPDF handles page breaks

    # 5. Strategic Recommendations
    pdf.add_page()
    pdf.chapter_title('Strategic Quality Roadmap')
    
    recoms = [
        ("Short-term", "Purge duplicate records and backfill missing critical identifiers identified in Section 4."),
        ("Mid-term", "Implement real-time range validation (e.g., using FHIR standards) at the source of truth."),
        ("Long-term", "Train the clinical staff on the impact of data quality on downstream AI research outcomes.")
    ]
    
    for phase, detail in recoms:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(*COLORS['accent'])
        pdf.cell(0, 10, phase, 0, 1)
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(*COLORS['primary'])
        pdf.multi_cell(0, 7, detail)
        pdf.ln(5)

    output_path = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(output_path)
    return output_path
