import os

from pkg.container import network_exists, setup_network, get_available_ip, get_network_subnet, run_compose, \
    shutdown_compose
from pkg.contants import NETWORK_NAME, DEFAULT_SERVICES_PATH, DEFAULT_SERVICE_COMPOSE_FILE, \
    WORK_DIR, LAMBDA_SERVICE_NAME, SERVICE_COMPOSE_FILE, DOCKERHUB_NAMESPACE, WORK_DIR_HASH
from pkg.service_manager_ex import DependencyCache


class Runner:
    @staticmethod
    def run():
        for compose_service in Runner.__service_compose_iterator():
            run_compose(compose_service["compose_file_path"], envs=compose_service["env_vars"])

    @staticmethod
    def stop():
        for compose_service in Runner.__service_compose_iterator():
            shutdown_compose(compose_service["compose_file_path"], envs=compose_service["env_vars"])

    @staticmethod
    def __allocate_services_ip(services, hosts_iterator):
        if not network_exists():
            setup_network()

        service_ip_map = {}

        for service_name in services:
            service = services[service_name]

            if service is not None:
                service_path = os.path.join(DEFAULT_SERVICES_PATH, service_name, service['tag_name'])

                if not os.path.isdir(service_path):
                    continue

                compose_file_path = os.path.join(DEFAULT_SERVICES_PATH, service_name, service['tag_name'],
                                                 SERVICE_COMPOSE_FILE)

                if not os.path.isfile(compose_file_path):
                    continue

            service_ip = str(next(hosts_iterator))

            service_ip_map[service_name] = service_ip

        return service_ip_map

    @staticmethod
    def __service_compose_iterator():
        if not network_exists():
            setup_network()

        services = DependencyCache.load_services_from_lock()
        services[LAMBDA_SERVICE_NAME] = None

        compose_envs = {
            "PARVUM_NETWORK": NETWORK_NAME,
        }

        hosts_iterator = get_available_ip(get_network_subnet())
        next(hosts_iterator)

        service_ip_map = Runner.__allocate_services_ip(services, hosts_iterator)

        service_ip = str(next(hosts_iterator))
        service_ip_map[LAMBDA_SERVICE_NAME] = service_ip
        compose_envs['PARVUM_SERVICE_' + LAMBDA_SERVICE_NAME.upper() + '_IP'] = service_ip

        for service_name in services:
            if service_name not in service_ip_map:
                continue

            compose_envs['PARVUM_SERVICE_' + service_name.upper() + '_IP'] = service_ip_map[service_name]

        for service_name in services:
            service = services[service_name]

            if service_name is LAMBDA_SERVICE_NAME:
                compose_file_path = os.path.join(WORK_DIR, DEFAULT_SERVICE_COMPOSE_FILE)
            else:
                compose_file_path = os.path.join(DEFAULT_SERVICES_PATH, service_name, service['tag_name'],
                                                 SERVICE_COMPOSE_FILE)

            if not os.path.isfile(compose_file_path):
                continue

            compose_envs_service = compose_envs.copy()
            compose_envs_service["PARVUM_SERVICE_NAME"] = service_name
            compose_envs_service["PARVUM_IPV4_ADDRESS"] = service_ip_map[service_name]

            if service is not None:
                compose_envs_service["PARVUM_IMAGE"] = DOCKERHUB_NAMESPACE + '/' + service_name + ':' + service['tag_name'][1:]
                compose_envs_service["PARVUM_VERSION"] = service['tag_name'] + '-' + WORK_DIR_HASH

            yield {"compose_file_path": compose_file_path, "env_vars": compose_envs_service}
