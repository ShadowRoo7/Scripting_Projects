#!/bin/bash
# It's a script that goes around the system, checks a bunch of these settings, and tells you:
# "here's what's configured, and here's whether that's good or bad." It doesn't fix anything —
#  it just reports.
# We start with the SSH config check
# We are using a while loop to read the /etc/ssh/sshd_config file to see if Root SSH login is enabled/disable
set -u
SettingName=${1:-}
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
                if [[ "$keyword" == "no" ]]
                then
                        echo "[PASS] Root login disabled entirely"
                        echo ""
                elif [[ "$keyword" == "prohibit-password" ]]
                then
                        echo "[PASS] Root login restricted to key-based auth (reasonably safe)"
                        echo ""
                elif [[ "$keyword" == "yes" ]]
                then
                        echo "[FAIL] Root login allowed with password — high risk"
                        echo ""
                else
                        echo "[Warning] Unknown Value: $keyword"
                        echo ""
                fi
        else
                echo "neither - correctly excluded"
        fi
done < <(grep "$SettingName" "/etc/ssh/sshd_config")
if [[ $matches_found -eq 0 ]]
then
        echo "$SettingName was not found"
fi
