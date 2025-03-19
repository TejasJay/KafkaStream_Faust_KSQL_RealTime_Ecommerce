**Step 1: Setting up Kafka, Zookeeper, and Topic Management**

In this first step, we will go over the setup of Kafka, Zookeeper, and the automation of topic management for the project. These topics are used for processing orders, payments, and user data, as well as for keeping track of aggregated revenue and failed payments.

### **Overview of the Setup**

We start by ensuring that Kafka and Zookeeper are running. The `automate.sh` script handles this process automatically. It checks if the services are already running, and if they are not, it starts them.

### **Automation Script: `automate.sh`**

```bash
#!/bin/bash

# Function to check if a process is running
is_running() {
    pgrep -f "$1" > /dev/null 2>&1
}

# Start Zookeeper if not running
if is_running "QuorumPeerMain"; then
    echo "Zookeeper is already running."
else
    echo "Starting Zookeeper..."
    ~/kafka/bin/zookeeper-server-start.sh ~/kafka/config/zookeeper.properties &
    sleep 20
fi

# Start Kafka Broker if not running
if is_running "kafka.Kafka"; then
    echo "Kafka Broker is already running."
else
    echo "Starting Kafka Broker..."
    ~/kafka/bin/kafka-server-start.sh ~/kafka/config/server.properties &
    sleep 20
fi

# List all topics and delete them
for topic in $(~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092); do
    if [[ "$topic" != "__consumer_offsets" ]]; then  # Avoid deleting the internal Kafka topic
        echo "Deleting topic: $topic"
        ~/kafka/bin/kafka-topics.sh --delete --topic "$topic" --bootstrap-server localhost:9092
    fi
done

# Wait a few seconds for Kafka to process the deletion
sleep 10

# Create Kafka Topics (Skip if already exists)
echo "Ensuring Kafka topics exist..."
~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "orders" || \
~/kafka/bin/kafka-topics.sh --create --topic orders --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "payments" || \
~/kafka/bin/kafka-topics.sh --create --topic payments --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "users" || \
~/kafka/bin/kafka-topics.sh --create --topic users --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "aggregated_revenue" || \
~/kafka/bin/kafka-topics.sh --create --topic aggregated_revenue --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "failed_payments" || \
~/kafka/bin/kafka-topics.sh --create --topic failed_payments --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "frequent_failed_payments" || \
~/kafka/bin/kafka-topics.sh --create --topic frequent_failed_payments --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 | grep -q "large_orders" || \
~/kafka/bin/kafka-topics.sh --create --topic large_orders --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

# Start Log Generators if not running
for script in "order_producer.py" "payment_producer.py" "user_producer.py"; do
    if is_running "$script"; then
        echo "$script is already running."
    else
        echo "Starting $script..."
        python3 ~/kafka_ecom/$script &
    fi
done

echo "All required services are running!"
```

### **What Does This Script Do?**

1.  **Zookeeper and Kafka Service Check:**
    -   It checks if the Zookeeper and Kafka services are running using the `is_running` function.
    -   If they are not running, the script starts them using the appropriate start commands (`zookeeper-server-start.sh` and `kafka-server-start.sh`).
2.  **Topic Deletion:**
    -   The script lists all the existing Kafka topics and deletes any existing topics (except for the internal `__consumer_offsets` topic).
    -   This ensures that you're working with a clean slate and prevents any old or unwanted data from interfering with the new topics.
3.  **Topic Creation:**
    -   After cleaning up the topics, the script creates the necessary Kafka topics (`orders`, `payments`, `users`, `aggregated_revenue`, `failed_payments`, `frequent_failed_payments`, and `large_orders`), each with 3 partitions and a replication factor of 1. This step ensures that the Kafka topics are properly configured for the project.
4.  **Log Generators:**
    -   The script then checks if the log generator scripts (`order_producer.py`, `payment_producer.py`, `user_producer.py`) are running. If they are not running, it starts them. These producers generate random data (orders, payments, and user activities) and send it to the respective Kafka topics.
* * *

**Step 2: Creating Kafka Producers to Simulate Data Flow**

In this step, we will review how to simulate the data flow by creating Kafka producers. The goal of these producers is to generate random data for orders, payments, and user activity, which are then sent to their respective Kafka topics. These producers will continuously send simulated data to Kafka, which will later be consumed by Faust agents for processing.

### **Overview of the Producers**

You have three separate producers for simulating orders, payments, and user activities. Each of these producers is written in Python and uses the `KafkaProducer` from the `kafka-python` library. Here’s a breakdown of each producer:

* * *

### **Order Producer: `order_producer.py`**

This script generates random order data and sends it to the Kafka topic `orders`.

