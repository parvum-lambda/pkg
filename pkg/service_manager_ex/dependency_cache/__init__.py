import json
import os

from semantic_version import Version, NpmSpec

from pkg.contants import JSON_FILE_PATH, LOCK_FILE_PATH
from pkg.service import Service


class DependencyCache:
    @staticmethod
    def get_consistent_services():
        consistent_services = {}
        lock_services = DependencyCache.load_services_from_lock()
        inconsistency_services = DependencyCache.get_inconsistent_services()

        for service_name in lock_services:
            if service_name not in inconsistency_services:
                consistent_services[service_name] = lock_services[service_name]["tag_name"][1:]

        return consistent_services

    @staticmethod
    def get_inconsistent_services():
        inconsistency_services = {}
        json_services = DependencyCache.load_services_from_json()
        lock_services = DependencyCache.load_services_from_lock()

        for service_name in json_services:
            if service_name not in lock_services:
                inconsistency_services[service_name] = json_services[service_name]
            elif Version(lock_services[service_name]["tag_name"][1:]) not in NpmSpec(json_services[service_name]):
                inconsistency_services[service_name] = json_services[service_name]

        return inconsistency_services

    @staticmethod
    def get_json_contents():
        if DependencyCache.__json_exists():
            json_file = open(JSON_FILE_PATH, "r")
            json_file_data = json_file.read()
            json_file.close()

            return json.loads(json_file_data)

        return {}

    @staticmethod
    def get_lock_contents():
        if DependencyCache.__lock_exists():
            lock_file = open(LOCK_FILE_PATH, "r")
            json_file_data = lock_file.read()
            lock_file.close()

            return json.loads(json_file_data)

        return {}

    @staticmethod
    def __json_exists():
        return os.path.isfile(JSON_FILE_PATH)

    @staticmethod
    def __lock_exists():
        return os.path.isfile(LOCK_FILE_PATH)

    @staticmethod
    def load_services_from_json():
        services = {}
        json_file = DependencyCache.get_json_contents()

        if "services" in json_file:
            for service_name in json_file["services"]:
                if type(json_file["services"][service_name]) is str:
                    version = json_file["services"][service_name]
                else:
                    version = json_file["services"][service_name]["version"]

                services[service_name] = version

        return services

    @staticmethod
    def update_service_versions_dict(services):
        json_file = DependencyCache.get_json_contents()

        if "services" not in json_file:
            json_file["services"] = {}

        for service_name in services:
            version = services[service_name]

            if service_name not in json_file["services"]:
                json_file["services"][service_name] = version
            else:
                if type(json_file["services"][service_name]) is str:
                    json_file["services"][service_name] = version
                else:
                    json_file["services"][service_name]["version"] = version

        return json_file

    @staticmethod
    def dump_to_json(_json):
        with open(JSON_FILE_PATH, 'w') as fp:
            json.dump(_json, fp, indent=4)
            fp.close()

    @staticmethod
    def dump_to_lock(services: list[Service]):
        service_dict = {}

        for service in services:
            service_dict[service.name()] = service.get_release().data()

        with open(LOCK_FILE_PATH, 'w') as fp:
            json.dump(service_dict, fp, indent=4)
            fp.close()

    @staticmethod
    def load_services_from_lock():
        return DependencyCache.get_lock_contents()
