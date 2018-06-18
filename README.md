# CAS_Auto_Login

SUSTC network account auto login. Coded in Python.

## Requirements

Python3.4+

requests

beautifulsoup4

html5lib

pyyaml

## Configuration items

**captive_portal_server:** see [here](https://www.noisyfox.cn/45.html). Default is "http://captive.v2ex.co/generate_204"

**username**: Your SUSTC studnet ID

**password**: CAS login password

**interval_check_network**: In second. Define the interval to check network status. So the program will response in at most *interval_check_network* time after the network is failed. Recommend value is 10.

**interval_retry_connection**: In second. If login was failed (e.g. the server was down or error username/password), how long the program will wait before next attempt. Recommend value is 60.
