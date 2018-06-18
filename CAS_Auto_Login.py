#!/usr/bin/python3

import os
import sys
import logging
import logging.config
import json
import re
import traceback
import socket
import requests
import yaml

from time import sleep
from bs4 import BeautifulSoup

from requests.exceptions import BaseHTTPError
from requests.exceptions import RequestException
from requests.exceptions import RetryError

os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

try:
    with open("logging.yaml", 'rt') as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
except:
    logging.basicConfig(
        format="[%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s",
        datefmt='%Y/%b/%d %H:%M:%S',
        handlers=[logging.FileHandler(filename='login.log', mode='a'), logging.StreamHandler()])
    logging.getLogger("CASLogin").setLevel(logging.INFO)
logger = logging.getLogger("CASLogin")

login = requests.session()

def load_config():
    with open('./config.json') as f:
        config = json.load(f)
    return config


def do_login(url, username, password):
    soup_login = BeautifulSoup(login.get(url).content, 'html5lib')
    logger.info('Start to get login information')

    info = {}
    for element in soup_login.find('form', id='fm1').find_all('input'):
        if element.has_attr('value'):
            info[element['name']] = element['value']

    info['username'] = username
    info['password'] = password

    url = 'https://cas.sustc.edu.cn/cas/login?service={}'.format(url)

    logger.info('Login as ' + username)

    r = login.post(url, data=info, timeout=30)
    logger.info('Login information posted to the CAS server.')

    soup_response = BeautifulSoup(r.content, 'html5lib')
    success = soup_response.find('div', {'class': 'success'})
    err = soup_response.find('div', {'class': 'errors', 'id': 'msg'})

    return success, err


def test_network(url):
    with login.get(url, timeout=10, allow_redirects=False) as test:
        if 300 > test.status_code >= 200:
            return None
        elif test.status_code == 302:
            return test.headers['Location']
        else:
            raise BaseHTTPError("Invalid status code {code}".format(code=test.status_code))


def check_ip():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as conn:
        try:
            conn.connect(('172.18.6.71', 12312))
            ip = conn.recv(128)
            logger.info("Your ip is: {ip}".format(ip=ip.decode()))
        except Exception as e:
            logger.error("Cannot get ip address: {msg}".format(msg=str(e)))


def main():
    logger.debug('Program started.')
    
    config = load_config()
    times_retry_login = config['max_times_retry_login']
    test_url = config['captive_portal_server']
    logger.debug('Configurations successfully imported.')
    
    while True:
        logger.info('Checking network status...')
        try:
            link = test_network(test_url)
            if not link:
                logger.info('You are already logged in.')
                return
            else:
                content = login.get(link, timeout=10).content
                soup_login = BeautifulSoup(content, 'html5lib')
                
                if 'CAS' not in soup_login.title.string:
                    logger.warning('Not connected to a SUSTC network')
                    return
                
                logger.info('You are offline. Starting login...')
                
                rem_link = re.search(r'window\.location = \'(.*)\';', soup_login.text).group(1)
                hostname = 'http://enet.10000.gd.cn:10001/sz/sz112/'
                service = hostname + rem_link
                
                success, err = do_login(service, config['username'], config['password'])
                
                if err:
                    logger.error('Error occurred: %s', str(err), exc_info=True)
                elif success:
                    logger.info('Login successful')
                    check_ip()
                    return
        except RequestException as err:
            logger.warn('Network FAILED.')
        
        # If keep trying to login too many times, it may trigger security alarm on the CAS server
        times_retry_login -= 1
        logger.info('{attempt} attempt(s) remaining.'.format(attempt=times_retry_login))
        if times_retry_login <= 0:
            raise RetryError
        logger.info('Try again in {time} sec. '.format(time=config['interval_retry_connection']))
        sleep(config['interval_retry_connection'])


if __name__ == '__main__':
    try:
        config = load_config()
        while True:
            main()
            sleep(config['interval_check_network'])
    except BaseHTTPError as err:
        logger.error('{msg}, consider updating \'captive_portal_server\''.format(msg=str(err)))
    except RetryError:
        logger.error('Attempts used up. The program will quit.')
    except Exception as e:
        logger.error("Critical error occurs", exc_info=True)
