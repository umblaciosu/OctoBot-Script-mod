import requests
import time
from influxdb_client import InfluxDBClient, Point, WriteOptions

# URL of the Flask application
url = "http://localhost:5000/command"

# InfluxDB configuration
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "5JtzHoWbtAFf4n6aSZuxdSRJ7A8YUk8Rs__nVbqp2SyezVtXhsGa-AnUvbAcX0A8I7DfwfRog6OL1rSnE1rwdQ=="  # Replace with your token
INFLUXDB_ORG = "myorg"
INFLUXDB_BUCKET = "mybucket"

# Create InfluxDB client
influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = influx_client.write_api(write_options=WriteOptions(batch_size=1))

# List of commands to send
commands = [
    {"pair": "ETH/USDT", "start_date": "2022-05-03", "end_date": "2024-05-03"},
    {"pair": "BTC/USDT", "start_date": "2022-01-01", "end_date": "2024-01-01"},
    {"pair": "ADA/USDT", "start_date": "2019-06-01", "end_date": "2021-06-01"}
]

def upload_to_db(response_local,command):
    if response_local:
        # Create InfluxDB client
        influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        write_api = influx_client.write_api(write_options=WriteOptions(batch_size=1))
        
        for each_response in response_local:
            # Write to InfluxDB
            point = Point(command["pair"]) \
                .field("start_time", each_response["start_time"]) \
                .field("end_time", each_response["end_time"]) \
                .field("price_start", each_response["price_start"]) \
                .field("price_end", each_response["price_end"]) \
                .field("price_min", each_response["price_min"]) \
                .field("price_max", each_response["price_max"]) \
                .tag("human_start_time", each_response["human_start_time"]) \
                .tag("human_end_time", each_response["human_end_time"])
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
    else:
        return

def send_command(command):
    """Send a single command to the Flask API."""
    while True:
        try:
            response = requests.post(url, json=command)
            if response.status_code == 503:  # Busy response
                print("Server is busy. Retrying in 2 seconds...")
                time.sleep(2)  # Wait before retrying
                continue

            response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)
            return response.json()  # Parse and return the JSON response
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

if __name__ == "__main__":
    for command in commands:
        print(f"Sending command: {command}")
        result = send_command(command)  # Send the command and wait for the response
        if (result):
            upload_to_db(result,command)
            print(f"Response: {result}\n")
        else:
            print(f"No result for:", command["pair"],"\n")
