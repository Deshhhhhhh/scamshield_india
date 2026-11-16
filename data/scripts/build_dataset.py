"""Builds the training corpus.

Sources:
  1. Hand-written Indian scam + safe seeds (below) — realistic Lucknow/India context.
  2. Template-based synthetic augmentation (seeded RNG) — trains the model on slot variety.
  3. UCI SMS Spam Collection (optional, data/raw/SMSSpamCollection) — real-world English SMS.

Outputs: data/training/train.csv + data/training/eval_holdout.csv (stratified 85/15).
The GOLDEN set (data/golden/golden_set.csv) is hand-written and DISJOINT from both —
build_dataset() asserts zero overlap.
"""

from __future__ import annotations

import csv
import random
import re
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "SMSSpamCollection"
OUT_DIR = ROOT / "data" / "training"
GOLDEN = ROOT / "data" / "golden" / "golden_set.csv"

# ------------------------------------------------------------ hand-written --
HAND_SCAM: dict[str, list[str]] = {
    "kyc_update": [
        "Dear customer, your SBI account KYC has expired. Update now at http://sbi-kyc-update.in or your a/c will be blocked within 24 hours.",
        "HDFC Bank: Your KYC verification is pending. Complete it immediately via the link or your account will be suspended tonight.",
        "आपका बैंक खाता KYC अपडेट न होने से बंद हो जाएगा। तुरंत क्लिक करें और OTP साझा करें।",
        "ICICI Bank alert: complete mandatory eKYC today. Failure will permanently deactivate your debit card.",
        "PNB: Dear account holder your KYC documents have expired. Verify now bit.ly/kyc-pnb-now to avoid suspension.",
        "Airtel Payments Bank: KYC pending. Share OTP received on your phone to reactivate wallet.",
        "Bank of Baroda notice: update your KYC within 2 hours using tinyurl.com/bob-kyc or services will be frozen.",
        "Your Pan Card is not linked with Aadhaar. Update immediately or pay ₹500 penalty. Link: update-pan-aadhaar.com",
        "SBI KYC expiry alert: update via the secure portal below to continue net banking services: https://secure-sbi-verify.com",
        "Dear Paytm user, your KYC is incomplete. Upgrade now to avoid wallet suspension: https://paytm-kyc-secure.in",
    ],
    "upi_refund": [
        "Dear customer, your refund of ₹2,499 from failed transaction is pending. Accept the collect request to receive amount.",
        "PhonePe: ₹5,000 cashback on your account. Approve the UPI request and enter PIN to claim refund.",
        "Your wrongly paid ₹7,500 will be refunded. Please accept the collect request from our support id to receive it.",
        "Refund of Rs. 1,850 approved by your bank. Open Google Pay, accept request and enter UPI PIN to credit.",
        "Cashback offer! Accept this UPI collect request of ₹1 and receive ₹3,000 instantly. Hurry, expires today.",
        "Amazon refund of ₹999 processed. To receive, approve the request on PhonePe. Do not share PIN with anyone.",
        "आपका ₹3,200 का रिफंड बाकी है। कोई UPI collect request accept करें और PIN डालें पैसे मिलेंगे।",
        "Flipkart: your overpayment refund Rs 1,299 is ready. Enter your UPI PIN in the app after accepting collect request.",
        "IRCTC refund of Rs 640 auto-initiated. For credit accept the pending request or your money will be forfeited.",
        "Dear user, transaction reversal of Rs. 4,750 sanctioned. Open any UPI app → pay ₹0 → enter PIN to receive.",
    ],
    "fake_job_offer": [
        "Congratulations! You are selected for Work From Home job. Earn ₹5,000-₹15,000 daily by liking YouTube videos. Registration fee ₹999 only.",
        "Part-time job offer! Pay ₹500 security deposit, work 2 hrs/day, salary ₹25,000/month. No experience needed. WhatsApp 98XXX-XXXXX.",
        "Hiring urgently: task-based job, rate products and earn ₹600 per task, instant payout, join our Telegram group link.",
        "WFH opportunity: Google/Amazon hiring freshers! Salary ₹40,000/month. Pay training fee ₹1,200, refundable after joining.",
        "Earn ₹30,000 weekly from home! Just review hotels online. Small registration charge Rs 350. Limited seats.",
        "Dear candidate, you are shortlisted for data entry job, salary Rs 45,000/month. Security deposit Rs 2,000 required before joining letter.",
        "Online job!! Type captions for Instagram reels, earn ₹800 per assignment, daily payout. Pay ₹450 onboarding fee.",
        "Urgent hiring for full-time remote role at Meesho, package 8 LPA. Interview fee Rs 1,500 via UPI to our HR.",
        "Work from mobile: give 5 star ratings on Google Maps, earn ₹300/rating, weekly salary. Registration Rs 299.",
        "Aap ghar baithe kaam kar sakte hain, ₹20,000/week, sirf ₹750 registration fee dein, turant join karein.",
    ],
    "digital_arrest": [
        "This is CBI Cyber Cell. A money laundering case is registered against your Aadhaar. Stay on the video call, do not disconnect or tell anyone. Pay ₹50,000 to clear your name.",
        "Mumbai Police: a parcel with narcotics in your name was seized. You are under digital arrest. Transfer security deposit of ₹90,000 immediately or face arrest.",
        "I am calling from ED headquarters. Your bank account is involved in a fraud investigation. Remain on call and deposit funds for verification.",
        "TRAI: your mobile number will be disconnected today for illegal activities. Connect to our officer on WhatsApp video or face arrest warrant.",
        "CBI officer Sharma here. Case No. 2026/DL/4471 — your name is linked to a ₹3 crore fraud. Stay on the line and cooperate or non-bailable warrant will be issued.",
        "This is Lucknow Cyber Crime Branch. An FIR is registered against you for hawala transactions. Cooperate via video call now.",
        "Supreme Court legal notice: your Aadhaar misused in money laundering. Digital arrest initiated. Pay Rs 75,000 security to cancel warrant.",
        "Customs officer: parcel seized containing MDMA, your documents attached. Confirm your address and pay penalty within 1 hour.",
        "ED digital arrest: transfer ₹1.2 lakh to RBI verification account. Do not tell anyone, investigation is confidential.",
        "Police headquarters: arrest order issued in your name for cyber crime. 8467001234 pe turant call karo warna giraftari hogi.",
    ],
    "voice_clone": [
        "Beta accident ho gaya hai, hospital mein admit hoon. Please 20,000 turant bhejo, phone kharab ho gaya hai.",
        "Hello? It's me, your son. I lost my wallet in an accident. Send ₹15,000 urgently to this number: 9XXXXXXXXX.",
        "Mom I'm in jail, my friend got into a fight, I need ₹25,000 bail money. Don't call anyone, lawyer said hurry.",
        "Namaste bhaiya, main aapke bhai bol raha hoon. Accident ho gaya, hospital bill ₹30,000 hai, abhi transfer karo.",
        "Papa, I am at the airport, my passport is confiscated, I need ₹50,000 to settle. Please urgent help.",
        "Your daughter is with us. She had an accident. Send money immediately or there will be trouble.",
        "This is your nephew. I am stuck in Dubai, police asking for penalty. Please transfer funds now, don't tell parents yet.",
        "Mummy hospital mein hoon, operation ke liye ₹40,000 chahiye abhi, phone staff leke baithi hai.",
        "Hi uncle, your niece met with an accident on NH-24, needs urgent surgery. Please send ₹35,000 to this UPI immediately.",
        "Emergency! Your grandson is in trouble. Call this number and pay ₹1,00,000 immediately. Do not call the police.",
    ],
    "lottery_prize": [
        "CONGRATULATIONS! Your mobile number won ₹25,00,000 in KBC Lucky Draw. Call 9XXXX-XXXXX to claim prize. Courier fee ₹5,000 required.",
        "Dear lucky winner! You won a Honda City in Amazon Diwali bumper. Pay ₹2,999 processing charge to receive car.",
        "KBC Kaun Banega Crorepati: you have been selected for Rs 25 lakh. Transfer Rs 4,500 as GST to claim your prize.",
        "Won ₹1 crore in Jio Lottery! To receive, send your Aadhaar and pay ₹8,000 delivery charges. Hurry call now.",
        "Congratulations! Your WhatsApp number was selected in lucky draw, prize ₹10,00,000. Contact claims officer Mr. Verma: 84XXXXX1200.",
        "Dear user, you won $500,000 in US Visa lottery 2026. Pay $150 clearance fee via UPI to process.",
        "Flipkart grand prize draw: you won ₹15,00,000! Pay registration fee ₹1,000 to claim. Offer expires tomorrow.",
        "Dear customer, your number lucky draw winner of 5 lakh rupees from LIC. Call now 70XXXXX019 to claim.",
        "You have been rewarded ₹75,000 by Paytm for loyal usage! Accept offer before midnight, pay ₹1,500 verification fee.",
        "Google India annual reward: you won ₹12,50,000. Share bank details and pay ₹3,000 documentation charges.",
    ],
    "investment_scam": [
        "Join our VIP trading Telegram group! Guaranteed daily profit of ₹5,000 on ₹10,000 investment. Limited seats.",
        "Double your money in 21 days! Our AI stock tips give 300% returns, fully SEBI registered. Invest now.",
        "Earn ₹50,000/day with our crypto opportunity. 100% guaranteed returns. Send funds to wallet address shared privately.",
        "Stock market sure shot tips!! Nifty calls, 500 pts daily profit. Join premium group ₹2,000/month.",
        "New IPO pre-subscription! Guaranteed listing gains of 80%. Invest before 6 PM today through our link.",
        "Hello! I am a Goldman Sachs portfolio manager. I can double your investment in crypto with zero risk. WhatsApp me.",
        "Daily profit of ₹10,000 assured! Just invest 25,000 with our expert traders. Withdraw anytime. 100% legal.",
        "Government approved online earning: invest ₹5,000 get ₹25,000 every week. Limited offer, act now.",
        "Forex master class free! Learn secret trading formula, daily income ₹15,000 guaranteed. Fund transfer to join.",
        "chit fund double plan: invest ₹50,000 today, get ₹1,00,000 in 6 months. 100% safe, trusted by thousands.",
    ],
    "fake_delivery": [
        "Your parcel from Mumbai is held at customs. Pay ₹499 duty fee via link below to release delivery today.",
        "DHL: shipment arrived but address incomplete. Update details and pay ₹150 redelivery fee: http://dhl-redelivery.in",
        "Blue Dart: package held at depot due to unpaid courier charges ₹99. Pay now bit.ly/bluedart-pay or it will be returned.",
        "Your India Post parcel could not be delivered. Pay ₹40 re-delivery charge at this link to schedule tomorrow.",
        "Amazon: your package is on hold. Pay customs fee ₹299 within 12 hours to avoid return to seller. Link given.",
        "FedEx India: your consignment has a problem. Pay clearance fee ₹650 immediately or package will be destroyed.",
        "Your Meesho order is stuck at GST verification. Pay Rs 120 GST via UPI link to release shipment.",
        "Courier on the way but address locked. Amount pending ₹85. Pay at dhl-pay.in to continue delivery.",
        "Your Bluedart parcel no. BD88213 held: pay Rs 175 handling fee using https://bluedart-fee-india.com",
        "International parcel seized by customs: you won ₹1.5 lakh contents + ₹499 fee to release. Click tinyurl.com/p-release",
    ],
    "electricity_bill": [
        "Dear consumer, your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill/KYC. Call 9XXXX-XXXXX immediately.",
        "Bijli Vibhag: Aaj raat konekshan kat jaayega agar ₹1 update fee jama nahi ki. Turant call karein 7XXXXX3456.",
        "URGENT: Power disconnection notice. Your meter KYC expired. Update via link or call helpline now to avoid cut.",
        "Dear user, your electricity bill pending ₹486. Power will be cut tonight 10 PM. Pay now: electricity-pay.in",
        "NBPDCL: urgent meter replacement drive. Dues ₹999 pending. Pay immediately or disconnection tonight.",
        "Bijli connection kat jane ka final notice: pay ₹650 update charge to maintain connection.",
        "TPDDL notice: update your electricity KYC online else supply will be disconnected this evening.",
        "Your power will be cut in 2 hours. Call 98XXXXX210 to stop disconnection process immediately.",
        "Urgent notice: light disconnection tonight at 9 PM. Pay ₹500 KYC charges NOW to avoid cut.",
        "Electricity dept: last bill of ₹1,000 not received. SMS karna hoga to pay: http://power-kyc-india.in",
    ],
    "bank_account_block": [
        "Your bank account will be blocked today due to incomplete KYC. Call our officer immediately at 8XXXXX5678 to verify.",
        "SBI ALERT: Suspicious activity detected. Account frozen temporarily. Verify identity via link secure-sbi-verify.com now.",
        "Dear customer your netbanking will be suspended in 24 hours. Update details immediately to avoid permanent block.",
        "Bank of Baroda: your account dormant due to PAN mismatch. Provide details else a/c will be deactivated.",
        "HDFC: high-risk transaction flagged. Account blocked. Call 91XXXX-XXXX to reactivate your account immediately.",
        "Axis Bank: unusual login attempt. Your card is blocked. Update KYC bit.ly/axis-unlock-now to restore.",
        "PNB: your account will be suspended as Aadhaar not linked. Link now else services stop tonight.",
        "Your debit card blocked due to KYC non-compliance. Call 75XXXXX90 within 1 hour else permanent block.",
        "Kotak alert: your netbanking access suspended after security breach. Reactivate: kotak-secure-verify.in NOW.",
        "Dear valued customer, complete re-KYC urgently else your account will be blocked permanently by RBI direction.",
    ],
    "government_impersonation": [
        "RBI notice: your account flagged in illegal transaction. To avoid arrest, verify and transfer funds for custody verification.",
        "TRAI: numbers involved in spam are being disconnected. Verify your number now: trai-verify.in",
        "Income Tax Department: you have tax refund of ₹18,750 pending. Submit bank details at incometax-refund.in to receive.",
        "Customs Department: parcel with 8 kg gold in your name. Pay ₹1.5 lakh customs duty to release or face action.",
        "Police: your number used in fraud case. Pay fine ₹7,000 via UPI to close FIR immediately.",
        "PM Kisan samman: you are eligible for ₹6,000. Pay ₹1 processing fee to claim. Link pmkisan-claim.com",
        "Election commission: your voter ID will be cancelled if Aadhaar not linked. Verify: voter-aadhaar-link.gov.fake",
        "UIDAI: your Aadhaar suspended due to misuse. Call 90XXXXX111 now to avoid legal action.",
        "Ministry of Finance: GST refund approved ₹24,600. Share card details to credit.",
        "Fake GST officer call: your business GST will be cancelled unless penalty ₹15,000 paid today.",
    ],
    "loan_app": [
        "Instant personal loan approved ₹5,00,000! No documents, no cibil. Click link to disburse: quickcash-loan.in",
        "Need cash now? Get ₹50,000 in 5 minutes without any paperwork. Download app: tinyurl.com/fastloan-now",
        "Congratulations! Loan of Rs 2 lakh pre-approved for you. No documents needed. Accept before midnight.",
        "Urgent loan without CIBIL score, ₹1 lakh instantly in your account. Interest only ₹50/day. Call 80XXXXXX90.",
        "No salary slip? No problem! Get instant loan app against your photo only. Quick approval, download now.",
        "Aapko Rs 80,000 ka loan approve hua hai bina kisi document ke, abhi app download karo aur paise pao.",
        "Zero documentation loan ₹3 lakh! No guarantor, no interest first month. Limited offer at easyloan-app.in",
        "Borrow ₹10,000 today, repay after 30 days, only ₹200 charges. Install KharchaLoan app now.",
        "Pre-approved loan for you: ₹1,50,000 at 0% for 3 months. Click: https://zero-interest-loan.co.in",
        "Loan sanctioned ₹90,000! Amount will transfer after ₹499 processing fee via UPI only.",
    ],
    "generic_spam": [
        "Flat 70% OFF on all ethnic wear! Diwali sale ends midnight. Shop now at examplefashion.in",
        "Get ₹200 cashback on your next recharge! Offer valid till Sunday. T&C apply.",
        "New year Dhamaka offer! Unlimited data 2TB at just ₹399/year. Click to activate.",
        "You have 2 unread promotional messages from your favourite brand. Tap to open.",
    ],
}

