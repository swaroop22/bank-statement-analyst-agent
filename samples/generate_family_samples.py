"""
Generate realistic sample statements for Dad and Wife in India (INR).
- Dad: Senior Pension, Fixed Deposits interest, healthcare, domestic living, home repair cheques.
- Wife: Corporate Salary (Tech), Quick commerce, shopping, dining, investments, and home furnishing.
"""

import os
import pandas as pd
from datetime import datetime, timedelta

def generate_family_statements(output_dir: str = "samples"):
    os.makedirs(output_dir, exist_ok=True)

    # -------------------------------------------------------------
    # 1. DAD'S STATEMENTS (HDFC Senior Checking & SBI Pension Account)
    # -------------------------------------------------------------
    dad_txs = []
    
    # 12 Months of 2023
    for month in range(1, 13):
        m_str = f"2023-{month:02d}"
        
        # Monthly Central Pension Inflow
        dad_txs.append({
            "Date": f"{m_str}-01",
            "Description": "NEFT*SBIN0001234*CPENG CENTRAL PENSION DISBURSAL",
            "Amount": 68500.00,
            "Type": "CREDIT"
        })
        
        # Post Office Monthly Income Scheme
        dad_txs.append({
            "Date": f"{m_str}-07",
            "Description": "NEFT*DOP00021*POST OFFICE MONTHLY INCOME SCHEME DIVIDEND",
            "Amount": 7500.00,
            "Type": "CREDIT"
        })
        
        # Quarterly Senior Citizen Fixed Deposit Interest
        if month in [3, 6, 9, 12]:
            dad_txs.append({
                "Date": f"{m_str}-25",
                "Description": "INTEREST CREDIT SBI SENIOR CITIZEN FD A/C 9812",
                "Amount": 22400.00,
                "Type": "CREDIT"
            })
            dad_txs.append({
                "Date": f"{m_str}-28",
                "Description": "TDS 194A DEDUCTION INCOME TAX",
                "Amount": -2240.00,
                "Type": "DEBIT"
            })

        # Bi-annual Senior Citizen Savings Scheme (SCSS)
        if month in [4, 10]:
            dad_txs.append({
                "Date": f"{m_str}-15",
                "Description": "NEFT*SBI0091*SENIOR CITIZEN SAVINGS SCHEME QUARTERLY INTEREST",
                "Amount": 19800.00,
                "Type": "CREDIT"
            })

        # Monthly Regular Living Expenses (Debits)
        dad_txs.append({
            "Date": f"{m_str}-03",
            "Description": "UPI/APOLLO PHARMACY/PRESCRIPTION SENIOR CARE",
            "Amount": -4850.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-05",
            "Description": "TSSPDCL ELECTRICITY BOARD POWER BILL",
            "Amount": -2350.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-06",
            "Description": "INDANE LPG GAS REFILL BOOKING",
            "Amount": -950.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-10",
            "Description": "HERITAGE FRESH GROCERY STORE",
            "Amount": -6800.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-14",
            "Description": "LOCAL VEGETABLE MARKET & PROVISIONS",
            "Amount": -3400.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-18",
            "Description": "MEDPLUS PHARMACY MEDICINES",
            "Amount": -2100.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-20",
            "Description": "D-MART SUPERMARKET MONTHLY SUPPLIES",
            "Amount": -7200.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-22",
            "Description": "INDIAN OIL PETROL PUMP",
            "Amount": -1800.00,
            "Type": "DEBIT"
        })
        dad_txs.append({
            "Date": f"{m_str}-24",
            "Description": "BSNL FIBER INTERNET & LANDLINE BILL",
            "Amount": -899.00,
            "Type": "DEBIT"
        })

    # Non-monthly items & Spikes for Dad
    # Agricultural land lease income
    dad_txs.append({
        "Date": "2023-05-18",
        "Description": "UPI/CHANDRA RAO/AGRICULTURAL LEASE PROCEEDS",
        "Amount": 120000.00,
        "Type": "CREDIT"
    })
    # Medical Health Diagnostics
    dad_txs.append({
        "Date": "2023-04-12",
        "Description": "VIJAYA DIAGNOSTIC LAB FULL BODY SENIOR MASTER HEALTH CHECKUP",
        "Amount": -8500.00,
        "Type": "DEBIT"
    })
    dad_txs.append({
        "Date": "2023-10-18",
        "Description": "DR LAL PATHLABS CARDIAC PROFILE TEST",
        "Amount": -4200.00,
        "Type": "DEBIT"
    })
    # Star Health Insurance Senior Citizen Annual Premium
    dad_txs.append({
        "Date": "2023-07-15",
        "Description": "STAR HEALTH INSURANCE ANNUAL SENIOR CITIZEN RED CARPET PREMIUM",
        "Amount": -38500.00,
        "Type": "DEBIT"
    })
    # IRCTC Trains to visit family
    dad_txs.append({
        "Date": "2023-08-10",
        "Description": "IRCTC TRAIN TICKET HYDERABAD TO CHENNAI 2 TIER AC",
        "Amount": -3650.00,
        "Type": "DEBIT"
    })
    # Charitable temple donation
    dad_txs.append({
        "Date": "2023-09-02",
        "Description": "TIRUMALA TIRUPATI DEVASTHANAM ANNA PRASADAM TRUST DONATION",
        "Amount": -15000.00,
        "Type": "DEBIT"
    })

    # Internal Transfer: Sweep to Fixed Deposit
    dad_txs.append({
        "Date": "2023-06-05",
        "Description": "TRANSFER TO SBI SENIOR CITIZEN TERM DEPOSIT A/C 9812",
        "Amount": -200000.00,
        "Type": "DEBIT"
    })

    # Unresolved Items (Needs Review Queue for Dad)
    dad_txs.append({
        "Date": "2023-03-20",
        "Description": "CHQ 492810 CLEARING TO SRI RAMA CONSTRUCTIONS HOME REPAIRS",
        "Amount": -140000.00,
        "Type": "DEBIT"
    })
    dad_txs.append({
        "Date": "2023-07-28",
        "Description": "CHQ 492811 CLEARING TO RESIDENTIAL COLONY BOREWELL MAINTENANCE",
        "Amount": -35000.00,
        "Type": "DEBIT"
    })
    dad_txs.append({
        "Date": "2023-11-14",
        "Description": "NEFT TO SRINIVAS RAO FAMILY WEDDING GIFT CONTRIBUTION",
        "Amount": -50000.00,
        "Type": "DEBIT"
    })
    dad_txs.append({
        "Date": "2023-08-25",
        "Description": "CHQ 492812 CLEARING UNKNOWN PAYEE",
        "Amount": -25000.00,
        "Type": "DEBIT"
    })
    dad_txs.append({
        "Date": "2023-12-05",
        "Description": "ATM CASH WITHDRAWAL SBI RETIRED COLONY BRANCH",
        "Amount": -20000.00,
        "Type": "DEBIT"
    })
    dad_txs.append({
        "Date": "2023-12-18",
        "Description": "BANK SERVICE CHARGES AND SMS ALERT FEES",
        "Amount": -450.00,
        "Type": "DEBIT"
    })

    dad_df = pd.DataFrame(dad_txs)
    # Format for CsvExcelParser: Date, Description, Amount (Negative = Outflow, Positive = Inflow)
    dad_file = os.path.join(output_dir, "dad_sbi_senior_account_2023.csv")
    dad_df[["Date", "Description", "Amount"]].to_csv(dad_file, index=False)


    # -------------------------------------------------------------
    # 2. WIFE'S STATEMENTS (ICICI Salary & Operational Account)
    # -------------------------------------------------------------
    wife_txs = []
    
    for month in range(1, 13):
        m_str = f"2023-{month:02d}"

        # Monthly Corporate Tech Salary Inflow
        wife_txs.append({
            "Date": f"{m_str}-01",
            "Description": "NEFT*HDFC0001*GOOGLE INDIA PRIVATE LIMITED CORP SALARY",
            "Amount": 185000.00,
            "Type": "CREDIT"
        })

        # Corporate Travel / Expense Reimbursement
        if month in [3, 7, 11]:
            wife_txs.append({
                "Date": f"{m_str}-15",
                "Description": "NEFT*CITI0001*CORPORATE TRAVEL & MEALS EXPENSE REIMBURSEMENT",
                "Amount": 28400.00,
                "Type": "CREDIT"
            })

        # Monthly Living & Discretionary Expenses (Debits)
        wife_txs.append({
            "Date": f"{m_str}-02",
            "Description": "MYGATE APARTMENT GATED COMMUNITY MAINTENANCE",
            "Amount": -18500.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-03",
            "Description": "BLINKIT QUICK COMMERCE GROCERIES",
            "Amount": -4200.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-05",
            "Description": "SWIGGY FOOD DELIVERY & DINEIN",
            "Amount": -3800.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-07",
            "Description": "ZEPTO 10 MINUTE GROCERY ORDER",
            "Amount": -3100.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-08",
            "Description": "BESCOM ELECTRICITY BANGALORE UTILITY",
            "Amount": -3450.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-10",
            "Description": "ZOMATO ONLINE RESTAURANT ORDER",
            "Amount": -2450.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-12",
            "Description": "UBER INDIA COMMUTE RIDES",
            "Amount": -4600.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-14",
            "Description": "AMAZON.IN ONLINE SHOPPING ELECTRONICS & HOME",
            "Amount": -8400.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-16",
            "Description": "MYNTRA FASHION APPAREL SHOPPING",
            "Amount": -6800.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-18",
            "Description": "NYKAA COSMETICS & BEAUTY STORE",
            "Amount": -4900.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-20",
            "Description": "STARBUCKS COFFEE INDIRANAGAR",
            "Amount": -1450.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-22",
            "Description": "ACT FIBERNET HIGH SPEED BROADBAND INTERNET",
            "Amount": -1199.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-24",
            "Description": "NETFLIX & SPOTIFY STREAMING SUBSCRIPTION",
            "Amount": -1249.00,
            "Type": "DEBIT"
        })
        wife_txs.append({
            "Date": f"{m_str}-26",
            "Description": "CULT.FIT GYM & FITNESS LIVE SUBSCRIPTION",
            "Amount": -1850.00,
            "Type": "DEBIT"
        })

        # Monthly Investment: Mutual Fund SIP
        wife_txs.append({
            "Date": f"{m_str}-05",
            "Description": "ACH DEBIT ZERODHA BROKING MUTUAL FUND SIP",
            "Amount": -45000.00,
            "Type": "DEBIT"
        })

        # Internal Transfer: Credit Card Auto-Payment
        wife_txs.append({
            "Date": f"{m_str}-20",
            "Description": "AUTOPAY CLEARING TO ICICI CORAL CREDIT CARD 4019",
            "Amount": -42000.00,
            "Type": "DEBIT"
        })

    # Non-monthly items & Spikes for Wife
    # Annual corporate bonus
    wife_txs.append({
        "Date": "2023-04-10",
        "Description": "NEFT*HDFC0001*GOOGLE INDIA CORP ANNUAL PERFORMANCE BONUS",
        "Amount": 320000.00,
        "Type": "CREDIT"
    })
    # Travel / Vacation Spike
    wife_txs.append({
        "Date": "2023-09-12",
        "Description": "MAKEMYTRIP HOLIDAY FLIGHTS & RESORT BOOKING GOA",
        "Amount": -58400.00,
        "Type": "DEBIT"
    })
    # Luxury / Jewelry
    wife_txs.append({
        "Date": "2023-10-24",
        "Description": "TANISHQ JEWELLERS FESTIVE DIWALI GOLD PURCHASE",
        "Amount": -84000.00,
        "Type": "DEBIT"
    })

    # Unresolved Items (Needs Review Queue for Wife)
    wife_txs.append({
        "Date": "2023-03-15",
        "Description": "NEFT TO URBAN LADDER & WOODENSTREET INTERIOR FURNISHING",
        "Amount": -180000.00,
        "Type": "DEBIT"
    })
    wife_txs.append({
        "Date": "2023-06-22",
        "Description": "UPI/ANANYA SHARMA/MODULAR KITCHEN WOODWORK CONTRACTOR",
        "Amount": -85000.00,
        "Type": "DEBIT"
    })
    wife_txs.append({
        "Date": "2023-08-04",
        "Description": "CHQ 301920 CLEARING TO HOME APPLIANCES LG REFRIGERATOR",
        "Amount": -62000.00,
        "Type": "DEBIT"
    })
    wife_txs.append({
        "Date": "2023-11-20",
        "Description": "IMPS TRANSFER TO SNEHA REDDY WEDDING EVENT",
        "Amount": -40000.00,
        "Type": "DEBIT"
    })
    wife_txs.append({
        "Date": "2023-12-10",
        "Description": "ATM CASH WITHDRAWAL MG ROAD ICICI BRANCH",
        "Amount": -25000.00,
        "Type": "DEBIT"
    })

    wife_df = pd.DataFrame(wife_txs)
    wife_file = os.path.join(output_dir, "wife_icici_salary_account_2023.csv")
    wife_df[["Date", "Description", "Amount"]].to_csv(wife_file, index=False)

    print(f"Generated family statements in {output_dir}:")
    print(f" - Dad: {dad_file} ({len(dad_txs)} transactions)")
    print(f" - Wife: {wife_file} ({len(wife_txs)} transactions)")

if __name__ == "__main__":
    generate_family_statements()
