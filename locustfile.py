"""Load test: locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 10 -t 60s"""

import random

from locust import HttpUser, between, task

MESSAGES = [
    "Your SBI KYC has expired. Update at http://sbi-kyc-now.in within 24 hours or a/c blocked.",
    "This is CBI. You are under digital arrest. Stay on the video call, do not tell anyone, transfer ₹50,000 now.",
    "Congratulations! You won ₹25,00,000 in KBC lucky draw. Pay ₹5,000 processing fee to claim.",
    "Dear customer, your order has been shipped and arrives tomorrow by 8 PM.",
    "Open PhonePe and approve the collect request to receive your ₹2,499 refund.",
    "Kal subah 7 baje gym milega? Main aa raha hoon.",
    "Work from home! Earn ₹5,000/day liking videos. Registration fee ₹999 only.",
    "Your electricity will be disconnected tonight for KYC update. Call 9XXXX-XXXXX now.",
    "Bhai kal match dekh rahe kya? 8 baje ghar wapas.",
    "₹5,000 cashback approved. Approve request in Paytm and enter PIN to claim.",
]


class ScamShieldUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(8)
    def analyze(self):
        self.client.post(
            "/v1/analyze", json={"message": random.choice(MESSAGES), "language": "auto"}, name="/v1/analyze"
        )

    @task(1)
    def health(self):
        self.client.get("/v1/health", name="/v1/health")

    @task(1)
    def stats(self):
        self.client.get("/v1/stats", params={"days": 7}, name="/v1/stats")
