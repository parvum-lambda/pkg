import os
import re
import subprocess

from pkg.contants import GH_DEVICE_LOGIN_URL, LAMBDA_PKG_IMAGE_NAME, LAMBDA_PKG_CONTAINER_NAME, WORK_DIR, \
    WORK_DIR_HASH, SUBNET_CACHE_FILE, NETWORK_NAME, NETWORK_SUBNET, GH_CACHE_DIR
from pkg.gh import GH, GHConfigError, GHInvalidToken
from pkg.helpers import run_read_sync
from ipaddress import IPv4Network


def get_image_hash():
    result = subprocess.run(['docker', 'images', '-f', 'reference=' + LAMBDA_PKG_IMAGE_NAME, '-q'], capture_output=True,
                            text=True)
    return re.sub('\r?\n', '', result.stdout)


def get_container_hash():
    result = subprocess.run(['docker', 'container', 'ls', '-f', 'name=' + LAMBDA_PKG_CONTAINER_NAME, '-aq'],
                            capture_output=True, text=True)
    return re.sub('\r?\n', '', result.stdout)


def get_network_hash():
    result = subprocess.run(['docker', 'network', 'ls', '-f', 'name=' + NETWORK_NAME, '-q'], capture_output=True,
                            text=True)
    return re.sub('\r?\n', '', result.stdout)


def network_exists():
    return get_network_hash() != ''


def image_exists():
    return get_image_hash() != ''


def container_exists():
    return get_container_hash() != ''


def remove_container():
    subprocess.run(['docker', 'container', 'rm', '-f', LAMBDA_PKG_CONTAINER_NAME], capture_output=True, text=True)


def remove_image():
    subprocess.run(['docker', 'image', 'rm', get_image_hash()], capture_output=True, text=True)


def build_image():
    os.system('docker build --tag ' + LAMBDA_PKG_IMAGE_NAME + ' ' + WORK_DIR)


def get_network_subnet():
    subnet_cache_lines = []

    if os.path.isfile(SUBNET_CACHE_FILE):
        read_stream = open(SUBNET_CACHE_FILE, 'r')
        subnet_cache_lines = read_stream.readlines()
        read_stream.close()

    subnet_map = {}

    for subnet_cache_raw in subnet_cache_lines:
        subnet_cache_raw_trimmed = re.sub(r'\n', '', subnet_cache_raw)

        if len(subnet_cache_raw_trimmed) == 0:
            continue

        subnet_cache_match = re.match(r'^([^=]+)=([^=]+)$', subnet_cache_raw_trimmed)
        subnet_map[subnet_cache_match.group(1)] = subnet_cache_match.group(2)

    if WORK_DIR_HASH in subnet_map:
        return subnet_map[WORK_DIR_HASH]

    base_subnet = NETWORK_SUBNET

    if len(subnet_map) > 0:
        base_subnet = subnet_map[list(subnet_map)[-1]]

    base_subnet_split_math = re.match(r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(/\d{1,2})', base_subnet)

    ip_segments = [
        base_subnet_split_math.group(1),
        base_subnet_split_math.group(2),
        base_subnet_split_math.group(3),
        base_subnet_split_math.group(4),
    ]
    cidr = base_subnet_split_math.group(5)

    first_segment = int(ip_segments[0])
    second_segment = int(ip_segments[1])

    if second_segment == first_segment:
        raise NetworkSubnetGenerateError

    ip_segments[1] = str(second_segment + 1)

    subnet = '.'.join(ip_segments) + cidr

    append_stream = open(SUBNET_CACHE_FILE, 'a')
    append_stream.write(WORK_DIR_HASH + '=' + subnet + '\n')
    append_stream.close()

    return subnet


def setup_network():
    os.system('docker network create -d=bridge --subnet=' + get_network_subnet() + ' ' + NETWORK_NAME)


def get_browser_command():
    commands = ['xdg-open', 'x-www-browser', 'open']

    for command in commands:
        result = subprocess.run(['which', command],
                                capture_output=True, text=True)

        if not not result.stdout:
            return command


def start_container():
    if not image_exists():
        print("Image not found, use init instead")
        return

    if container_exists():
        print("Container already running")
        return

    os.system(
        'docker run -it --rm --name ' + LAMBDA_PKG_CONTAINER_NAME + ' ' +
        '-v "' + GH_CACHE_DIR + ':/root/.config/gh" ' + LAMBDA_PKG_IMAGE_NAME)


def get_gh_credentials():
    if not image_exists():
        build_image()

    if container_exists():
        remove_container()

    browser_command = get_browser_command()
    os.system(browser_command + ' ' + GH_DEVICE_LOGIN_URL)

    start_container()


def setup(force):
    if force:
        get_gh_credentials()
        return

    try:
        GH('')
        print("No action required")
    except GHConfigError or GHInvalidToken:
        get_gh_credentials()


def run_compose(compose_file, envs=None):
    run_read_sync('docker-compose -f ' + compose_file + ' up -d', env_vars=envs)


def shutdown_compose(compose_file, envs=None):
    run_read_sync('docker-compose -f ' + compose_file + ' down', env_vars=envs)


def get_available_ip(subnet):
    network = IPv4Network(subnet)

    return network.hosts()


class NetworkSubnetGenerateError(BaseException):
    def __init__(self):
        self.message = "Cannot generate a new subnet"