#### **Code Explanation:**

```python
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
```

#### **What the Script Does:**

1.  **Kafka Producer Configuration:** It sets up the Kafka producer with `localhost:9092` as the Kafka broker.
2.  **Order Generation:** The `generate_order` function creates random order data. Each order includes an `order_id`, `user_id`, `product_id`, `quantity`, `price`, and `timestamp`.
3.  **Sending Messages:** The producer sends each generated order to the Kafka `orders` topic in JSON format. It simulates real-time order flow by sending an order every 2 seconds.
* * *

### **Payment Producer: `payment_producer.py`**

This script generates random payment data and sends it to the Kafka topic `payments`.

#### **Code Explanation:**

```python
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
        "amount": round(random.uniform(10, 500), 2),
        "payment_method": random.choice(["Credit Card", "Debit Card", "PayPal", "Crypto"]),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# Send Payment Messages to Kafka
while True:
    payment = generate_payment()
    # print(f"Producing Payment: {payment}")
    producer.send("payments", value=payment)
    time.sleep(3)  # Simulate real-time payments
```

#### **What the Script Does:**

1.  **Kafka Producer Configuration:** The producer is set up similarly to the order producer, sending data to `localhost:9092`.
2.  **Payment Generation:** The `generate_payment` function creates random payment data, including `payment_id`, `order_id`, `user_id`, `status` (either "SUCCESS" or "FAILED"), `amount`, `payment_method`, and `timestamp`.
3.  **Sending Messages:** The producer sends each generated payment to the Kafka `payments` topic in JSON format. The script sends a payment every 3 seconds to simulate real-time payments.
* * *

### **User Activity Producer: `user_producer.py`**

This script generates random user activity data and sends it to the Kafka topic `users`.

#### **Code Explanation:**

```python
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
```

#### **What the Script Does:**

1.  **Kafka Producer Configuration:** The producer is set up in the same way, targeting the `users` Kafka topic.
2.  **User Activity Generation:** The `generate_user_activity` function creates random user activities. Each event includes `user_id`, `name`, `event_type` (such as signup, login, view, add to cart, or purchase), `product_id` (if applicable), and `timestamp`.
3.  **Sending Messages:** Each generated user activity is sent to the Kafka `users` topic. A new event is sent every 4 seconds to simulate real-time user activities.
* * *

### **What These Producers Achieve:**

-   **Simulate Data for Kafka:** These producers continuously send simulated data to Kafka, enabling you to test the entire pipeline.
-   **Topic Populating:** They populate the Kafka topics (`orders`, `payments`, `users`) with sample data, which will later be consumed and processed by Faust agents.
* * *

**Step 3: Setting Up Faust Consumers to Process Kafka Data**

In this step, we will configure Faust agents to consume the data from the Kafka topics (`orders`, `payments`, `users`) that we populated in the previous step. The agents will process this data, perform necessary operations like aggregating revenue, detecting failed payments, and managing frequent failed payment events.

### **Overview of Faust Consumers**

Faust is an asynchronous stream processing library that interacts directly with Kafka. We will create multiple Faust agents to consume data from different Kafka topics and process it in real-time. Here is how we configured the Faust consumers for our topics:

* * *

### **1\. Setting up Faust App**

We start by creating a Faust app that connects to the Kafka broker (`localhost:9092`). The app will consume messages from various Kafka topics and store intermediate results in an in-memory store.

#### **Code Explanation:**

```python
import faust
import json  # Needed for manual decoding

app = faust.App(
    "order-payment-processor",
    broker="kafka://localhost:9092",
    store="memory://",
    web_port=6066,
    consumer_auto_offset_reset="earliest",
)

# Define topics
orders_topic = app.topic("orders", value_type=None)
payments_topic = app.topic("payments", value_type=None)
failed_payments_topic = app.topic("failed_payments", value_type=None)
large_orders_topic = app.topic("large_orders", value_type=None)
aggregated_revenue_topic = app.topic("aggregated_revenue", value_type=None)
frequent_failed_payments_topic = app.topic("frequent_failed_payments", value_type=None)

# Define tables to track state
user_revenue = app.Table("user_revenue", default=float, partitions=3)
failed_payment_count = app.Table("failed_payment_count", default=int, partitions=3)

print("🔥 Faust Worker Started... Waiting for messages...")
```

#### **Explanation:**

1.  **App Configuration:**
    -   The `faust.App` object connects to the Kafka broker at `localhost:9092`.
    -   We store intermediate data in memory (`store="memory://"`) and reset the consumer offsets to the earliest available messages (`consumer_auto_offset_reset="earliest"`).
    -   The web interface is available at `http://localhost:6066/` for monitoring.
