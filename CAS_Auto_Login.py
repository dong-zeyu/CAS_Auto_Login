#!/usr/bin/env python3

import os
import sys
import logging
import logging.config
import json
import re
import traceback
import requests
import yaml

from time import sleep
from bs4 import BeautifulSoup

from requests.exceptions import BaseHTTPError
from requests.exceptions import RequestException
from requests.exceptions import RetryError

# os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))
sys.path.insert(0, '')

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


def hot_load(module_name):
    module = __import__(module_name)
    import importlib
    
    # A bug of Python3.6- See https://github.com/python/cpython/pull/972
    if importlib._bootstrap._find_spec(module_name, None, module) is None:
        raise ModuleNotFoundError(f"spec not found for the module {module_name!r}", name=module_name)
    
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


def wait_network(url, waiting_interval):
    while True:
        link = test_network(url)
        if not link is None:
            return link
        sleep(waiting_interval)


def load_config():
    with open('./config.json') as f:
        config = json.load(f)
    return config


def main():
    logger.info('Program started.')

    while True:
        config = load_config()
        logger.debug('Configurations successfully imported.')

        try:
            logger.info('Checking network status... [every %d sec]', config['interval_check_network'])
            link = wait_network(config['captive_portal_server'], config['interval_check_network'])

            red_page = requests.get(link, timeout=10)
            content = red_page.content
            red_page.close()

            soup_login = BeautifulSoup(content, 'html5lib')
            
            if 'CAS' not in soup_login.title.string:
                logger.warning('Not connected to a SUSTC network')
                sleep(config['interval_check_network'])
                continue
            
            logger.info('You are offline. Starting login...')
            
            rem_link = re.search(r'window\.location = \'(.*)\';', soup_login.text).group(1)
            hostname = 'http://enet.10000.gd.cn:10001/sz/sz112/'
            service = hostname + rem_link
            
            success, err = do_login(service, config['username'], config['password'])
            
            if err:
                logger.error('Error occurred: %s', str(err))
                logger.info('Try again in {time} sec. '.format(time=config['interval_retry_connection']))
                sleep(config['interval_retry_connection'])
            elif success:
                logger.info('Login successful')
                
                # define the orperation after login
                try:
                    hot_load("post_login").run(locals())
                except ModuleNotFoundError:
                    pass
                except Exception as e:
                    logger.error("Error in executing run() in post_login: %s",e , exc_info=True)
                
        except RequestException as err:
            logger.warn('Network FAILED: %s', err)
            sleep(config['interval_check_network'])
        except BaseHTTPError as err:
            logger.error('{msg}, consider updating \'captive_portal_server\''.format(msg=str(err)))
            sleep(config['interval_check_network'])
        
        

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical("Critical error occurs", exc_info=True)
