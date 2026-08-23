#!/bin/bash

# It's a script that goes around the system, checks a bunch of these settings, and tells you:
# "here's what's configured, and here's whether that's good or bad." It doesn't fix anything —
#  it just reports.

set -u

SettingName=${1:-}

# Declare associative array, where each key is a combination of setting name and value
declare -A PermitRootLogin PasswordAuthentication
PermitRootLogin["no"]="[PASS] Root login disabled entirely"
PermitRootLogin["yes"]="[FAIL] Root login allowed with password (high risk)"
PermitRootLogin["prohibit-password"]="[PASS] Root login restricted to key-based auth (reasonably safe)"
PasswordAuthentication["no"]="[PASS] Disables password login and forces SSH key-based authentication (safer)"
PasswordAuthentication["yes"]="[FAIL] allows password login, which can be targeted by brute-force attacks (riskier)"

lookup_verdict(){
	# Store the arguments passed to the function in these variables
	local array_name="$1"
	local value_to_check="$2"

	# table now "points at" the real array
	declare -n table="$array_name"

	# -v tests whether this specific array KEY is set at all
	if declare -p $array_name &>/dev/null 
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

usage(){
        echo -e "\nusage:\n\t$0 <SettingName> [...]\n" >&2
}

matches_found=0

if [[ -z $SettingName ]]
then
        usage
        exit 1
fi

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