2.  **Topics:** We define Faust topics that correspond to Kafka topics:
    -   `orders`, `payments`, `failed_payments`, `large_orders`, `aggregated_revenue`, and `frequent_failed_payments`.
    -   The `value_type=None` tells Faust not to automatically decode the messages, as we're handling decoding manually.
3.  **Tables:** We define two in-memory tables for tracking the user revenue and failed payment count:
    -   `user_revenue`: A table that stores total revenue by `user_id`.
    -   `failed_payment_count`: A table that counts the number of failed payments for each user.
* * *

### **2\. Processing Orders**

The first agent will consume the `orders` topic and process the incoming order messages. It will aggregate the total revenue per user and send the aggregated revenue to the `aggregated_revenue` topic.

#### **Code Explanation:**

```python
# ✅ Process Orders
@app.agent(orders_topic)
async def process_orders(orders):
    async for order in orders:
        try:
            order_data = json.loads(order) if isinstance(order, (str, bytes)) else order
            print(f"✅ RECEIVED ORDER: {order_data}")
            user_revenue[order_data["user_id"]] += order_data["price"]

            revenue_event = {
                "user_id": order_data["user_id"],
                "total_revenue": user_revenue[order_data["user_id"]],
                "timestamp": order_data["timestamp"]
            }
            print(f"📊 AGGREGATED REVENUE: {revenue_event}")
            await aggregated_revenue_topic.send(value=json.dumps(revenue_event))

        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode order message: {order}, Error: {e}")
```

#### **What the Agent Does:**

1.  **Consumption of Orders:** This agent listens to the `orders` topic and processes each incoming order.
2.  **Order Processing:**
    -   It tries to decode the order message from JSON (if necessary).
    -   It updates the `user_revenue` table by adding the order price to the user's total revenue.
3.  **Sending Aggregated Revenue:** After processing the order, the agent sends the aggregated revenue for the user to the `aggregated_revenue` topic.
* * *

### **3\. Processing Payments**

The second agent consumes the `payments` topic and checks if the payment status is "FAILED" or if the payment amount exceeds $500. If a payment is marked as "FAILED," the agent will track the failed payment and update the `failed_payment_count` table.

#### **Code Explanation:**

```python
# ✅ Process Payments
@app.agent(payments_topic)
async def process_payments(payments):
    async for payment in payments:
        print(f"✅ RECEIVED PAYMENT: {payment}")

        try:
            payment_data = json.loads(payment) if isinstance(payment, (str, bytes)) else payment
            print(f"✅ RECEIVED PAYMENT: {payment_data}")

            # 🚨 Detect Failed Payments
            if payment_data["status"] == "FAILED":
                failed_event = {
                    "order_id": payment_data["order_id"],
                    "user_id": payment_data["user_id"],
                    "amount": payment_data["amount"],
                    "payment_method": payment_data["payment_method"],
                    "timestamp": payment_data["timestamp"]
                }
                print(f"🚨 FAILED PAYMENT DETECTED: {failed_event}")
                await failed_payments_topic.send(value=json.dumps(failed_event))

                # Update failure count for user
                failed_payment_count[payment_data["user_id"]] += 1

            # 🚀 Detect Large Payments (Above $500)
            if payment_data["amount"] > 500:
                large_payment_event = {
                    "order_id": payment_data["order_id"],
                    "user_id": payment_data["user_id"],
                    "amount": payment_data["amount"],
                    "payment_method": payment_data["payment_method"],
                    "timestamp": payment_data["timestamp"]
                }
                print(f"💰 LARGE PAYMENT DETECTED: {large_payment_event}")
                await large_orders_topic.send(value=json.dumps(large_payment_event))

        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode payment message: {payment}, Error: {e}")
```

#### **What the Agent Does:**

1.  **Consumption of Payments:** This agent listens to the `payments` topic and processes each payment message.
2.  **Detect Failed Payments:** If a payment's status is "FAILED," it sends a failure event to the `failed_payments` topic and updates the `failed_payment_count` table for that user.
3.  **Detect Large Payments:** If the payment amount exceeds $500, it sends a large payment event to the `large_orders` topic.
* * *

### **4\. Detecting Frequent Failed Payments**

The third agent consumes the `failed_payments` topic and tracks how many failed payments a user has made. If a user exceeds three failed payments, it sends a warning message to the `frequent_failed_payments` topic.

#### **Code Explanation:**

