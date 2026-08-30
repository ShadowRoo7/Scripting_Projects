#!/bin/bash

# It's a script that goes around the system, checks a bunch of these settings, and tells you:
# "here's what's configured, and here's whether that's good or bad." It doesn't fix anything —
#  it just reports.

set -u

SettingName=${1:-}
default_settings=("PermitRootLogin" "PasswordAuthentication" "PermitEmptyPasswords" "X11Forwarding" "PubkeyAuthentication")

# Declare associative arrays
declare -A PermitRootLogin PasswordAuthentication PermitEmptyPasswords X11Forwarding PubkeyAuthentication
PermitRootLogin["no"]="[PASS] Root login disabled entirely"
PermitRootLogin["yes"]="[FAIL] Root login allowed with password (high risk)"
PermitRootLogin["prohibit-password"]="[PASS] Root login restricted to key-based auth (reasonably safe)"

PasswordAuthentication["no"]="[PASS] Disables password login and forces SSH key-based authentication (safer)"
PasswordAuthentication["yes"]="[FAIL] allows password login, which can be targeted by brute-force attacks (riskier)"

PermitEmptyPasswords["no"]="[PASS] Empty passwords are not allowed"
PermitEmptyPasswords["yes"]="[FAIL] Empty passwords are allowed — critical risk"

X11Forwarding["no"]="[PASS] X11 forwarding disabled"
X11Forwarding["yes"]="[WARNING] X11 forwarding enabled — only needed for GUI app forwarding, disable if unused"

PubkeyAuthentication["yes"]="[PASS] Key-based authentication is enabled"
PubkeyAuthentication["no"]="[FAIL] Key-based authentication is disabled — relies on weaker auth methods"

# This Function tells you any user other than root has the UID equal to 0
suspicious_user(){
	echo "--- Checking suspicious user in /etc/passwd ---"
	count=0
	while read -r line
        do
		username="$(echo "$line" | awk -F':' '{ print $1 }')"
		UserID="$(echo $line | awk -F':' '{ print $3 }')"
		
		if [[ "$username" != "root" ]] && [[ "$UserID" == "0" ]]
		then
			echo "!!!!!! Found something suspicious !!!!!!"
			echo "$username has the UID of $UserID"
			count=$((count + 1))
		fi

	done < <(cat "/etc/passwd")
	
	if [[ $count -eq 0 ]]
	then 
		echo "Nothing suspicious found in /etc/passwd"
	fi
}

# This Function tells you the verdict based on the value_to_check
lookup_verdict(){
	# Store the arguments passed to the function in these variables
	local array_name="$1"
	local value_to_check="$2"

	# table now "points at" the real array
	declare -n table="$array_name"

	# -v tests whether this specific array KEY is set at all
	if declare -p "$array_name" &>/dev/null 
	then
		if [[ -v table["$value_to_check"] ]]
		then
        		echo "${table[$value_to_check]}"
    		else
        		echo "[WARNING] unrecognized value: $value_to_check"
    		fi
	else
		echo "$array_name array does not exist"
	fi
}

# This Function read "/etc/ssh/sshd_config" file, search for all the line that has our key word 
# and output them 
# if they are settings it tells you what configuration are on set 
# if they are just comments it tells you too
Reporter(){
	local SettingName="$1"
	echo "--- Checking $SettingName ---"

	matches_found=0

	while read -r line
	do	
		matches_found=$((matches_found + 1))
        	echo ""
        	echo "$line"

        	# Check if line is commented or not
	
        	if [[ "$line" =~ ^[[:space:]]*# ]]
        	then
                	echo "This line is Commented"
                	echo ""
		
		elif [[ "$line" =~ ^[[:space:]]*$SettingName ]]
		then
                
			keyword=$(echo "$line" | awk '{ print $2 }')
			lookup_verdict "$SettingName" "$keyword"
    			echo ""
        	fi

	done < <(grep "$SettingName" "/etc/ssh/sshd_config")

	if [[ $matches_found -eq 0 ]]
	then
        	echo "$SettingName was not found"
	fi
}

if [[ -z $SettingName ]]
then
	for s in "${default_settings[@]}"; do
		Reporter "$s"
    	done
	suspicious_user
else
	Reporter "$SettingName"
	suspicious_user
fi











































