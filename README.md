# CAS_Auto_Login

SUSTC network account auto login. Coded in Python.

## Requirements

Python3.6+

requests >= 2.18.0

beautifulsoup4

html5lib

pyyaml

## Configuration

The following file are either required or optional for this program. Each file must be put into current working directory to have effect. You can refer to `*.sample` file in code tree for more information.

### config.json (required)

- **captive_portal_server:** see [here](https://www.noisyfox.cn/45.html). You will need to put a URL that will response a status code like `2XX` and  other status code are not accepted. Default is "<http://captive.v2ex.co/generate_204>"

- **username**: Your SUSTC student ID

- **password**: CAS login password

- **interval_check_network**: In second. Define the interval to check network status. So the program will response in at most *interval_check_network* time after the network is failed. Recommend value is 10.

- **interval_retry_connection**: In second. If login was failed (e.g. the server was down or error username/password), how long the program will wait before next attempt. Recommend value is 60.

### logging.yaml (optional)

Logging configuration. See Python document for [logging](https://docs.python.org/3/library/logging.config.html) for detailed information. If not set, the program will log to both console and a file named `login.log`

### post_login.py (optional)

This program provides a callback function after a successful login operation in order to get the ip address, update DDNS information, run a specific program and etc.. The program will hot load `post_login.py` and call `post_login.run` with parameter `local()`. You can refer to the code to see what information you will have in `local()`. Please make sure that your script have a function named `run` with exactly one positional parameter.
