from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

def generate_pdf_report(response, data):
    # Create document
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    
    # Define emerald theme colors
    emerald_dark = HexColor('#047857')  # Emerald-700
    emerald_light = HexColor('#10B981')  # Emerald-500
    
    # Custom styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        textColor=emerald_dark,
        fontSize=24,
        spaceAfter=30
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        textColor=emerald_dark,
        fontSize=16,
        spaceAfter=12
    )

    # Add title
    elements.append(Paragraph("Clearance Status Report", title_style))
    elements.append(Spacer(1, 20))
    
    # Statistics Table
    stats_data = [
        ['Total Students', str(data['total_students'])],
        ['Cleared Students', str(data['cleared_students'])],
        ['Pending Clearance', str(data['pending_clearance'])]
    ]
    
    stats_table = Table(stats_data, colWidths=[300, 200])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#ECFDF5')),  # Emerald-50
        ('TEXTCOLOR', (0, 0), (-1, -1), emerald_dark),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, emerald_light)
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 30))
    
    # Add detailed breakdown section
    elements.append(Paragraph("Detailed Breakdown", header_style))
    elements.append(Spacer(1, 10))
    
    # Create detailed table
    if data.get('detailed_data'):
        detailed_headers = [['Department', 'Pending', 'Approved', 'Denied']]
        detailed_data = detailed_headers + data['detailed_data']
        
        detailed_table = Table(detailed_data, colWidths=[200, 100, 100, 100])
        detailed_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), emerald_dark),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#F0FDF4')),  # Emerald-50
            ('GRID', (0, 0), (-1, -1), 1, emerald_light)
        ]))
        
        elements.append(detailed_table)
    
    # Build PDF
    doc.build(elements)
