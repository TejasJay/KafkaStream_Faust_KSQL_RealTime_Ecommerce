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
   # Avoid deleting the internal Kafka topic
    echo "Deleting topic: $topic"
    ~/kafka/bin/kafka-topics.sh --delete --topic "$topic" --bootstrap-server localhost:9092
    
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


sleep 20

# Start Log Generators if not running
for script in "order_producer.py" "payment_producer.py" "user_producer.py"; do
    if is_running "$script"; then
        echo "$script is already running."
    else
        echo "Starting $script..."
        python3 ~/kafka_ecom/$script &
    fi
done

sleep 20

if is_running "ksql-server-start"; then
    echo "KSQL Server is already running."
else
    echo "Starting KSQL Server..."
    ~/kafka/confluent/bin/ksql-server-start ~/kafka/confluent/etc/ksqldb/ksql-server.properties &
    sleep 20
fi


echo "All required services are running!"