```python
# ✅ Detect Frequent Failed Payments
@app.agent(failed_payments_topic)
async def count_failed_payments(failed_payments):
    async for failure in failed_payments:
        try:
            failure_data = json.loads(failure) if isinstance(failure, (str, bytes)) else failure
            user_id = failure_data["user_id"]
            failed_payment_count[user_id] += 1

            if failed_payment_count[user_id] > 3:  # If a user has more than 3 failed payments
                warning_event = {
                    "user_id": user_id,
                    "failed_payment_count": failed_payment_count[user_id],
                    "last_failed_timestamp": failure_data["timestamp"]
                }
                print(f"⚠️ FREQUENT FAILED PAYMENTS: {warning_event}")
                await frequent_failed_payments_topic.send(value=json.dumps(warning_event))

        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode failed payment message: {failure}, Error: {e}")
```

#### **What the Agent Does:**

1.  **Consumption of Failed Payments:** This agent listens to the `failed_payments` topic and processes each failed payment.
2.  **Tracking Failures:** It increments the `failed_payment_count` for the user in the `failed_payment_count` table.
3.  **Frequent Failed Payments:** If a user has more than three failed payments, it sends a warning to the `frequent_failed_payments` topic.
* * *

**Step 4: Aggregating Data and Stream Processing**

In this step, we’ll dive deeper into how the data is processed, aggregated, and stored in real-time using Faust’s streaming capabilities. We’ve already set up our Faust agents to consume data from Kafka topics, but now we’ll focus on how we aggregate specific data and send it to the relevant Kafka topics for further processing.

* * *

### **Overview of Stream Processing with Faust**

Faust is designed to handle real-time stream processing. It can listen to Kafka topics, process the data as it arrives, and perform operations such as aggregation, filtering, or transformation. Once the data is processed, Faust can write the output back to Kafka or to an external storage system.

For our case, we’ll use Faust to:

1.  **Aggregate user revenue** from `orders`.
2.  **Detect failed payments** and monitor for **frequent failed payments**.
3.  **Monitor large payments**.
4.  **Create stream filters** for data like failed payments and large orders.
* * *

### **1\. Aggregate User Revenue**

We’ll aggregate the total revenue for each user as orders are processed. For this, we define a **Faust Table** (`user_revenue`), which stores the aggregated revenue by `user_id`.

#### **Code Explanation:**

```python
# ✅ Aggregate User Revenue
@app.agent(orders_topic)
async def aggregate_revenue(orders):
    async for order in orders:
        try:
            order_data = json.loads(order) if isinstance(order, (str, bytes)) else order
            user_revenue[order_data["user_id"]] += order_data["price"]

            revenue_event = {
                "user_id": order_data["user_id"],
                "total_revenue": user_revenue[order_data["user_id"]],
                "timestamp": order_data["timestamp"]
            }
            print(f"📊 AGGREGATED REVENUE: {revenue_event}")
            await aggregated_revenue_topic.send(value=json.dumps(revenue_event))

        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode order message: {order}, Error: {e}")
```

#### **What’s Happening Here:**

1.  **Agent Consumption:** The agent listens to the `orders` topic and processes each order.
2.  **Revenue Calculation:** For each order, the agent increments the total revenue for the corresponding user by adding the `price` to the `user_revenue` table.
3.  **Sending Aggregated Revenue:** After processing the order, the agent sends the aggregated revenue for the user to the `aggregated_revenue` topic.

The `user_revenue` table allows us to keep track of each user’s total revenue, and we can use this table for real-time aggregation of user purchases.

* * *

### **2\. Detecting Large Payments**

The `process_payments` agent is responsible for detecting payments that exceed $500 and sending them to the `large_orders` Kafka topic.

#### **Code Explanation:**

```python
# 🚀 Detect Large Payments (Above $500)
if payment_data["amount"] > 500:
    large_payment_event = {
        "order_id": payment_data["order_id"],
        "user_id": payment_data["user_id"],
        "amount": payment_data["amount"],
        "payment_method": payment_data["payment_method"],
        "timestamp": payment_data["timestamp"]
    }
    print(f"💰 LARGE PAYMENT DETECTED: {large_payment_event}")
    await large_orders_topic.send(value=json.dumps(large_payment_event))
```

#### **What’s Happening Here:**

1.  **Large Payment Detection:** If the payment amount exceeds $500, it’s considered a large payment.
2.  **Sending to Kafka:** The agent sends the large payment event to the `large_orders` topic for further processing or analysis.

This allows the system to keep track of large payments, which can be useful for fraud detection, monitoring, or reporting.

* * *

### **3\. Detecting Failed Payments**

The `process_payments` agent also detects payments with a "FAILED" status. If a payment fails, it triggers an event that is sent to the `failed_payments` Kafka topic. The failed payment count is tracked for each user.

#### **Code Explanation:**

