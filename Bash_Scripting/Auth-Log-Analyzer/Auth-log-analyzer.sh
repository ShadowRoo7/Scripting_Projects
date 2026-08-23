#!/bin/bash

set -u

# Variables as command line arguments
LOGFILE="${1:-}"
THRESHOLD="${2:-5}"
WINDOW="${3:-300}"

usage() {
        echo -e "\nusage:\n\t$0 <logfile> [threshold] [window_seconds]\n" >&2
	echo -e "\t  threshold default: 5" >&2
	echo -e "\t  window_seconds: 300 (5 minutes)\n" >&2
}

# verify if the file the script user precise the path to the file while writing the command
if [[ -z "$LOGFILE" ]] 
then
	usage
	exit 1
fi

# Verify if the file exist
if [[ ! -f "$LOGFILE" ]]
then
	echo -e "log file $LOGFILE was not found\n" >&2 
	exit 1
fi

# Declaration of associtive arrays that store fail_timestamps and fail_counts
declare -A fail_timestamps
declare -A fail_counts

# Read each line in the log file
while read -r line
do
	# Verify if this is a failed/accepted line
	if [[ "$line" == *"Accepted"* ]]
	then
		ip=$(echo "$line" | grep -Po '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
		timestamp=$(echo "$line" | awk '{ print $1 }')
		
		# Reinitialize values to default
		fail_timestamps[$ip]=""
		fail_counts[$ip]=0		

	elif [[ "$line" == *"Failed"* ]]
	then
		ip=$(echo "$line" | grep -Po '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
		timestamp=$(echo "$line" | awk '{ print $1 }')
		
		# Append new value timestamp to its array and increment fail_counts
		fail_timestamps[$ip]="${fail_timestamps[$ip]:-}$timestamp "
                fail_counts[$ip]=$((${fail_counts[$ip]:-0} + 1))
	fi	

done < <(grep -E "Failed password|Accepted password" "$LOGFILE")

for ip_logged in "${!fail_counts[@]}"
do
	if [[ ${fail_counts[$ip_logged]} -ge $THRESHOLD ]]
	then
		# Convert fail_timestamps into array
		read -r -a fail_timestamps_logged_ip <<< "${fail_timestamps[$ip_logged]}"

		last_stamp="${fail_timestamps_logged_ip[-1]}"
		fifth_last_stamp="${fail_timestamps_logged_ip[-$THRESHOLD]}"

		# converting string to date
		last_stamp=$(date -d "$last_stamp" +%s)
		fifth_last_stamp=$(date -d "$fifth_last_stamp" +%s)
		
		difference=$(($last_stamp - $fifth_last_stamp))
		
		# Check if difference greater or equal to $WINDOW seconds
		if [[ $difference -le $WINDOW ]] 
		then
			echo "Brute Force Attack from $ip_logged in between $difference secondes"
		fi
			
	fi
done

