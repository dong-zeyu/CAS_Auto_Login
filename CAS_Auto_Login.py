#!/usr/bin/python3

import os
import sys
import logging
import importlib
import json
import re
import traceback
import requests

from time import sleep
from bs4 import BeautifulSoup

from requests.exceptions import BaseHTTPError
from requests.exceptions import RequestException
from requests.exceptions import RetryError

# os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

def load_config():
    with open('./config.json') as f:
        config = json.load(f)
    return config
config = load_config()

logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s",
    datefmt='%Y/%b/%d %H:%M:%S',
    handlers=[logging.FileHandler(filename='CASLogin.log', mode='a'), logging.StreamHandler()])
logger = logging.getLogger("CASLogin")
logger.setLevel(logging.INFO)


def hot_load(module_name):
    module = __import__(module_name)
    import importlib
    
    # A bug of Python3.6- See https://github.com/python/cpython/pull/972
    if importlib._bootstrap._find_spec(module_name, None, module) is None:
        raise ModuleNotFoundError("spec not found for the module {name}".format(name=module_name), name=module_name)
    
    importlib.reload(module)
    return module


def do_login(url, username, password):
    with requests.session() as login:
        cas_page = login.get(url)
        try:
            soup_login = BeautifulSoup(cas_page.content, 'html5lib')
            
            logger.info('Start to get login information')
            logger.debug("URL: %s\nContent:\n%s", cas_page.url, cas_page.content.decode())

            info = {}
            for element in soup_login.find('form', id='fm1').find_all('input'):
                if element.has_attr('value'):
                    info[element['name']] = element['value']

            info['username'] = username
            info['password'] = password

            url = cas_page.url

            logger.info('Login as ' + username)

            r = login.post(url, data=info, timeout=30)

            logger.info('Login information posted to the CAS server.')
            logger.debug("URL: %s\nContent:\n%s", r.url, r.content.decode())

            soup_response = BeautifulSoup(r.content, 'html5lib')
            success = soup_response.find('div', {'class': 'success'})
            err = soup_response.find('div', {'class': 'errors', 'id': 'msg'})

            if success is None and err is None:
                logger.error("Bad response:\n%s", r.content.decode())
                err = "Bad response"

            return success, err
        except Exception as err:
            logger.error("Error in login:\n%s", cas_page.content.decode(), exc_info=True)
            return False, "Content error"


def test_network(url):
    with requests.get(url, timeout=10, allow_redirects=False) as test:
        if 300 > test.status_code >= 200:
            return None
        elif test.status_code == 302:
            return test.headers['Location']
        else:
            raise BaseHTTPError("Invalid status code {code}".format(code=test.status_code))


def main():

    global config
    config = load_config()
    logger.debug('Configurations successfully imported.')
    
    times_retry_login = config['max_times_retry_login']
    test_url = config['captive_portal_server']
    
    while True:
        logger.debug('Checking network status...')
        try:
            link = test_network(test_url)
            if not link:
                logger.debug('You are already logged in.')
                return
            else:
                content = requests.get(link, timeout=10).content
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
                    logger.error('Error occurred: %s', str(err))
                elif success:
                    logger.info('Login successful')
                    
                    # define the orperation after login
                    try:
                        hot_load("post_login").run()
                    except ModuleNotFoundError:
                        pass
                    except Exception as e:
                        logger.error("Error in executing run() in post_login: %s",e , exc_info=True)
                    
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
    logger.info('Program started. Monitoring network...')
    try:
        while True:
            try:
                main()
            except RetryError:
                logger.error('Attempts used up. Wait for next %d second', config['interval_check_network'])
            sleep(config['interval_check_network'])
    except BaseHTTPError as err:
        logger.error('{msg}, consider updating \'captive_portal_server\''.format(msg=str(err)))
    except Exception as e:
        logger.critical("Critical error occurs", exc_info=True)