```python
# 🚨 Detect Failed Payments
if payment_data["status"] == "FAILED":
    failed_event = {
        "order_id": payment_data["order_id"],
        "user_id": payment_data["user_id"],
        "amount": payment_data["amount"],
        "payment_method": payment_data["payment_method"],
        "timestamp": payment_data["timestamp"]
    }
    print(f"🚨 FAILED PAYMENT DETECTED: {failed_event}")
    await failed_payments_topic.send(value=json.dumps(failed_event))

    # Update failure count for user
    failed_payment_count[payment_data["user_id"]] += 1
```

#### **What’s Happening Here:**

1.  **Failed Payment Detection:** The agent checks if the `payment_data["status"]` is "FAILED."
2.  **Failure Event:** If the payment failed, it creates a `failed_event` and sends it to the `failed_payments` Kafka topic.
3.  **Failed Payment Count:** It also increments the failed payment count for the user in the `failed_payment_count` table.
* * *

### **4\. Detecting Frequent Failed Payments**

The `count_failed_payments` agent monitors the failed payment count for each user. If the user exceeds a threshold of three failed payments, it triggers an event to notify about frequent failed payments.

#### **Code Explanation:**

```python
# ✅ Detect Frequent Failed Payments
@app.agent(failed_payments_topic)
async def count_failed_payments(failed_payments):
    async for failure in failed_payments:
        try:
            failure_data = json.loads(failure) if isinstance(failure, (str, bytes)) else failure
            user_id = failure_data["user_id"]
            failed_payment_count[user_id] += 1

            if failed_payment_count[user_id] > 3:  # If a user has more than 3 failed payments
                warning_event = {
                    "user_id": user_id,
                    "failed_payment_count": failed_payment_count[user_id],
                    "last_failed_timestamp": failure_data["timestamp"]
                }
                print(f"⚠️ FREQUENT FAILED PAYMENTS: {warning_event}")
                await frequent_failed_payments_topic.send(value=json.dumps(warning_event))

        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode failed payment message: {failure}, Error: {e}")
```

#### **What’s Happening Here:**

1.  **Frequent Failed Payment Detection:** The agent listens to the `failed_payments` topic, and for each failed payment, it increments the count in the `failed_payment_count` table.
2.  **Threshold Check:** If the number of failed payments exceeds three, it triggers a warning event.
3.  **Sending Warning Event:** The warning event is sent to the `frequent_failed_payments` topic for further action, such as notifying the user or flagging their account.
* * *


* * *

### **Step 5: Monitoring the Data with KSQL**

In this step, we will focus on **monitoring the Kafka topics** using **KSQL** (Kafka Query Language). KSQL allows us to run SQL-like queries on our Kafka topics and create real-time streaming data pipelines.

* * *

### **1\. Monitoring with KSQL**

After producing and consuming data using Faust, we can interact with it using **KSQL**. KSQL is designed to process and query streaming data in real time, allowing you to filter, aggregate, and manipulate data stored in Kafka topics.

#### **1.1 Starting KSQL CLI (KSQL Shell)**

To interact with Kafka streams and tables, we can use the **KSQL CLI**. Here’s how you can start the KSQL shell:

1.  **Navigate to the Kafka directory where KSQL is installed.**

    ```bash
    cd ~/kafka/confluent-7.0.0/bin
    ```

2.  **Start the KSQL CLI**:

    ```bash
    ./ksql
    ```

    Once you run this command, you should see the KSQL CLI prompt:

    ```bash
    ksql>
    ```

    This means that you are now in the interactive KSQL shell, ready to run queries on Kafka topics.

* * *

#### **1.2 Creating Streams for Kafka Topics**

Now, let’s define the streams for our Kafka topics (like `orders`, `payments`, `failed_payments`, etc.) using the KSQL shell. Here's how we define streams for the topics we've created:

```sql
-- Create a stream for Orders
CREATE STREAM orders_stream (
  order_id STRING,
  user_id INT,
  product_id INT,
  quantity INT,
  price DOUBLE,
  timestamp STRING
) WITH (KAFKA_TOPIC='orders', VALUE_FORMAT='JSON', PARTITIONS=3);

-- Create a stream for Payments
CREATE STREAM payments_stream (
  payment_id STRING,
  order_id STRING,
  user_id INT,
  status STRING,
  amount DOUBLE,
  payment_method STRING,
  timestamp STRING
) WITH (KAFKA_TOPIC='payments', VALUE_FORMAT='JSON', PARTITIONS=3);

-- Create a stream for Failed Payments
CREATE STREAM failed_payments_stream (
  order_id STRING,
  user_id INT,
  amount DOUBLE,
  payment_method STRING,
  timestamp STRING
) WITH (KAFKA_TOPIC='failed_payments', VALUE_FORMAT='JSON', PARTITIONS=3);

-- Create a stream for Large Orders (where amount > 500)
CREATE STREAM large_orders_stream AS
SELECT * FROM orders_stream
WHERE price > 500
EMIT CHANGES;

-- Create a stream for Aggregated Revenue
CREATE STREAM aggregated_revenue_stream AS
SELECT user_id, SUM(price) AS total_revenue
FROM orders_stream
GROUP BY user_id
EMIT CHANGES;
```

