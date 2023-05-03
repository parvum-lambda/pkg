from typing import Dict

from pkg.contants import LAMBDA_SERVICE_NAME, LAMBDA_BASE_REPO
from pkg.helpers import formatex
from pkg.service import Service, ReleaseNotFound, ServiceNotFound
from pkg.service.release import Release


class DependencyStack:

    def __init__(self):
        self.__stack_buffer = {}
        self.__release_stack = []

        pass

    def force_push(self, service_name: str, version: str):
        service = Service(service_name).match_release(version)

        self.__stack_buffer.update({
            service_name: {
                LAMBDA_SERVICE_NAME + '(self)': version
            }
        })
        self.__release_stack.append(service.get_release().id)

    def force_push_bulk(self, services: Dict[str, str]):
        for service_name in services:
            self.force_push(service_name, services[service_name])

    def push_from_release(self, release: Release):
        dependencies = release.dependencies()

        for dependency_name in dependencies:
            self.push(release.service(), dependency_name, dependencies[dependency_name])

    def push(self, required_by: Service or None, service_name_buffer: str, version: str):
        service_name = service_name_buffer.lower()

        if service_name is LAMBDA_SERVICE_NAME:
            return

        if required_by is None:
            required_by_key = LAMBDA_SERVICE_NAME + '(self)'
        else:
            required_by_key = required_by.name() + '@' + required_by.get_release().version()

        try:
            service = Service(service_name).match_release(version)
        except ServiceNotFound as service_not_found:
            print(formatex('!BService not found!R' + LAMBDA_BASE_REPO + '/!B' + service_not_found.name))
            exit(1)
        except ReleaseNotFound as release_not_found:
            print(formatex(
                '!BService not found!R' + LAMBDA_BASE_REPO + '/!B' + release_not_found.service_name +
                '@' + release_not_found.version_constraint
            ))
            exit(1)

        if service_name not in self.__stack_buffer:
            self.__stack_buffer.update({
                service_name: {
                    required_by_key: version
                }
            })
        else:
            self.__stack_buffer[service_name].update({
                required_by_key: version
            })

        release_id = service.get_release().id()

        if release_id in self.__release_stack:
            return

        self.__release_stack.append(release_id)

        self.push_from_release(service.get_release())

    def resolve_stack(self):
        resolved_stack = []

        for service_name in self.__stack_buffer:
            versions = []

            for required_by in self.__stack_buffer[service_name]:
                versions.append(self.__stack_buffer[service_name][required_by])

            try:
                service = Service(service_name).match_release(' '.join(versions))
                resolved_stack.append(service)
            except ReleaseNotFound:
                print(formatex('!B!rDependency conflict:'))

                for required_by in self.__stack_buffer[service_name]:
                    print(formatex('- Service !B' + required_by + ' !Rrequires !B' + service_name + '!R@!B!r' + self.__stack_buffer[service_name][required_by]))

                return None

        return resolved_stack
