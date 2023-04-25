import re

from pkg.contants import LAMBDA_BASE_REPO, LAMBDA_PKG_SERVICE_NAME, LATEST_RELEASE_IDENTIFIER, LAMBDA_SERVICE_NAME
from pkg.gh import GH
from pkg.helpers import formatex
from pkg.service import Service
from pkg.service_manager_ex.dependency_cache import DependencyCache
from pkg.service_manager_ex.dependency_stack import DependencyStack
from pkg.service_manager_ex.runner import Runner


class ServiceManagerEx:
    __dependency_stack = DependencyStack()
    __resolved_dependencies: list[Service] = []

    def __init__(self):
        self.gh = GH(LAMBDA_BASE_REPO)

    def __update(self):
        consistent_services = DependencyCache.get_consistent_services()
        self.__dependency_stack.force_push_bulk(consistent_services)
        self.__local_dependencies = DependencyCache.load_services_from_json()

        inconsistent_services = DependencyCache.get_inconsistent_services()

        for service_name in inconsistent_services:
            version = inconsistent_services[service_name]

            service = Service(service_name)
            service.prune()

            if version is not None:
                self.__dependency_stack.force_push(service_name, version)

    def ls(self):
        repos = self.gh.get_repos()

        ignored_repos = [LAMBDA_SERVICE_NAME, LAMBDA_PKG_SERVICE_NAME]

        for repo in repos:
            if repo['name'] in ignored_repos:
                continue

            print(formatex('!R' + LAMBDA_BASE_REPO + '/!B' + repo['name']))

    def install(self):
        self.__update()
        self.__resolved_dependencies += self.__dependency_stack.resolve_stack()

        for service in self.__resolved_dependencies:
            service.get_release().install()

    def require_services(self, services_raw):
        Runner.stop()
        self.__update()
        required_services = {}

        for service_raw in services_raw:
            service_name, version_constraint = self.__split_service_name_version(service_raw)

            self.__require_service(service_name, version_constraint)
            required_services[service_name] = version_constraint

        for service in self.__resolved_dependencies:
            service.get_release().install()

        DependencyCache.dump_to_json(DependencyCache.update_service_versions_dict(required_services))
        DependencyCache.dump_to_lock(self.__resolved_dependencies)

        Runner.run()

    def start(self):
        Runner.run()

    def stop(self):
        Runner.stop()

    def start_services(self):
        Runner.run()

    def stop_services(self):
        Runner.stop()

    def __require_service(self, service_name, version_constraint):
        self.__dependency_stack.push(None, service_name, version_constraint)
        self.__resolved_dependencies += self.__dependency_stack.resolve_stack()

    @staticmethod
    def __split_service_name_version(service):
        re_result = re.match(r"([^@]+)(?:@(.+))?", service)
        name = re_result.group(1)
        version_constraint = re_result.group(2)

        if version_constraint is None:
            version_constraint = LATEST_RELEASE_IDENTIFIER

        return name, version_constraint