#### **Explanation:**

-   **Creating Streams:**
    -   Each `CREATE STREAM` statement defines a stream corresponding to a Kafka topic. The streams are connected to the Kafka topics (`orders`, `payments`, `failed_payments`) where the data is being produced.
-   **Filtering and Aggregating Data:**
    -   For `large_orders_stream`, we filter out orders that have a price greater than $500.
    -   For `aggregated_revenue_stream`, we aggregate the revenue by `user_id` using a `SUM` function over the `price` field.
-   **EMIT CHANGES:**
    -   The `EMIT CHANGES` clause ensures that the query runs continuously, meaning it will keep processing new messages as they arrive in the stream.
* * *

### **2\. Testing the KSQL Stream**

After creating the streams, you can test them by querying the stream to see real-time data being processed. For example:

```sql
-- Query the large orders stream
SELECT * FROM large_orders_stream EMIT CHANGES;

-- Query the aggregated revenue stream
SELECT * FROM aggregated_revenue_stream EMIT CHANGES;
```

These queries will display the data from the streams in real time as new records are added to the Kafka topics.

* * *



### **Step 6: Handling Partitions and Rebalancing**

This step is crucial for ensuring that Kafka topics are properly distributed and that there are no issues with partition allocation, replication, and leader election. Here's how we approached it:

#### **6.1 Rebalancing Partitions**

In Kafka, partitions are distributed across brokers to ensure load balancing. If topics grow, you might need to redistribute partitions across brokers to optimize the system.

1.  **List Kafka Topics**
    The first task was to list all Kafka topics to understand their partition and replication setup. Using the `kafka-topics.sh` command, we listed all topics:

    Example:

    ```bash
    ~/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
    ```

2.  **Describe Kafka Topics**
    We described the topics to understand their partition count and replication factor. This helps in ensuring that the topics are distributed appropriately.

    Example:

    ```bash
    ~/kafka/bin/kafka-topics.sh --describe --topic orders --bootstrap-server localhost:9092
    ```

    Output might look like:

    ```bash
    Topic: orders PartitionCount: 3 ReplicationFactor: 1
    ```

    This shows that the topic `orders` has 3 partitions and a replication factor of 1.

3.  **Rebalancing Partitions**
    When a topic's partition distribution wasn't optimal, we needed to rebalance the partitions. Kafka allows us to manually reassign partitions across brokers. First, we created a reassignment JSON file (`reassignment.json`), specifying which partitions to move to which brokers.

    Example of the reassignment JSON file:

    ```json
    {
      "version": 1,
      "partitions": [
        {
          "topic": "orders",
          "partition": 0,
          "replicas": [0]
        },
        {
          "topic": "orders",
          "partition": 1,
          "replicas": [0]
        },
        {
          "topic": "orders",
          "partition": 2,
          "replicas": [0]
        }
      ]
    }
    ```

    Then, we executed the reassignment with:

    ```bash
    ~/kafka/bin/kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --reassignment-json-file reassignment.json --execute
    ```

    This command moved the partitions across brokers as specified in the JSON file.

4.  **Verifying Rebalancing**
    After executing the reassignment, we verified that the partitions were balanced across the brokers. This was done by running the `describe` command again:

    ```bash
    ~/kafka/bin/kafka-topics.sh --describe --topic orders --bootstrap-server localhost:9092
    ```

    The `Leader`, `Replicas`, and `ISR` (in-sync replicas) columns should reflect the new partition distribution.

* * *

#### **6.2 Leader Election**

Kafka partitions have a leader that handles read and write operations. If the leader fails, Kafka automatically elects a new leader. We can also manually trigger the leader election for partitions when necessary.

1.  **Triggering Leader Election**
    To ensure that the correct leader is elected, especially in cases of partition leadership issues, we triggered the leader election process using the `kafka-leader-election.sh` script.

    Example command:

    ```bash
    ~/kafka/bin/kafka-leader-election.sh --bootstrap-server localhost:9092 --topic orders --partition 0 --election-type preferred
    ```

    In this case, we triggered leader election for partition 0 of the `orders` topic.

