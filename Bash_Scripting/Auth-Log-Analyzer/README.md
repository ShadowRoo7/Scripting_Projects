# Auth Log Analyzer
 
A bash script that scans SSH authentication logs and flags source IPs showing
a brute-force login pattern — clustered failed login attempts within a short
time window.
 
## Why this matters for a SOC
 
Detecting brute-force SSH attempts is one of the most common Tier 1 SOC
triage tasks: an alert fires because a source IP has racked up a suspicious
number of failed logins, and the analyst has to decide whether it's a real
attack or noise. This script implements that exact detection logic by hand —
parsing raw auth logs, tracking failures per IP, and applying a
threshold/time-window rule — instead of relying on a SIEM's built-in rule to
do it invisibly. Understanding *how* that detection actually works under the
hood is what separates knowing how to click through a dashboard from
understanding what the dashboard is doing.
 
## What it does
 
- Parses `Failed password` and `Accepted password` lines from an SSH auth log
- Tracks the number and timing of failed login attempts per source IP
- Clears an IP's failure history once it successfully authenticates
- Flags an IP as a likely brute-force source once its most recent N failures
  (N = threshold) all happened within a configurable time window
- Configurable failure threshold and time window via command-line arguments
## Detection logic & assumptions
 
| Setting | Default | Why |
|---|---|---|
| Threshold | 5 failed attempts | A person who mistypes their password once or twice isn't suspicious on their own; repeated failures are a stronger signal. 5 is a common baseline that balances catching real attempts against generating noise from normal human error. |
| Time window | 300 seconds (5 minutes) | The key signal isn't just *how many* failures happened, but *how fast*. A human retrying a password takes minutes between attempts; an automated brute-force tool fires attempts seconds apart. The window is what tells the two apart. |
| Reset on success | Yes | A successful login is treated as evidence the account was legitimately accessed, so prior failures for that IP are cleared. This is a simplification — see Limitations. |
 
Both values can be overridden at runtime — see Usage below.
 
## Usage
 
```bash
chmod +x Auth-log-analyzer.sh
./Auth-log-analyzer.sh <logfile> [threshold] [window_seconds]
```
 
Examples:
 
```bash
# Default: 5 failures within 300 seconds
./Auth-log-analyzer.sh Generated-Auth-Log
 
# Custom: alert on 3 failures within 60 seconds (more sensitive)
./Auth-log-analyzer.sh Generated-Auth-Log 3 60
```
 
If no logfile is given, or the given path doesn't exist, the script prints a
usage message and exits with a non-zero status:
 
```
$ ./Auth-log-analyzer.sh
 
usage:
        ./Auth-log-analyzer.sh <logfile> [threshold] [window_seconds]
          threshold default: 5
          window_seconds: 300 (5 minutes)
```
 
## Sample output
 
Running against the included sample log (`Generated-Auth-Log`), which
contains a mix of normal logins, a slow scattered set of failures, and a
fast brute-force burst:
 
```
$ ./Auth-log-analyzer.sh Generated-Auth-Log
Brute Force Attack from 172.18.144.1 in between 20 secondes
```
 
Notice what's *not* flagged: `10.0.0.5`, which also had 5 failed attempts,
but spread across 40 minutes — that pattern looks like occasional human
error, not an automated attack, so the script correctly leaves it alone.
Tightening the window catches only the fast pattern; loosening it would
catch both.
 
## Sample log included
 
`Generated-Auth-Log` is a small synthetic auth log covering three scenarios:
 
- A user who fails twice, then logs in successfully (history cleared, no alert)
- An IP that fails once, succeeds, then returns and fails 5 more times in 20
  seconds (correctly flagged)
- An IP with 5 failures spread over 40 minutes (correctly *not* flagged)
No real credentials, hostnames, or IPs are involved — it's synthetic data,
so anyone can clone this repo and run the script immediately.
 
## Limitations / what I'd add next
 
- This is a **batch/offline analyzer** — it reads the whole file once rather
  than monitoring in real time. A natural next step would be a `tail -f`
  based version that checks continuously and could auto-block an offending
  IP (e.g. via `iptables`), with a whitelist to avoid locking out legitimate
  admins.
- "Reset on success" means an attacker who eventually guesses correctly
  right at the end of a burst won't have that specific burst flagged in
  isolation, since the successful login clears the count. A production
  detector would likely also flag the *pattern* (many failures immediately
  followed by a success), not just ongoing failure bursts.
- IPv4 only — the IP-matching pattern doesn't currently recognize IPv6
  addresses.
- Doesn't distinguish between usernames targeted from the same IP (e.g. one
  attacker trying many accounts vs. repeatedly hitting one account) — that
  distinction could be a useful follow-up analysis.
- Assumes a consistent log format; tested against both ISO-8601-style
  timestamps and lines with Windows-style (CRLF) line endings, but hasn't
  been tested against every real-world auth.log variant (e.g. classic
  syslog timestamps like `Jul 24 08:12:01`).
## Requirements
 
- bash 4+ (associative arrays)
- Standard GNU coreutils (`grep -P`, `awk`, `date -d`)
