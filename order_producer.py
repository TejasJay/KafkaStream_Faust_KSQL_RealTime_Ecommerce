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

# Generate Random Order Data
def generate_order():
    return {
        "order_id": fake.uuid4(),
        "user_id": random.randint(1, 100),
        "product_id": random.randint(1000, 9999),
        "quantity": random.randint(1, 5),
        "price": round(random.uniform(10, 500), 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# Send Order Messages to Kafka
while True:
    order = generate_order()
    # print(f"Producing Order: {order}")
    producer.send("orders", value=order)
    time.sleep(2)  # Simulate real-time order flow
