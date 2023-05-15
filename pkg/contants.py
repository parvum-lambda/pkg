import os
import re
from hashlib import md5
from pkg.helpers import run_read_sync

GH_DEVICE_LOGIN_URL = "https://github.com/login/device"
LAMBDA_BASE_REPO = "parvum-lambda"
LATEST_RELEASE_IDENTIFIER = "latest"
try:
    LAMBDA_SERVICE_NAME = re.sub(r"\n", "", run_read_sync("basename -s .git `git config --get remote.origin.url`"))
    GIT_ENVIRONMENT = True
except:
    GIT_ENVIRONMENT = False
    LAMBDA_SERVICE_NAME = None

LAMBDA_PKG_SERVICE_NAME = "pkg"
DOCKERHUB_NAMESPACE = "kiske"
DOCKER_IMAGE_TAG = "1.0.0"
LAMBDA_PKG_IMAGE_NAME = DOCKERHUB_NAMESPACE + "/" + LAMBDA_PKG_SERVICE_NAME + ":" + DOCKER_IMAGE_TAG
LAMBDA_PKG_CONTAINER_NAME = LAMBDA_PKG_SERVICE_NAME
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".parvum")
GH_CACHE_DIR = os.path.join(CACHE_DIR, "gh", ".config")
WORK_DIR = os.getcwd()
WORK_DIR_HASH = md5(WORK_DIR.encode()).hexdigest()[0:12]
SUBNET_CACHE_FILE = os.path.join(CACHE_DIR, "subnet_cache.ini")
NETWORK_NAME = "parvum-lambda-" + WORK_DIR_HASH
NETWORK_SUBNET_IP = "128.0.0.0"
NETWORK_CIDR = "24"
NETWORK_SUBNET = NETWORK_SUBNET_IP + "/" + NETWORK_CIDR
PARVUM_JSON_FILE = "parvum.json"
PARVUM_LOCK_FILE = "parvum.lock"
DEFAULT_PARVUM_LOCAL_PATH = ".parvum"
DEFAULT_SERVICES_PATH = os.path.join(WORK_DIR, DEFAULT_PARVUM_LOCAL_PATH, "services")
SERVICE_COMPOSE_FILE = "docker-compose.yml"
DEFAULT_SERVICE_COMPOSE_FILE = "docker-compose.parvum.yml"
DEFAULT_COMPOSE_FILE_ASSET_LABEL = "Parvum compose file"
JSON_FILE_PATH = os.path.join(WORK_DIR, PARVUM_JSON_FILE)
LOCK_FILE_PATH = os.path.join(WORK_DIR, PARVUM_LOCK_FILE)
