"""
Script to generate a sample invoice PDF for OCR testing
Run with: python generate_sample_invoice.py
"""
from datetime import datetime

def generate_sample_invoice():
    """Generate a sample invoice PDF using reportlab"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError:
        print("⚠️  reportlab not installed. Using alternative method...")
        generate_simple_invoice_image()
        return

    # Create PDF
    pdf_path = "sample_invoice.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Header
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a5f3e'),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    story.append(Paragraph("FRESH PRODUCE SUPPLIERS", title_style))
    story.append(Paragraph("Invoice #INV-2026-0420", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Invoice details
    header_data = [
        ['Date:', '20-Apr-2026', 'Supplier:', 'Fresh Produce Suppliers'],
        ['Invoice ID:', 'INV-2026-0420', 'Terms:', 'Net 7 days'],
    ]
    header_table = Table(header_data, colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Items table
    items_data = [
        ['PRODUCT', 'QTY', 'UNIT', 'PRICE', 'TOTAL'],
        ['Tomatoes', '50', 'kg', '28', '1400'],
        ['Full Cream Milk', '100', 'L', '55', '5500'],
        ['Sourdough Bread', '40', 'loaves', '90', '3600'],
        ['Greek Yogurt', '60', 'cups', '80', '4800'],
        ['Bananas', '30', 'dozen', '38', '1140'],
        ['Spinach', '25', 'bunches', '22', '550'],
        ['Potatoes', '80', 'kg', '18', '1440'],
        ['Mango Alphonso', '45', 'kg', '120', '5400'],
        ['Carrots', '35', 'kg', '20', '700'],
        ['Onions', '60', 'kg', '22', '1320'],
    ]
    
    items_table = Table(items_data, colWidths=[2.2*inch, 0.8*inch, 1*inch, 1*inch, 0.8*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5f3e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Totals
    totals_data = [
        ['SUBTOTAL:', '26,750'],
        ['TAX (5%):', '1,337'],
        ['TOTAL:', '28,087'],
    ]
    totals_table = Table(totals_data, colWidths=[5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 12),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#1a5f3e')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(totals_table)
    
    # Build PDF
    doc.build(story)
    print(f"✅ Sample invoice created: {pdf_path}")
    print("📄 You can now upload this file to the OCR page for testing!")


def generate_simple_invoice_image():
    """Fallback: Generate a simple image using PIL"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("❌ Neither reportlab nor PIL installed.")
        print("📋 Please install: pip install reportlab pillow")
        return
    
    # Create image
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    y = 40
    line_height = 30
    
    # Title
    draw.text((150, y), "FRESH PRODUCE SUPPLIERS", fill='black')
    y += line_height * 1.5
    draw.text((200, y), "Invoice #INV-2026-0420", fill='black')
    y += line_height * 2
    
    # Headers
    draw.text((50, y), "PRODUCT", fill='black')
    draw.text((350, y), "QTY", fill='black')
    draw.text((450, y), "UNIT", fill='black')
    draw.text((550, y), "PRICE", fill='black')
    draw.text((650, y), "TOTAL", fill='black')
    y += line_height
    
    # Items
    items = [
        ("Tomatoes", "50", "kg", "28", "1400"),
        ("Full Cream Milk", "100", "L", "55", "5500"),
        ("Sourdough Bread", "40", "loaves", "90", "3600"),
        ("Greek Yogurt", "60", "cups", "80", "4800"),
        ("Bananas", "30", "dozen", "38", "1140"),
        ("Spinach", "25", "bunches", "22", "550"),
        ("Potatoes", "80", "kg", "18", "1440"),
        ("Mango Alphonso", "45", "kg", "120", "5400"),
        ("Carrots", "35", "kg", "20", "700"),
        ("Onions", "60", "kg", "22", "1320"),
    ]
    
    for name, qty, unit, price, total in items:
        draw.text((50, y), name, fill='black')
        draw.text((360, y), qty, fill='black')
        draw.text((460, y), unit, fill='black')
        draw.text((560, y), price, fill='black')
        draw.text((660, y), total, fill='black')
        y += line_height
    
    y += line_height
    draw.text((400, y), "SUBTOTAL: 26,750", fill='black')
    y += line_height
    draw.text((400, y), "TAX (5%): 1,337", fill='black')
    y += line_height
    draw.text((400, y), "TOTAL: 28,087", fill='black')
    
    # Save image
    img.save("sample_invoice.png")
    print("✅ Sample invoice image created: sample_invoice.png")
    print("📷 You can now upload this image to the OCR page for testing!")


if __name__ == "__main__":
    print("🔧 Generating sample invoice...")
    generate_sample_invoice()