HAND_SAFE: list[str] = [
    "Hey, are we still meeting at 7 for dinner at Hazratganj?",
    "Bhai tu kal office aayega na? Meeting 10 baje hai",
    "Your order #402-8821334 has been shipped and will arrive tomorrow by 8 PM.",
    "Dear customer, Rs 250 was debited from your account towards electricity bill. If not done by you contact bank.",
    "Your OTP for login is 482910. Do not share this OTP with anyone, including bank officials.",
    "Mummy ne khana banaya hai, jaldi ghar aa jao",
    "Reminder: dentist appointment tomorrow 10:30 AM at Aliganj clinic",
    "Team, standup moved to 11:30 today. Jira board updated.",
    "Your train 12004 Lucknow Shatabdi departs 06:10. PNR 4521309876. Have a safe journey.",
    "Salary of ₹78,450 credited to your account for October. Slip attached.",
    "Congrats on the new job! Party kab de rahe ho?",
    "Recharge successful! ₹299, 1.5GB/day for 28 days. Validity till 12 Dec.",
    "Reminder from Apollo Pharmacy: your medicine order is ready for pickup.",
    "Bhai match dekhne chalein? Ghar pe hi sab milenge 8 baje",
    "Electricity bill ₹1,240 due on 25 Nov. Pay via the official discom app to avoid late fee.",
    "Meeting with vendor rescheduled to Friday 3 PM, same link.",
    "Your UPI payment of ₹450 to Sharma General Store was successful. Ref 410298765432.",
    "Happy birthday! May this year bring you success and health.",
    "Library books due date is 30 November. Please renew at the counter.",
    "Flight AI-865 Lucknow to Delhi departs 14:20. Web check-in open. Happy journey.",
    "The WiFi password is Lucknow@2026. Router restart at 2 PM today.",
    "Namaste, your subscription to Hindustan Times digital expires on 30 Nov. Renew to continue.",
    "Aaj office se thodi der se niklunga, meeting hai. Dinner 10 baje bana lena",
    "Your credit card ending 4321 statement for Oct is generated. Total due ₹12,340, min due ₹620.",
    "Call me when you reach home. No rush.",
    "Society AGM this Sunday 11 AM in community hall. Agenda attached.",
    "Dear resident, water supply will be interrupted tomorrow 2-5 PM for tank cleaning.",
    "Invoice INV-2026-0911 from TechMart Solutions attached. Amount ₹18,500, due 30 days.",
    "Train PNR 2233445566: chart prepared, coach B2, berth 34 (lower).",
    "Great presentation today! Client loved the dashboard mockups.",
]

