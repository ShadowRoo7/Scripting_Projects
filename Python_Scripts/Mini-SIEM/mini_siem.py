import re
import datetime
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests


class Notifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.api_url = "http://ip-api.com/json/"

    def get_geo_location(self, ip):
        # Make the request
        response = requests.get(f"{self.api_url}{ip}")

        # Extract the JSON data
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print("Error fetching geo location")
            return None

    def send_alert(self, ip):
        # Fetch the data
        geo_data = self.get_geo_location(ip)

        # Check if we got valid data
        if geo_data and geo_data.get("status") == "success":
            country = geo_data.get("country", "Unknown")
            city = geo_data.get("city", "Unknown")

            # Webhooks (Discord/Slack) need a "content" or "text" key
            message = f"🚨 **ALERT**: Brute Force Detected!\n**IP**: {ip}\n**Location**: {city}, {country}"

            # Create the payload dictionary
            payload = {"content": message}

            # Send the payload
            try:
                requests.post(self.webhook_url, json=payload)
                print(f"Alert sent for {ip} ({city}, {country})")
            except Exception as e:
                print(f"Failed to send alert: {e}")
        else:
            print(f"Could not find location for {ip}")


# url = "https://discord.com/api/webhooks/1474114391694770432/DsjpX95R687nU6b7XqC_w7XU0iY3acKV5K-3kXs8fYGzjXxu88zKamnfd8XZUOz9E0cV"
# Notifier(url).send_alert("45.155.205.233")

# A whitelist of ip addresses
whitelist = ["185.222.110.114", "185.222.110.115", "185.222.110.116"]


# Building the Parser
class LogParser:
    def __init__(self):
        # Regex pattern to capture Timestamp, Status, User, and IP
        # ex: Feb 08 22:26:05 sshd[1234]: Accepted password for Root from 192.168.1.131 port 22
        pattern = r"(?P<timestamp>\w{3} \d{2} \d{2}:\d{2}:\d{2}) sshd\[1234\]: (?P<status>\w+) password for (?P<user>\w+) from (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) port 22"

        # Compile the regex so it's ready for fast matching
        self.regex = re.compile(pattern)

    def parse(self, log_line):
        # scan the text
        match = self.regex.search(log_line)

        # Verify if the line matches the pattern
        if match:
            # Extract info from the line, store them in a dictionary and return them
            return {
                "Timestamp": match.group("timestamp"),
                "Status": match.group("status"),
                "User": match.group("user"),
                "IP": match.group("ip"),
            }
        # Otherwise if the line is empty or doesn't match the patter
        else:
            return None


# parser = LogParser()
# fake_log = "Feb 08 22:26:05 sshd[1234]: Accepted password for Root from 192.168.1.131 port 22"
# result = parser.parse(fake_log)
# print(result)


class DetectionEngine(LogParser):
    def __init__(self, notifier, threshold=3, window_size=60):
        super().__init__()
        self.notifier = notifier
        self.memory = {}
        self.threshold = threshold
        self.window_size = window_size

    def process_event(self, log_data):
        # Parse the log data using the parse method from LogParser()
        result = self.parse(log_data)

        # Verify if the result match the pattern or not if not we pass
        if result is None:
            pass
        # if the result status is "Accepted" we delete it's "IP" from the memory if existed in it else we pass
        elif result["Status"] == "Accepted":
            if result["IP"] in self.memory:
                del self.memory[result["IP"]]
            else:
                pass
        # if the result status is "Failed"
        else:
            # CONVERT: Convert the incoming log timestamp string to a datetime object
            current_dt = datetime.datetime.strptime(
                result["Timestamp"], "%b %d %H:%M:%S"
            )

            # Give a pass to the log from the IP in the whitelist
            if result["IP"] in whitelist:
                pass

            # Check if IP exists and count is less than 3
            elif (
                result["IP"] in self.memory
                and len(self.memory[result["IP"]]) < self.threshold
            ):

                valid_timestamps = []

                # Loop through the stored timestamps
                for stored_time_str in self.memory[result["IP"]]:
                    # 2. CONVERT: Convert stored string to datetime for math
                    stored_dt = datetime.datetime.strptime(
                        stored_time_str, "%b %d %H:%M:%S"
                    )

                    # 3. MATH: Calculate difference in seconds
                    if (current_dt - stored_dt).total_seconds() < self.window_size:
                        valid_timestamps.append(stored_time_str)

                # Update memory with only the recent timestamps
                self.memory[result["IP"]] = valid_timestamps

                # Add the new timestamp (stored as string)
                self.memory[result["IP"]].append(result["Timestamp"])

            # Check for alert logic
            elif (
                result["IP"] in self.memory
                and len(self.memory[result["IP"]]) >= self.threshold
            ):
                print(f"Brute Force Attack from {result['IP']}")
                self.notifier.send_alert(result["IP"])
                del self.memory[result["IP"]]

            # Else it creates the new entry
            elif result["IP"] not in self.memory:
                self.memory[result["IP"]] = [result["Timestamp"]]


"""Detector = DetectionEngine()
logs = ["Feb 08 20:26:05 sshd[1234]: Failed password for Root from 192.168.1.131 port 22",
        "Feb 08 22:26:08 sshd[1234]: Failed password for Root from 192.168.1.131 port 22",
        "Feb 08 22:27:04 sshd[1234]: Failed password for Root from 192.168.1.131 port 22"]
for log in logs:
    Detector.process_event(log)"""


class LogMonitor(FileSystemEventHandler):
    def __init__(self, engine):
        self.engine = engine
        self.last_position = 0

    def on_modified(self, event):
        # Check filename
        if "auth.log" in event.src_path:
            try:
                # Open file
                with open("auth.log", "r") as logs:
                    # Jump to bookmark
                    logs.seek(self.last_position)

                    # Read new lines
                    new_lines = logs.readlines()

                    # Update the bookmark immediately (save current spot)
                    self.last_position = logs.tell()

                    # send to the Brain
                    for new_line in new_lines:
                        self.engine.process_event(new_line)
            except FileNotFoundError:
                # Handle if file is deleted/rotated
                self.last_position = 0


if __name__ == "__main__":
    # Set up the Notifier (Paste your URL here)
    # NOTE: Replace this URL with your actual Discord Webhook URL
    url = "PASTE_YOUR_WEBHOOK_URL_HERE"

    # Create a Notifier object
    notifier = Notifier(url)

    # Create the Brain (Logic)
    # You can change threshold=3 to threshold=5 if you want to test stricter rules
    engine = DetectionEngine(notifier=notifier, threshold=3)

    # Create the Monitor (Eyes) and give it the Brain
    event_handler = LogMonitor(engine)

    # Create the Observer (The Guard)
    observer = Observer()

    # Assign the Monitor to watch the CURRENT folder ('.')
    observer.schedule(event_handler, path=".", recursive=False)

    # Start the Guard
    observer.start()

    print("[*] SIEM is active. Monitoring 'auth.log'...")

    try:
        # Keep the script running forever
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop the guard cleanly if you press Ctrl+C
        observer.stop()
        print("[*] SIEM stopped.")

    observer.join()
