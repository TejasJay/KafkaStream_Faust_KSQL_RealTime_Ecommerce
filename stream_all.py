import faust
import json  # ✅ Needed for manual decoding

app = faust.App(
    "order-payment-processor",
    broker="kafka://localhost:9092",
    store="memory://",
    web_port=6066,
    consumer_auto_offset_reset="earliest",
)

# ✅ Fix: Use `value_type=None` to prevent automatic decoding
orders_topic = app.topic("orders", value_type=None)
payments_topic = app.topic("payments", value_type=None)
users_topic = app.topic("users", value_type=None)
failed_payments_topic = app.topic("failed_payments", value_type=None)
large_orders_topic = app.topic("large_orders", value_type=None)
aggregated_revenue_topic = app.topic("aggregated_revenue", value_type=None)
frequent_failed_payments_topic = app.topic("frequent_failed_payments", value_type=None)

# ✅ Table Partitions Set to Match Kafka Topics (3 Partitions)
user_revenue = app.Table("user_revenue", default=float, partitions=3)
failed_payment_count = app.Table("failed_payment_count", default=int, partitions=3)

print("🔥 Faust Worker Started... Waiting for messages...")


# Cache to store user details
user_cache = {}

# ✅ Process Users (Store user details in cache)
@app.agent(users_topic)
async def user_details(users):
    async for user in users:
        try:
            user_data = json.loads(user) if isinstance(user, (str, bytes)) else user
            user_id = user_data.get("user_id")
            if user_id:
                user_cache[user_id] = user_data  # Store user data in cache
            print(f"✅ User Details Updated: {user_cache[user_id]}")
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode user message: {user}, Error: {e}")

# ✅ Process Orders (Lookup user details)
@app.agent(orders_topic)
async def process_orders(orders):
    async for order in orders:
        try:
            order_data = json.loads(order) if isinstance(order, (str, bytes)) else order
            user_id = order_data.get("user_id")
            if user_id in user_cache:
                user_info = user_cache[user_id]  # Retrieve user details
                print(f"✅ RECEIVED ORDER: {order_data} for User: {user_info}")
            else:
                print(f"✅ RECEIVED ORDER: {order_data} but ⚠️ WARNING: No user details found for user_id: {user_id}")
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode order message: {order}, Error: {e}")




# ✅ Process Payments
@app.agent(payments_topic)
async def process_payments(payments):
    async for payment in payments:
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

if __name__ == "__main__":
    app.main()


