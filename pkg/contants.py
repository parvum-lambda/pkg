import os
import re
from pkg.helpers import run_read_sync
from hashlib import md5

GH_DEVICE_LOGIN_URL = "https://github.com/login/device"
LAMBDA_BASE_REPO = "parvum-lambda"
LAMBDA_PKG_SERVICE_NAME = re.sub(r"\n", "", run_read_sync("basename -s .git `git config --get remote.origin.url`"))
LAMBDA_PKG_IMAGE_NAME = LAMBDA_PKG_SERVICE_NAME
LAMBDA_PKG_CONTAINER_NAME = LAMBDA_PKG_SERVICE_NAME
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WORK_DIR = os.getcwd()
WORK_DIR_HASH = md5(WORK_DIR.encode()).hexdigest()[0:12]
SUBNET_CACHE_FILE = os.path.join(BASE_DIR, 'subnet_cache.ini')
NETWORK_NAME = "parvum-lambda-" + WORK_DIR_HASH
NETWORK_SUBNET_IP = "128.0.0.0"
NETWORK_CIDR = "24"
NETWORK_SUBNET = NETWORK_SUBNET_IP + "/" + NETWORK_CIDR
