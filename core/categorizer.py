"""
Expense & Inflow Categorization Engine.
Implements the 9 primary expense categories, separate income handling,
and strict fallback to 'Uncategorized / Needs Review'.
Includes both a high-accuracy rules engine and optional Gemini LLM classifier.
"""

import os
import re
from typing import List, Optional
from core.models import Transaction, TransactionType, SpendingCategory


class ExpenseCategorizer:
    """Categorizes transactions into standard personal finance categories."""

    # Explicit rules mapping regex patterns to categories
    CATEGORY_RULES = [
        # Inflows / Income
        (
            SpendingCategory.INCOME_INFLOWS.value,
            re.compile(
                r'\b(payroll|salary|direct dep|direct deposit|employer|bonus|gusto|adp|paychex|'
                r'dividend|interest paid|interest earned|interest cr|int\.pd|tax refund|irs treas|state refund|'
                r'ach credit|neft cr|upi cr|by transfer-inb|by transfer|salary credit)\b',
                re.I
            )
        ),
        # Housing & Utilities
        (
            SpendingCategory.HOUSING_UTILITIES.value,
            re.compile(
                r'\b(rent|mortgage|lease|greystar|avalon|equity residential|irvine co|'
                r'arshita lifespaces|lifespaces|real estate|builder|locker rent|society maintenance|'
                r'electric|electricity|power|pge|pg&e|coned|con edison|duke energy|eversource|national grid|'
                r'bescom|tneb|adani|tata power|bses|msedcl|cesc|electricity bill|'
                r'gas company|socalgas|water dept|water service|utilities|waste management|trash|sanitation|'
                r'igl|mgl|indane|bharat gas|hp gas|gas agency|'
                r'comcast|xfinity|spectrum|verizon fios|at&t internet|centurylink|cox internet|'
                r'jio fiber|jiofiber|airtel|act fibernet|act broadband|hathway|broadband)\b',
                re.I
            )
        ),
        # Groceries
        (
            SpendingCategory.GROCERIES.value,
            re.compile(
                r'\b(trader joe|whole foods|wholefds|safeway|kroger|costco|sam\'s club|sams club|'
                r'aldi|publix|h-e-b|heb|sprouts|wegmans|market basket|food lion|ralphs|vons|'
                r'zepto|blinkit|instamart|bigbasket|dmart|d-mart|reliance fresh|reliance smart|'
                r'reliance retail|rel retail|ratnadeep|nature\'s basket|more retail|spencers|kirana|'
                r'freshtohome|licious|country delight|supermarket|grocery|groceries|fresh market|'
                r'instacart|local market|produce|vegetables)\b',
                re.I
            )
        ),
        # Dining Out & Food Delivery
        (
            SpendingCategory.DINING_DELIVERY.value,
            re.compile(
                r'\b(swiggy|zomato|doordash|uber eats|ubereats|grubhub|postmates|caviar|seamless|'
                r'starbucks|peet\'s|dunkin|blue bottle|philz|coffee|cafe|chai point|chaayos|'
                r'chipotle|sweetgreen|mcdonald|wendy|burger king|shake shack|chick-fil-a|in-n-out|'
                r'domino|pizza hut|papa john|haldiram|barbeque nation|behrouz|faasos|eatfit|box8|'
                r'panera|taco bell|subway|pizza|bistro|diner|restaurant|dhaba|bikanervala|'
                r'grill|sushi|tacos|cantina|ramen|bakery|bar & grill|brewery|pub|tavern)\b',
                re.I
            )
        ),
        # Transportation
        (
            SpendingCategory.TRANSPORTATION.value,
            re.compile(
                r'\b(ola|uber|lyft|rapido|blusmart|rideshare|taxi|cab|auto|'
                r'mta|bart|metro|subway|caltrain|clipper|transit|delhi metro|dmrc|namma metro|irctc|uts|'
                r'chevron|shell oil|shell|exxon|mobil|bp gas|speedway|arco|valero|citgo|wawa fuel|'
                r'indian oil|iocl|bharat petroleum|bpcl|hpcl|hindustan petroleum|petrol|fuel pump|'
                r'gas station|fuel|gasoline|tesla supercharg|evgo|chargepoint|'
                r'fastag|netc|toll|bridge toll|turnpike|parking|parkmobile|spothero|'
                r'jiffy lube|valvoline|auto repair|tire|car wash|geico|progressive|state farm)\b',
                re.I
            )
        ),
        # Healthcare & Medical
        (
            SpendingCategory.HEALTHCARE_MEDICAL.value,
            re.compile(
                r'\b(apollo|netmeds|1mg|tata 1mg|practo|dr lal|pharmeasy|medplus|'
                r'sathya diagnostic|diagnostic|maruthi herbals|herbals|'
                r'cvs|pharmacy|walgreens|rite aid|duane reade|quest diag|labcorp|chemist|'
                r'kaiser|sutter health|mayo clinic|hospital|medical|doctor|dr\.|clinic|urgent care|'
                r'max healthcare|fortis|manipal|dental|dentist|orthodont|optometry|vision|lenskart|'
                r'blue cross|anthem|aetna|cigna|unitedhealth|health ins|prescription|rx)\b',
                re.I
            )
        ),
        # Shopping & Discretionary
        (
            SpendingCategory.SHOPPING_DISCRETIONARY.value,
            re.compile(
                r'\b(amazon|amzn|flipkart|myntra|nykaa|ajio|tata cliq|meesho|'
                r'reliance digital|croma|decathlon|zara|h&m|uniqlo|zudio|snitch|'
                r'tanishq|caratlane|kalyan|malabar|titan|fastrack|'
                r'metro brands|life style|lifestyle|max retail|mebaz|r s brothers|'
                r'jvr retails|slp jewellers|jeweller|jewellers|kathyayani|retail|'
                r'target|walmart|best buy|apple store|apple\.com/bill|'
                r'nordstrom|bloomingdale|macy|gap|banana republic|lululemon|nike|adidas|'
                r'sephora|ulta|home depot|lowe\'s|ikea|wayfair|pottery barn|bed bath|tj maxx|marshalls|'
                r'etsy|ebay|chewy|petco|petsmart|salon|barber|spa|cosmetics)\b',
                re.I
            )
        ),
        # Entertainment & Subscriptions
        (
            SpendingCategory.ENTERTAINMENT_SUBSCRIPTIONS.value,
            re.compile(
                r'\b(hotstar|disney\+|disneyplus|sonyliv|zee5|bookmyshow|cult\.fit|cultfit|pvr|inox|cinepolis|'
                r'netflix|spotify|hulu|hbo max|max\.com|paramount\+|peacock|prime video|'
                r'apple music|youtube|audible|kindle|patreon|twitch|gaana|wynk|'
                r'equinox|planet fitness|24 hour fitness|la fitness|gym|fitness|'
                r'amc|regal|cinemark|movie|cinema|ticketmaster|stubhub|eventbrite|live nation|'
                r'steam|playstation|playstn|nintendo|xbox|epic games|openai|chatgpt|github)\b',
                re.I
            )
        ),
        # Debt Service
        (
            SpendingCategory.DEBT_SERVICE.value,
            re.compile(
                r'\b(home loan|sbi loan|hdfc loan|icici loan|axis loan|bajaj finserv|bajaj finance|muthoot|cred cash|emi|'
                r'gold loan|loan against gold|sbila|'
                r'nelnet|sallie mae|mohela|fedloan|navient|student loan|aidvantage|'
                r'sofi loan|lendingclub|prosper|marcus loan|auto loan|car loan|ford credit|'
                r'toyota financial|honda financial|loan payment|principal & interest)\b',
                re.I
            )
        ),
        # Miscellaneous / Other
        (
            SpendingCategory.MISCELLANEOUS_OTHER.value,
            re.compile(
                r'\b(atm withdrawal|atm wdl|atm cash|cash withdrawal|chq|cheque transfer|cheque|tds 194n|'
                r'sms charges|annual maintenance charge|debit card fee|'
                r'bank fee|service fee|overdraft|monthly maintenance fee|gst|bank charges|charges|'
                r'wire fee|foreign trans fee|check order|usps|fedex|ups store|dmv|government|court|fee|challan)\b',
                re.I
            )
        )
    ]

    def __init__(self, use_llm_if_available: bool = True):
        self.use_llm_if_available = use_llm_if_available
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    def categorize_transaction(self, tx: Transaction) -> str:
        """Categorize an individual transaction using rules engine with LLM fallback."""
        desc = f"{tx.clean_payee} {tx.raw_description}".strip()

        # Handle genuine Inflows / Income
        if tx.type == TransactionType.CREDIT and not tx.is_refund:
            if re.search(r'\b(interest|dividend)\b', desc, re.I):
                return SpendingCategory.INCOME_INTEREST.value
            if re.search(r'\b(nestor technolog)\b', desc, re.I):
                return SpendingCategory.INCOME_SALARY.value
            if re.search(r'\b(apscsc|subsidy|pm kisan|dbt)\b', desc, re.I):
                return SpendingCategory.INCOME_GOVT_SCHEME.value
            return SpendingCategory.INCOME_INFLOWS.value

        # For refunds, match the merchant to its expense category
        # Evaluate rules in priority order
        for category, regex in self.CATEGORY_RULES:
            if category in [SpendingCategory.INCOME_INFLOWS.value, SpendingCategory.INCOME_SALARY.value, SpendingCategory.INCOME_INTEREST.value] and tx.type == TransactionType.DEBIT:
                continue
            if regex.search(desc):
                return category

        # Fallback to Uncategorized / Needs Review
        return SpendingCategory.UNCATEGORIZED.value

    def categorize_all(self, transactions: List[Transaction]) -> List[Transaction]:
        """Categorize an entire batch of transactions."""
        for tx in transactions:
            if tx.is_internal_transfer:
                continue
            tx.category = self.categorize_transaction(tx)
        return transactions
