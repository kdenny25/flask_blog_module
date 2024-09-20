import os

ALLOWED_HOSTS = [os.environ['WEBSITE_HOSTNAME']] if 'WEBSITE_HOSTNAME' in os.environ else []
CSRF_TRUSTED_ORIGINS = ['https://' + os.environ['WEBSITE_HOSTNAME']] if 'WEBSITE_HOSTNAME' in os.environ else []

CONN_STRING = os.environ['CONN_STRING']

SECRET_KEY = os.environ['SECRET_KEY']
GOOGLE_LOGIN_CLIENTID = os.environ['GOOGLE_LOGIN_CLIENTID']