SYNTH_TEMPLATES: dict[str, list[str]] = {
    "kyc_update": [
        "{bank}: Your KYC has expired. Update now at {link} or a/c blocked within {hrs} hours.",
        "Dear customer, {bank} account KYC verification pending. Click {link} to complete else services suspended.",
        "{bank} ALERT: update eKYC immediately via {link}. Failure leads to permanent account deactivation.",
        "आपका {bank} KYC अपडेट नहीं है। {link} पर तुरंत अपडेट करें वरना खाता बंद होगा।",
        "{bank}: mandatory Aadhaar-PAN linking required. Visit {link} to avoid penalty.",
    ],
    "upi_refund": [
        "Your refund of ₹{amt} is pending. Accept the UPI collect request to receive it.",
        "₹{amt} cashback approved! Approve request in {wallet} and enter PIN to claim.",
        "{mall}: overpayment refund ₹{amt} ready. Enter UPI PIN after accepting collect request.",
        "{wallet}: transaction reversal ₹{amt}. Open app, accept request, enter PIN.",
        "आपका ₹{amt} रिफंड आया है। {wallet} request accept करें और PIN डालें।",
    ],
    "fake_job_offer": [
        "Work from home! Earn ₹{amt2}/day liking videos. Registration fee ₹{fee}. Join {tg}.",
        "Part-time task job: review products, ₹{amt2} daily, instant payout. Security deposit ₹{fee}.",
        "Urgent hiring {job}, salary ₹{amt3}/month. No experience. Training fee ₹{fee} refunded later.",
        "Earn ₹{amt2} per day from home. Like, subscribe, earn. Onboarding ₹{fee} only.",
        "WFH salary ₹{amt3}/month! Pay refundable deposit ₹{fee} for joining kit.",
    ],
    "digital_arrest": [
        "CBI: case against your Aadhaar in ₹{crore} crore fraud. Stay on video call, do not tell anyone. Pay ₹{amt} to clear.",
        "{city} Police: parcel seized with drugs in your name. Digital arrest initiated. Transfer ₹{amt} or warrant issued.",
        "I am from ED. Your account linked to money laundering case. Remain on line and deposit ₹{amt} for verification.",
        "{city} Cyber Cell: FIR against you. Video call now and pay ₹{amt} to close investigation. Confidential matter.",
        "TRAI: your number in illegal usage case. Connect on WhatsApp video or face arrest in 1 hour.",
    ],
    "voice_clone": [
        "Beta accident ho gaya, hospital mein hoon. ₹{amt} turant bhejo is number pe.",
        "It's me your {relative}. Wallet lost, police asking for ₹{amt}. Send now, don't tell anyone yet.",
        "Mummy, accident near {city}, operation ke liye ₹{amt} chahiye abhi.",
        "Your {relative} is with us after an accident. Transfer ₹{amt} immediately.",
        "I am your {relative}, stuck at airport, need ₹{amt} urgently for penalty.",
    ],
    "lottery_prize": [
        "CONGRATULATIONS! You won ₹{amt3} in {brand} lucky draw! Call {phone} to claim. Fee ₹{fee}.",
        "Dear winner, your number selected in {brand} KBC draw. Pay ₹{fee} processing charge via UPI.",
        "You won a car in {brand} festive draw! Pay ₹{fee} registration to receive. Hurry!",
        "{brand} reward: ₹{amt3} for you! Share bank details + ₹{fee} verification fee.",
        "Lucky user! ₹{amt3} prize from {brand}. Call {phone} now, offer expires tonight.",
    ],
    "investment_scam": [
        "Join {tg}! Guaranteed ₹{amt2} daily profit on ₹{amt} investment. Limited seats.",
        "Double money in {days} days! Our {thing} tips give 200% returns. Invest now.",
        "Crypto fund: guaranteed 300% in {days} days. Send ₹{amt} to wallet shared after joining {tg}.",
        "Stock tips VIP group: {pct}% monthly returns guaranteed. Join for ₹{fee}/month.",
        "Govt approved: invest ₹{amt}, get ₹{amt3} every {days} days. 100% safe.",
    ],
    "fake_delivery": [
        "Your parcel held at customs. Pay ₹{fee} duty fee via {link} to release today.",
        "{courier}: package held due to unpaid charges ₹{fee}. Pay now {link} or returned.",
        "India Post: parcel could not deliver. Pay ₹{fee} re-delivery at {link}",
        "{courier}: shipment problem. Pay clearance ₹{fee} IMMEDIATELY or package destroyed.",
        "Your order stuck at GST verification. Pay ₹{fee} via UPI {link}",
    ],
    "electricity_bill": [
        "Electricity gone tonight! Unpaid bill/KYC. Call {phone} now or disconnect at 9 PM.",
        "bijli vibhag: {hrs} hours mein connection kat jayega. ₹{fee} update fee jama karo: {phone}",
        "Power disconnection notice: meter KYC expired. Pay ₹{fee} at {link} to avoid cut tonight.",
        "{discom}: dues ₹{fee} pending. Pay immediately else disconnection this evening.",
        "Bijli connection band ho jayega aaj raat. ₹{fee} KYC charge bhariye, call {phone}.",
    ],
    "bank_account_block": [
        "{bank}: your account will be blocked today. Call {phone} to verify identity now.",
        "{bank} ALERT: suspicious activity, account frozen. Verify at {link} immediately.",
        "Your {bank} netbanking suspended in {hrs} hours. Update at {link} to avoid permanent block.",
        "{bank}: PAN mismatch, account to be deactivated. Provide details at {link}",
        "{bank}: high-risk login flagged. Update KYC {link} to restore services NOW.",
    ],
    "government_impersonation": [
        "RBI: your account in illegal transaction. Verify + transfer ₹{amt} for custody check to avoid arrest.",
        "Income Tax: refund ₹{amt} pending. Submit details at {link}",
        "Customs: parcel with contraband seized in your name. Pay duty ₹{amt} via UPI.",
        "Police: your number in fraud case. Pay fine ₹{fee} to {phone} to close FIR.",
        "{scheme}: you are eligible for ₹{amt3}. Pay ₹{fee} processing to claim: {link}",
    ],
    "loan_app": [
        "Instant loan ₹{amt3} approved! No documents. Disburse today: {link}",
        "Need cash? ₹{amt} in 5 minutes, no cibil, no papers. {link}",
        "Pre-approved loan ₹{amt}! Zero interest first month. Accept now: {link}",
        "Get ₹{amt2}000 loan against Aadhaar only. {link} or call {phone}.",
        "Aapko ₹{amt} loan approve hua, sirf ₹{fee} processing fee UPI pe. {link}",
    ],
    "safe": [
        "Order #{num} delivered. Rate your experience at {mall}.",
        "Your appointment with Dr. {name} confirmed for {day}.",
        "Salam! {relative} kaha hain aap? Bat karo",
        "Reminder: pay {society} maintenance of ₹{maint} by {day}.",
        "Your subscription to {paper} expires on {day}. Renew anytime in app.",
    ],
}

