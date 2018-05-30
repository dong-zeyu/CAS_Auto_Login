#!/usr/bin/python

import json
import logging
import os
import re
import sys
import traceback
import requests

from time import sleep
from bs4 import BeautifulSoup

from requests.exceptions import HTTPError
from requests.exceptions import ConnectionError

os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s",
    datefmt='%Y/%b/%d %H:%M:%S',
    handlers=[logging.FileHandler(filename='CASLogin.log', mode='a'), logging.StreamHandler()])
logger = logging.getLogger("CASLogin")
logger.setLevel(logging.DEBUG)

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

    logger.info('Login information acquired.')

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
            raise HTTPError("Invalid status code {code}".format(code=test.status_code))

def main():
    logger.info('Program started.')
    
    
    config = load_config()
    times_retry_login = config['max_times_retry_login']
    test_url = config['captive_portal_server']
    logger.info('Configurations successfully imported.')
    
    while times_retry_login >= 0:
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
                    logger.error('Error occurred: ' + err.text)
                    times_retry_login -= 1
                elif success:
                    logger.info('Login successful')
                    return
        except ConnectionError as err:
            logger.warn('Connection FAILED. Try again in ' + str(config['interval_retry_connection']) + ' sec.')
            times_retry_login -= 1
        
        # If keep trying to login too many times, it may trigger security alarm on the CAS server
        logger.info('Try again in {time} sec. {attempt} attempt(s) remaining.'.format(time=config['interval_retry_connection'], attempt=times_retry_login))
    
    logger.error('Attempts used up. The program will quit.')


if __name__ == '__main__':
    try:
        main()
    except HTTPError as err:
        logger.error('{msg}, consider updating \'captive_portal_server\''.format(msg=str(err)))
    except Exception as e:
        logger.error("".join(traceback.format_exc()))
 