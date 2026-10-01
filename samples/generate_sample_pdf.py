"""
Generates a realistic sample PDF bank statement for testing PDF extraction.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_sample_pdf(output_path: str = "samples/bank_of_america_checking_oct2024.pdf"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "BANK OF AMERICA, N.A.")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 65, "P.O. Box 15284, Wilmington, DE 19850")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 95, "Account Statement - Total Checking")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 110, "Statement Period: October 01, 2024 through October 31, 2024")
    c.drawString(50, height - 125, "Account Number Ending in: 7724")
    c.drawString(50, height - 140, "Currency: USD")

    # Table Header
    y = height - 180
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Date")
    c.drawString(130, y, "Description")
    c.drawString(450, y, "Amount ($)")
    c.line(50, y - 5, 550, y - 5)

    transactions = [
        ("10/01", "DIRECT DEPOSIT EMPLOYER PAYROLL", "3,100.00"),
        ("10/02", "RENT PAYMENT GREYSTAR APTS", "-1,950.00"),
        ("10/03", "SAFEWAY SUPERMARKET #1084", "-84.20"),
        ("10/05", "PACIFIC GAS & ELECTRIC UTILITY", "-135.40"),
        ("10/07", "UBER TRIP HELP.UBER.COM", "-22.50"),
        ("10/10", "NETFLIX.COM STREAMING", "-15.49"),
        ("10/12", "CHIPOTLE ONLINE ORDER", "-18.75"),
        ("10/15", "DIRECT DEPOSIT EMPLOYER PAYROLL", "3,100.00"),
        ("10/16", "TRADER JOES GROCERY STORE", "-112.30"),
        ("10/18", "COMCAST INTERNET SERVICE", "-79.99"),
        ("10/20", "AUTOMATIC PAYMENT - THANK YOU", "-420.00"),  # Internal card payoff
        ("10/22", "CVS PHARMACY HEALTHCARE", "-28.40"),
        ("10/25", "SHELL OIL GAS STATION", "-45.00"),
        ("10/28", "SPOTIFY USA RECURRING", "-11.99"),
    ]

    c.setFont("Helvetica", 9)
    y -= 25
    for dt, desc, amt in transactions:
        c.drawString(50, y, dt)
        c.drawString(130, y, desc)
        c.drawString(450, y, amt)
        y -= 20

    c.save()
    print(f"Generated sample statement PDF at: {output_path}")


if __name__ == "__main__":
    generate_sample_pdf()