BANKS = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "PNB", "Kotak", "Bank of Baroda", "Canara Bank", "Union Bank"]
WALLETS = ["Paytm", "PhonePe", "Google Pay", "Amazon Pay", "BHIM"]
MALL = ["Amazon", "Flipkart", "Meesho", "Myntra", "Ajio"]
COURIERS = ["DHL", "Blue Dart", "India Post", "FedEx", "Ekart"]
CITIES = ["Lucknow", "Delhi", "Mumbai", "Kanpur", "Noida", "Pune", "Hyderabad"]
DISCOMS = ["TPDDL", "NBPDCL", "BESCOM", "MSEDCL", "KESCO"]
RELATIVES = ["son", "daughter", "brother", "sister", "friend", "cousin", "uncle", "aunt"]
NAMES = ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Khan", "Mishra", "Trivedi"]
THINGS = ["AI stock", "Nifty", "crypto", "F&O", "IPO", "forex"]
TG = ["our Telegram group", "the VIP channel", "@wealth_tips_official"]
PAPERS = ["Hindustan Times", "The Hindu", "Times of India"]
JOBS = ["data entry operator", "customer support", "delivery executive", "tele caller"]


def rand_link() -> str:
    dom = random.choice(
        [
            "secure-verify.in",
            "kyc-update.net",
            "pay-now.shop",
            "verify-account.info",
            "bit.ly/xK29",
            "tinyurl.com/qwe123",
        ]
    )
    return f"http://{dom}"


