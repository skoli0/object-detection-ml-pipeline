import json
import os
import time

from confluent_kafka import Producer


def main() -> None:
    broker = os.getenv("REDPANDA_BROKER", "localhost:9092")
    producer = Producer({"bootstrap.servers": broker})
    topic = "inference-events"
    for i in range(5):
        payload = {"event_id": i, "image_path": f"datasets/raw/images/sample_{i}.jpg"}
        producer.produce(topic, json.dumps(payload).encode())
        producer.poll(0)
        print(f"Produced {payload}")
        time.sleep(1)
    producer.flush()


if __name__ == "__main__":
    main()
