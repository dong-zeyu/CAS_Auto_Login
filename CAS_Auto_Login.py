import json
import logging
import os
import re
import sys
import traceback
from time import sleep

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format="[%(asctime)s.%(msecs)03d] - %(levelname)s - %(message)s",
    datefmt='%Y/%b/%d %H:%M:%S',
    level=logging.DEBUG,
    filename='CASLogin.log')
logging.getLogger('requests').setLevel(logging.WARNING)

login = requests.session()

CONNECTED = 10001
CONNECTION_TIMEOUT = 10002
NEED_LOGIN = 10003


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
   try:
      with login.get(url, timeout=10, allow_redirects=False) as test:
          if 300 > test.status_code >= 200:
             return CONNECTED, None
          elif test.status_code == 302:
             content = login.get(test.headers['Location'], timeout=10).content
             soup_login = BeautifulSoup(content, 'html5lib')
             if 'CAS' not in soup_login.title.string:
                logging.warning('Not connected to a SUSTC network')
                return CONNECTED, None
             else:
                return NEED_LOGIN, re.search(r'window\.location = \'(.*)\';', soup_login.text).group(1)
          else:
             logging.warning('Recieved status code {code}, consider updating \'captive_portal_server\''.format(code=test.status_code))
             return CONNECTION_TIMEOUT, None
   except requests.RequestException:
       return CONNECTION_TIMEOUT, None


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
   
   while True:
      logging.info('Checking network status...')
      status, rem_link = test_network(test_url)
      if status == CONNECTION_TIMEOUT:
         logging.info('Connection FAILED. Try again in ' + str(config['interval_retry_connection']) + ' sec.')
         times_retry_login -= 1
      elif status == CONNECTED:
         logging.info('You are already logged in.')
         break
      elif status == NEED_LOGIN:
         logging.info('You are offline. Starting login...')

         hostname = 'http://enet.10000.gd.cn:10001/sz/sz112/'
         url = hostname + rem_link

         success, err = do_login(url, config['username'], config['password'])

         if err:
            times_retry_login -= 1
            logging.error('Error occurred: ' + err.text)
         elif success:
            logging.info('Login successful')
            break
      
      if times_retry_login > 0:
         # If keep trying to login too many times, it may trigger security alarm on the CAS server
         logging.info('Try again in {time} sec. {attempt} attempt(s) remaining.'.format(time=config['interval_retry_connection'], attempt=times_retry_login))
      else:
         logging.info('Attempts used up. The program will quit.')
         sys.exit(-1)
      sleep(config['interval_retry_connection'])
   
   logging.info('Online.')
   sys.exit(0)


if __name__ == '__main__':
   try:
      main()
   except Exception as e:
      logging.error("".join(traceback.format_exc()))