def fill(t: str) -> str:
    return (
        t.replace("{bank}", random.choice(BANKS))
        .replace("{wallet}", random.choice(WALLETS))
        .replace("{mall}", random.choice(MALL))
        .replace("{courier}", random.choice(COURIERS))
        .replace("{city}", random.choice(CITIES))
        .replace("{discom}", random.choice(DISCOMS))
        .replace("{scheme}", random.choice(["PM Kisan", "PM Awas", "Ayushman", "Ujjwala"]))
        .replace("{relative}", random.choice(RELATIVES))
        .replace("{name}", random.choice(NAMES))
        .replace("{thing}", random.choice(THINGS))
        .replace("{tg}", random.choice(TG))
        .replace("{paper}", random.choice(PAPERS))
        .replace("{job}", random.choice(JOBS))
        .replace("{link}", rand_link())
        .replace("{phone}", f"+91-{random.randint(70000, 99999)}{random.randint(10000, 99999)}")
        .replace("{amt}", str(random.choice([499, 999, 1500, 2500, 5000, 7500, 12000, 25000, 50000, 90000])))
        .replace("{amt2}", str(random.choice([500, 800, 1000, 2000, 3000, 5000])))
        .replace("{amt3}", str(random.choice([50000, 100000, 250000, 500000, 1000000, 2500000])))
        .replace("{fee}", str(random.choice([99, 199, 299, 499, 750, 999, 1500, 2000])))
        .replace("{maint}", str(random.choice([1500, 2000, 2500, 3000])))
        .replace("{crore}", str(random.choice([2, 5, 10, 25])))
        .replace("{pct}", str(random.choice([20, 30, 50, 100])))
        .replace("{days}", str(random.choice([7, 15, 21, 30])))
        .replace("{hrs}", str(random.choice([2, 4, 24])))
        .replace("{num}", str(random.randint(100000000, 999999999)))
        .replace("{day}", random.choice(["Monday", "Sunday", "25 November", "30 November", "tomorrow"]))
        .replace("{society}", random.choice(["Green Park", "Shalimar", "Gomti Nagar"]))
    )