2.  **Verifying Leader Election**
    After running the leader election, we verified the current leader for the partition using the `describe` command again:

    ```bash
    ~/kafka/bin/kafka-topics.sh --describe --topic orders --bootstrap-server localhost:9092
    ```

    This ensures that the leader for the partitions is correctly assigned, and no partitions are leaderless.

* * *



### **Step 7: Troubleshooting Issues**

In this step, we focused on identifying and resolving issues related to partition mismatches, Kafka consumer errors, and group coordination. Here's a breakdown of how we handled these problems:

#### **7.1 Partition Mismatch Errors**

A common issue that can arise in a Kafka setup is a **partition mismatch** between the main topic and its changelog topic. Changelog topics are internal Kafka topics that track changes to tables in Kafka Streams or Faust, and they must have the same number of partitions as the main topic.

1.  **Identifying Partition Mismatch** The error we encountered was related to partition mismatches. For example, you might see an error message like:

    ```
    PartitionsMismatch: The source topic 'orders' for table 'user_revenue'
    has 1 partition, but the changelog topic 'orders_changelog' has 3 partitions.
    ```

    This occurs when the number of partitions in the source topic and the corresponding changelog topic don't match. It’s important to ensure they are in sync to avoid data inconsistencies or errors in the application.

2.  **Resolving Partition Mismatch** To resolve this issue, we made sure that the partition count of all the changelog topics matched that of the source topic. This can be done by adjusting the partitions for the changelog topic to match the source topic’s partition count.

    Example:

    ```bash
    ~/kafka/bin/kafka-topics.sh --alter --topic orders_changelog --partitions 3 --bootstrap-server localhost:9092
    ```

    This command adjusts the partition count of the `orders_changelog` topic to match that of the `orders` topic, resolving the mismatch issue.

3.  **Verifying Partition Consistency** After making the necessary changes, we verified that all topics (main and changelog) had the same partition count:

    ```bash
    ~/kafka/bin/kafka-topics.sh --describe --topic orders --bootstrap-server localhost:9092
    ~/kafka/bin/kafka-topics.sh --describe --topic orders_changelog --bootstrap-server localhost:9092
    ```

    This helped us confirm that both the main topic and changelog topic were now aligned in terms of partitioning.

* * *

#### **7.2 Kafka Consumer Errors**

During our setup, we faced issues with Kafka consumers, especially related to group coordination. Kafka consumer groups are used to share the work of consuming messages across multiple consumers. However, misconfigurations or failures in the consumer group can cause issues.

1.  **Identifying Consumer Group Issues** One of the common errors is related to group coordination. For instance:

    ```
    Group Coordinator Request failed: [Error 15] GroupCoordinatorNotAvailableError
    ```

    This error happens when the Kafka broker fails to coordinate the consumer group. The cause could be a broker failure, improper configurations, or network issues.

2.  **Troubleshooting Consumer Group Errors** To resolve this, we performed the following steps:
    -   **Ensure Kafka Broker is Running**: Ensure that the Kafka broker is running and accessible by the consumer. We verified this by checking the status of the Kafka server:

        ```bash
        sudo systemctl status kafka
        ```

    -   **Check Kafka Consumer Group Status**: We used the `kafka-consumer-groups.sh` command to inspect the status of our consumer groups and their lag.

        ```bash
        ~/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group order-payment-processor
        ```

        This helps us understand the offset and lag of each consumer group and whether any consumer has fallen behind or failed to process messages.

3.  **Resolving Group Coordinator Issues** To fix coordination issues, we:
    -   Ensured that the consumer group was properly configured.
    -   If necessary, reset the offsets for the consumer group using:

        ```bash
        ~/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group order-payment-processor --reset-offsets --to-earliest --execute
        ```

    This command resets the offsets to the earliest message for the specified consumer group.

4.  **Restarting Kafka Broker (If Needed)** If the group coordinator issues persisted, we restarted the Kafka broker to refresh the broker state:

    ```bash
    sudo systemctl restart kafka
    ```

    This helped resolve issues related to stale broker states that could affect group coordination.

* * *

#### **7.3 Addressing Configuration Issues**

1.  **Invalid Kafka Configuration**
    A potential issue might be incorrect configuration in the Kafka server or consumer settings. In this case, we ensured that all configurations were correct, especially for consumer groups and partition assignments.

2.  **Check Broker and Partition Assignments** We ensured the partitions were assigned correctly across brokers using the `kafka-reassign-partitions.sh` script, and that no broker had overburdened partitions.
* * *


### **Step 8: Logging and Monitoring**

In this step, we set up monitoring and logging to ensure the system runs smoothly and we can easily troubleshoot or improve performance. We focused on observing Kafka topics, KSQL queries, and Faust logs. Monitoring is crucial in understanding system behavior, performance metrics, and troubleshooting issues that arise in production.

