# CAS_Auto_Login
SUSTC network account auto login. Coded in Python.
## Requirements
Python2.7+

requests==2.11.

beautifulsoup4==4.5.3

## Configuration items

**captive_portal_server:** see [here](https://www.noisyfox.cn/45.html). Default is "http://captive.v2ex.co/generate_204"

**username**: Your SUSTC studnet ID

**password**: CAS login password

**interval_retry_connection**: In second. If the status check failed (e.g. the server was down or there is no Internet connection), how long the program will wait before next attempt. Default value is 30.

**max_times_retry_login**: Maximum time the program will try to login to the server. Default value is 5.