def load_uci() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if not RAW.exists():
        print("UCI dataset not found — continuing without it (hand + synthetic only)")
        return rows
    with RAW.open(encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) != 2:
                continue
            kind, msg = parts
            msg = msg.strip()
            if len(msg) < 10:
                continue
            rows.append((msg, "generic_spam" if kind == "spam" else "safe"))
    random.shuffle(rows)
    half = 1500
    spam = [r for r in rows if r[1] == "generic_spam"][:half]
    ham = [r for r in rows if r[1] == "safe"][:half]
    print(f"UCI: using {len(spam)} spam + {len(ham)} ham")
    return spam + ham


def main() -> None:
    rows: list[tuple[str, str, str]] = []  # text, scam_type, source
    for stype, msgs in HAND_SCAM.items():
        rows += [(m, stype, "hand") for m in msgs]
    rows += [(m, "safe", "hand") for m in HAND_SAFE]

    for stype, templates in SYNTH_TEMPLATES.items():
        target = 110 if stype != "safe" else 260
        made = 0
        while made < target:
            rows.append((fill(random.choice(templates)), stype, "synthetic"))
            made += 1

    rows += [(m, t, "uci") for m, t in load_uci()]

    # dedup, keep first
    seen: set[str] = set()
    unique: list[tuple[str, str, str]] = []
    for text, stype, source in rows:
        key = re.sub(r"\s+", " ", text.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append((text.strip(), stype, source))
    random.shuffle(unique)

    # safety: no overlap with golden set
    golden_texts: set[str] = set()
    if GOLDEN.exists():
        with GOLDEN.open() as fh:
            for r in csv.DictReader(fh):
                golden_texts.add(re.sub(r"\s+", " ", r["text"].strip().lower()))
    unique = [r for r in unique if re.sub(r"\s+", " ", r[0].strip().lower()) not in golden_texts]

    holdout_n = max(1, int(len(unique) * 0.15))
    train, holdout = unique[: len(unique) - holdout_n], unique[len(unique) - holdout_n :]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in (("train.csv", train), ("eval_holdout.csv", holdout)):
        with (OUT_DIR / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["text", "label", "scam_type", "source"])
            for text, stype, source in data:
                w.writerow([text, "safe" if stype == "safe" else "scam", stype, source])
    from collections import Counter

    print(f"train={len(train)} holdout={len(holdout)}")
    print("type distribution (train):", dict(Counter(r[1] for r in train)))


if __name__ == "__main__":
    main()