#### **8.1 KSQL Query Monitoring**

1.  **Log Queries in KSQL:** KSQL provides a robust platform for performing stream processing queries on data stored in Kafka topics. For each KSQL query we ran (e.g., for detecting large payments or aggregating revenue), we needed to monitor for any errors or failures during query execution.
    -   **Start the KSQL Server**: As mentioned before, we started the KSQL server:

        ```bash
        ./ksql-server-start ../etc/ksql/ksql-server.properties
        ```

    -   **View Query Logs**: Logs for KSQL queries can be viewed in the KSQL server logs. We can use the following command to check logs related to KSQL:

        ```bash
        tail -f /var/log/confluent/ksql-server.log
        ```

        This gives us real-time feedback on how the queries are being executed, and if there are any issues like resource allocation problems or query syntax errors.

2.  **Monitor Query Execution:** In KSQL, queries like `CREATE STREAM` and `CREATE TABLE` are used to process and store streaming data. For example:

    ```sql
    CREATE STREAM large_orders_stream AS
    SELECT * FROM orders_stream
    WHERE amount > 500
    EMIT CHANGES;
    ```

    The **EMIT CHANGES** statement continuously streams the results. The query execution can be monitored using:

    ```bash
    SHOW QUERIES;
    ```

    This will display the running queries, their statuses, and details about each stream or table created.

    -   **Monitor for Errors**: If a query fails due to a schema mismatch, partitioning issues, or incorrect input data, the error message will be printed in the logs.
    -   **Cancel Queries**: If a query is problematic or needs to be stopped for any reason, it can be canceled:

        ```sql
        CANCEL QUERY <query_id>;
        ```

    Example log output for a successful query:

    ```
    2025-03-18 13:32:45,234 INFO  Query running: CREATE STREAM large_orders_stream AS SELECT * FROM orders_stream WHERE amount > 500 EMIT CHANGES;
    2025-03-18 13:32:50,345 INFO  Stream large_orders_stream created.
    ```

* * *

#### **8.2 Faust Worker Logging**

Faust is a Python stream processing library that interacts with Kafka and performs operations like aggregations or detecting failed payments. Faust workers produce logs that are crucial to understanding if the tasks are running as expected.

1.  **Faust Worker Logs**: Faust generates logs for each agent it runs. For example, for the `process_orders` and `process_payments` agents, you will see log entries such as:

    ```
    ✅ RECEIVED ORDER: {'order_id': '1', 'user_id': 99, 'product_id': 101, 'quantity': 1, 'price': 100.0, 'timestamp': '2025-03-18 13:31:10'}
    🚨 FAILED PAYMENT DETECTED: {'order_id': '1', 'user_id': 99, 'amount': 100.0, 'payment_method': 'Credit Card', 'timestamp': '2025-03-18 13:32:00'}
    ```

    These logs give insights into the processing of orders, payments, and detection of events like failed payments or large payments.

2.  **Faust Logging Configuration**: You can configure Faust logging to capture more detailed logs (e.g., debug information) by adjusting the logging configuration:

    ```python
    import logging
    logging.basicConfig(level=logging.DEBUG)  # Change to DEBUG for more detailed logs
    ```

    Faust by default outputs logs to `stderr`, but they can be redirected to files or monitored using other logging tools for real-time feedback.

3.  **Using Faust Web Interface for Monitoring**: Faust also comes with a built-in web interface that you can access on `localhost:6066`:
    -   This provides a view of the streams, tables, and queries currently running.
    -   You can use this web interface to monitor stream progress, check on agent health, and troubleshoot issues.

    Access it by visiting:

    ```
    http://localhost:6066
    ```

    The web interface gives a detailed view of the state of all Faust applications and the data flowing through the streams.

* * *

#### **8.3 Kafka Consumer and Producer Logs**

Monitoring Kafka consumers and producers is also crucial for troubleshooting. Consumer group offsets, lag, and throughput provide critical insights into Kafka's real-time operation.

1.  **Kafka Consumer Logs**: The consumer group's lag and status can be monitored using the `kafka-consumer-groups.sh` script:

    ```bash
    ~/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group order-payment-processor
    ```

    This will display details on how far behind each consumer group is in terms of message processing, helping to identify any consumers that are lagging or experiencing issues.

2.  **Kafka Producer Logs**: Kafka producers send messages to Kafka topics, and their performance can be monitored for any delays or failures. Producers in Kafka also have internal logs, which you can monitor to detect issues like delivery failures or buffer overflows:
    -   For high-volume systems, producers may log warnings about buffer sizes or request timeouts.
* * *














