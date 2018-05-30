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

from urllib3.exceptions import ResponseError
from requests.exceptions import ConnectionError

logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s",
    datefmt='%Y/%b/%d %H:%M:%S',
    level=logging.DEBUG,
    filename='CASLogin.log')
logging.getLogger('requests').setLevel(logging.WARNING)

login = requests.session()

def load_config():
   with open('./config.json') as f:
      config = json.load(f)
   return config


def do_login(url, username, password):
   soup_login = BeautifulSoup(login.get(url).content, 'html5lib')
   logging.info('Start to get login information')

   info = {}
   for element in soup_login.find('form', id='fm1').find_all('input'):
      if element.has_attr('value'):
         info[element['name']] = element['value']

   logging.info('Login information acquired.')

   info['username'] = username
   info['password'] = password

   url = 'https://cas.sustc.edu.cn/cas/login?service={}'.format(url)

   logging.info('Login as ' + username)

   r = login.post(url, data=info, timeout=30)
   logging.info('Login information posted to the CAS server.')
   
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
         raise ResponseError("Invalid status code {code}".format(code=test.status_code))

def main():
   logging.info('Program started.')
   
   try:
      os.chdir(os.path.dirname(sys.argv[0]))  # To read config in the same directory
   except OSError:
      pass
   config = load_config()
   times_retry_login = config['max_times_retry_login']
   test_url = config['captive_portal_server']
   logging.info('Configurations successfully imported.')
   
   while times_retry_login >= 0:
      logging.info('Checking network status...')
      try:
         link = test_network(test_url)
         if not link:
            logging.info('You are already logged in.')
            return
         else:
            content = login.get(link, timeout=10).content
            soup_login = BeautifulSoup(content, 'html5lib')
            
            if 'CAS' not in soup_login.title.string:
               logging.warning('Not connected to a SUSTC network')
               return
            
            logging.info('You are offline. Starting login...')
            
            rem_link = re.search(r'window\.location = \'(.*)\';', soup_login.text).group(1)
            hostname = 'http://enet.10000.gd.cn:10001/sz/sz112/'
            service = hostname + rem_link

            success, err = do_login(service, config['username'], config['password'])

            if err:
               logging.error('Error occurred: ' + err.text)
               times_retry_login -= 1
            elif success:
               logging.info('Login successful')
               return
      except ConnectionError as err:
         logging.warn('Connection FAILED. Try again in ' + str(config['interval_retry_connection']) + ' sec.')
         times_retry_login -= 1

      # If keep trying to login too many times, it may trigger security alarm on the CAS server
      logging.info('Try again in {time} sec. {attempt} attempt(s) remaining.'.format(time=config['interval_retry_connection'], attempt=times_retry_login))
   
   logging.error('Attempts used up. The program will quit.')


if __name__ == '__main__':
   try:
      main()
   except ResponseError as err:
      logging.error('{msg}, consider updating \'captive_portal_server\''.format(msg=str(err)))
   except Exception as e:
      logging.error("".join(traceback.format_exc()))
