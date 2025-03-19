from kafka import KafkaProducer
import json
import time
import random
from faker import Faker

fake = Faker()

# Kafka Producer Configuration
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Generate Random Payment Data
def generate_payment():
    return {
        "payment_id": fake.uuid4(),
        "order_id": fake.uuid4(),
        "user_id": random.randint(1, 100),
        "status": random.choice(["SUCCESS", "FAILED"]),
        "amount": round(random.uniform(10, 600), 2),
        "payment_method": random.choice(["Credit Card", "Debit Card", "PayPal", "Crypto"]),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# Send Payment Messages to Kafka
while True:
    payment = generate_payment()
    # print(f"Producing Payment: {payment}")
    producer.send("payments", value=payment)
    time.sleep(3)  # Simulate real-time payments
