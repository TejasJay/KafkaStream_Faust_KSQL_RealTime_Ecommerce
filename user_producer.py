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

# Dictionary to store user_id → name mapping
user_names = {}

# Function to get or generate a user name
def get_user_name(user_id):
    if user_id not in user_names:
        user_names[user_id] = fake.name()  # Generate a new name only if user_id is new
    return user_names[user_id]

# Generate Random User Activity
def generate_user_activity():
    user_id = random.randint(1, 100)  # Keep user_id consistent
    return {
        "user_id": user_id,
        "name": get_user_name(user_id),  # Fetch consistent name for user_id
        "event_type": random.choice(["signup", "login", "view_product", "add_to_cart", "purchase"]),
        "product_id": random.randint(1000, 9999) if random.choice([True, False]) else None,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# Send User Activity Messages to Kafka
while True:
    user_event = generate_user_activity()
    # print(f"Producing User Event: {user_event}")
    producer.send("users", value=user_event)
    time.sleep(4)  # Simulate real-time user activity
