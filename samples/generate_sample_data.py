"""
Sample statement generator.
Creates realistic test data:
1. Checking Account CSV (Chase)
2. Credit Card CSV (American Express)
"""

import os
import pandas as pd

def generate_samples(output_dir: str = "samples"):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Chase Checking Statement (October 2024)
    # Checking convention: Negative amount = Outflow/Debit, Positive amount = Inflow/Credit
    checking_data = [
        {"Date": "10/01/2024", "Description": "DIRECT DEPOSIT ACME CORP PAYROLL", "Amount": 3250.00},
        {"Date": "10/01/2024", "Description": "RENT PAYMENT GREYSTAR APTS", "Amount": -2100.00},
        {"Date": "10/02/2024", "Description": "TRADER JOE'S #142 SAN FRANCISCO CA", "Amount": -118.40},
        {"Date": "10/03/2024", "Description": "STARBUCKS COFFEE #1829", "Amount": -6.75},
        {"Date": "10/04/2024", "Description": "PG&E ELECTRIC & GAS UTILITY", "Amount": -142.50},
        {"Date": "10/05/2024", "Description": "COMCAST XFINITY INTERNET", "Amount": -85.00},
        {"Date": "10/06/2024", "Description": "SHELL OIL 574421 SAN JOSE CA", "Amount": -52.30},
        {"Date": "10/07/2024", "Description": "DOORDASH DELIVERY", "Amount": -44.80},
        {"Date": "10/09/2024", "Description": "CVS PHARMACY #9382 PRESCRIPTION", "Amount": -34.20},
        {"Date": "10/10/2024", "Description": "NETFLIX.COM MONTHLY SUBSCRIPTION", "Amount": -15.49},
        {"Date": "10/11/2024", "Description": "SPOTIFY USA RECURRING", "Amount": -11.99},
        {"Date": "10/12/2024", "Description": "PLANET FITNESS MONTHLY DUES", "Amount": -24.99},
        {"Date": "10/13/2024", "Description": "ATM CASH WITHDRAWAL CHASE BRANCH", "Amount": -80.00},
        {"Date": "10/15/2024", "Description": "DIRECT DEPOSIT ACME CORP PAYROLL", "Amount": 3250.00},
        {"Date": "10/16/2024", "Description": "WHOLE FOODS MARKET #104", "Amount": -92.15},
        {"Date": "10/17/2024", "Description": "CHIPOTLE ONLINE ORDER", "Amount": -19.45},
        {"Date": "10/18/2024", "Description": "CALTRAIN TICKET SAN FRANCISCO", "Amount": -16.50},
        {"Date": "10/19/2024", "Description": "SWEETGREEN SALAD", "Amount": -21.30},
        {"Date": "10/20/2024", "Description": "AUTOMATIC PAYMENT - CHASE CARD ENDING 8821", "Amount": -550.00}, # Internal transfer to exclude!
        {"Date": "10/22/2024", "Description": "NELNET STUDENT LOAN PAYMENT", "Amount": -220.00},
        {"Date": "10/24/2024", "Description": "SAFEWAY SUPERMARKET #084", "Amount": -78.60},
        {"Date": "10/26/2024", "Description": "UBER TRIP RIDEPASS", "Amount": -28.50},
        {"Date": "10/28/2024", "Description": "MONTHLY MAINTENANCE BANK FEE", "Amount": -12.00},
    ]
    df_checking = pd.DataFrame(checking_data)
    checking_csv = os.path.join(output_dir, "chase_checking_oct2024_act4812.csv")
    df_checking.to_csv(checking_csv, index=False)

    # 2. Amex Credit Card Statement (October 2024)
    # Credit Card convention: Positive amount = Charge/Spend (Debit), Negative = Payment/Refund (Credit)
    amex_data = [
        {"Date": "10/02/2024", "Description": "AMAZON.COM*2K48J DIGITAL", "Amount": 84.50},
        {"Date": "10/04/2024", "Description": "TARGET T-0948 STORE", "Amount": 68.20},
        {"Date": "10/08/2024", "Description": "BEST BUY STORE #1084 ELECTRONICS", "Amount": 420.00}, # Anomaly spike!
        {"Date": "10/11/2024", "Description": "AMAZON.COM REFUND / RETURN", "Amount": -34.50}, # Refund to offset!
        {"Date": "10/14/2024", "Description": "SHAKE SHACK #0429", "Amount": 31.40},
        {"Date": "10/18/2024", "Description": "LOCAL BISTRO & BAR SAN FRANCISCO", "Amount": 95.00},
        {"Date": "10/20/2024", "Description": "ONLINE PAYMENT - THANK YOU", "Amount": -550.00}, # Internal payment received!
        {"Date": "10/23/2024", "Description": "APPLE.COM/BILL ICLOUD STORAGE", "Amount": 9.99},
        {"Date": "10/25/2024", "Description": "LYFT RIDE FARE", "Amount": 34.10},
        {"Date": "10/27/2024", "Description": "CHEVRON GAS STATION", "Amount": 46.50},
    ]
    df_amex = pd.DataFrame(amex_data)
    amex_csv = os.path.join(output_dir, "amex_credit_card_oct2024_act8821.csv")
    df_amex.to_csv(amex_csv, index=False)

    print(f"Generated sample statements in {output_dir}:")
    print(f" - {checking_csv} ({len(checking_data)} rows)")
    print(f" - {amex_csv} ({len(amex_data)} rows)")

if __name__ == "__main__":
    generate_samples()
