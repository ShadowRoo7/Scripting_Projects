import datetime
import time
import random

# A list of good ip addresses
good_ip = [
    "192.168.1.105",
    "192.168.1.112",
    "192.168.1.118",
    "192.168.1.125",
    "192.168.1.131",
    "192.168.1.202",
    "73.152.84.11",
    "217.164.78.233",
    "142.250.185.206",
    "101.44.63.87",
]

# A list of the organization users
Users = ["Momo", "Mimo", "Admin", "Root", "Assane"]

# A list of bad ip addresses
bad_ip = ["185.220.101.141", "94.102.61.24", "45.155.205.233", "185.222.110.114"]

# A list of bad ip addresses
all_ip = good_ip + bad_ip

# Status (Failed or Accepted)
status = ["Accepted", "Failed"]


def log_generator():
    try:
        while True:
            # Simulate a Brute Force Attack 10% of the time
            if random.random() <= 0.1:
                ip = random.choice(bad_ip)
                print(f"Simulating Brute Force Attack from {ip}")

                for _ in range(4):
                    # Parsing the time
                    timestamp = datetime.datetime.now().strftime("%b %d %H:%M:%S")

                    # Generate a log line
                    log_line = f"{timestamp} sshd[1234]: {status[1]} password for root from {ip} port 22\n"

                    # Adding the log line to the Auth.log file
                    with open("auth.log", "a") as log:
                        log.write(log_line)

            else:
                ip = random.choice(all_ip)
                if ip in bad_ip:
                    # Parsing the time
                    timestamp = datetime.datetime.now().strftime("%b %d %H:%M:%S")

                    # Generate a log line
                    log_line = f"{timestamp} sshd[1234]: {status[1]} password for root from {ip} port 22\n"

                    # Adding the log line to the Auth.log file
                    with open("auth.log", "a") as log:
                        log.write(log_line)
                else:
                    timestamp = datetime.datetime.now().strftime("%b %d %H:%M:%S")
                    log_line = f"{timestamp} sshd[1234]: {status[0]} password for {random.choice(Users)} from {ip} port 22\n"

                    with open("auth.log", "a") as log:
                        log.write(log_line)

            # Wait before the next log
            time.sleep(random.uniform(1, 3))
    except KeyboardInterrupt:
        print("\n[*] Log Generator stopped by user.")


if __name__ == "__main__":
    log_generator()
