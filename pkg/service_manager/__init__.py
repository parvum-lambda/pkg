import json
import os
import re
import tarfile

from semantic_version import Spec, Version

from pkg.contants import WORK_DIR, LAMBDA_BASE_REPO, LAMBDA_PKG_SERVICE_NAME
from pkg.gh import GH, GHRequestError
from pkg.helpers import formatex, run_read_sync


class ServiceManager:
    VERSION_SEPARATOR = '@'
    LATEST_RELEASE_IDENTIFIER = 'latest'
    ERR_NONE = 0
    ERR_SERVICE_NOT_FOUND = 1
    ERR_VERSION_NOT_FOUND = 2
    ERR_COULD_NOT_GET_RELEASES = 3
    WARN_NONE = 0
    WARN_SETUP_SCRIPT_NOT_FOUND = 1 << 0
    WARN_COMPOSE_NOT_FILE_FOUND = 1 << 1

    DEFAULT_SERVICES_PATH = WORK_DIR + '/.parvum/services'
    DEFAULT_SERVICE_SETUP_SCRIPT = 'setup.parvum.sh'
    DEFAULT_SERVICE_COMPOSE_FILE = 'docker-compose.parvum.yml'
    PARVUM_JSON_FILE = 'parvum.json'
    PARVUM_LOCK_FILE = 'parvum.lock'
    JSON_FILE_PATH = os.path.join(WORK_DIR, PARVUM_JSON_FILE)
    LOCK_FILE_PATH = os.path.join(WORK_DIR, PARVUM_LOCK_FILE)

    def __init__(self):
        self.gh = GH(LAMBDA_BASE_REPO)

    def ls(self):
        repos = self.gh.get_repos()

        for repo in repos:
            if repo['name'] == LAMBDA_PKG_SERVICE_NAME:
                continue

            print(formatex('!R' + LAMBDA_BASE_REPO + '/!B' + repo['name']))

    def install(self):
        if os.path.isfile(self.LOCK_FILE_PATH):
            self.__install_from_lock()
        elif os.path.isfile(self.JSON_FILE_PATH):
            self.__install_from_json()

    def start(self):
        services = self.__load_services_from_lock()

        compose_files = {}

        for service_name in services:
            compose_file = self.__get_service_compose_file(service_name, services[service_name])

            if compose_file is None:
                continue

            compose_files[service_name] = compose_file

        print(compose_files)

    def require(self, services):
        services_releases = []
        require_errors = []

        for service in services:
            name, version_constraint = self.__split_service_name_version(service)
            release_buffer = self.__require_service(name, version_constraint)

            if release_buffer["error"] == self.ERR_NONE:
                services_releases.append(release_buffer)
            else:
                require_errors.append(release_buffer)

        for service in services_releases:
            self.__check_and_run_service_files(service)

        self.__format_json_file(services_releases)
        self.__format_lock_file(services_releases)

        for service in services_releases:
            self.__print_warns(service)

        for service in require_errors:
            self.__print_errors(service)

    def __install_sub_dependencies(self, path):
        lock_file_path = os.path.join(path, self.PARVUM_LOCK_FILE)
        json_file_path = os.path.join(path, self.PARVUM_JSON_FILE)

        if os.path.isfile(lock_file_path):
            self.__install_from_lock(lock_file_path)
        elif os.path.isfile(json_file_path):
            self.__install_from_json(json_file_path)

    def __get_service_compose_file(self, service_name, service):
        service_target_path = self.__format_service_target_path(service_name, service)
        compose_file = os.path.join(service_target_path, self.DEFAULT_SERVICE_COMPOSE_FILE)
        if not os.path.isfile(compose_file):
            return None

        return compose_file

    def __load_services_from_lock(self):
        lock_file = open(self.LOCK_FILE_PATH, "r")
        lock_file_data = lock_file.read()
        lock_file.close()

        return json.loads(lock_file_data)

    def __install_from_json(self, json_file_path=None):
        json_file = open(json_file_path if json_file_path is not None else self.JSON_FILE_PATH, "r")
        json_file_data = json_file.read()
        json_file.close()

        json_file_json = json.loads(json_file_data)

        if "services" not in json_file_json:
            return

        services_releases = []
        require_errors = []

        for service_name in json_file_json["services"]:
            if type(json_file_json["services"][service_name]) is str:
                version = json_file_json["services"][service_name]
            else:
                version = json_file_json["services"][service_name]["version"]

            release_buffer = self.__require_service(service_name, version)

            if release_buffer["error"] == self.ERR_NONE:
                services_releases.append(release_buffer)
            else:
                require_errors.append(release_buffer)

        for service in services_releases:
            self.__check_and_run_service_files(service)

        self.__format_json_file(services_releases)
        self.__format_lock_file(services_releases)

        for service in services_releases:
            self.__print_warns(service)

        for service in require_errors:
            self.__print_errors(service)

    def __install_from_lock(self, lock_file_path=None):
        lock_file = open(lock_file_path if lock_file_path is not None else self.LOCK_FILE_PATH, "r")
        lock_file_data = lock_file.read()
        lock_file.close()

        lock_file_json = json.loads(lock_file_data)

        self.__require_resolved_services(lock_file_json)

    def __require_resolved_services(self, services):
        for service_name in services:
            service = {
                "service": service_name,
                "release": services[service_name],
            }

            release_asset = self.__get_asset(service)
            self.__extract_release_asset(service_name, release_asset)

    def __format_json_file(self, services):
        json_file_data = ""
        if os.path.isfile(self.JSON_FILE_PATH):
            json_file = open(self.JSON_FILE_PATH, "r")
            json_file_data = json_file.read()
            json_file.close()

        if json_file_data:
            json_file_json = json.loads(json_file_data)
        else:
            json_file_json = {"services": {}}

        for service in services:
            if service['version_constraint'] is self.LATEST_RELEASE_IDENTIFIER:
                version = "^" + service["release"]["tag_name"]
            else:
                version = service['version_constraint']

            json_file_json['services'][service['service']] = version

        with open(self.JSON_FILE_PATH, 'w') as fp:
            json.dump(json_file_json, fp, indent=4)

    def __format_lock_file(self, services):
        lock_file_data = ""
        if os.path.isfile(self.LOCK_FILE_PATH):
            lock_file = open(self.LOCK_FILE_PATH, "r")
            lock_file_data = lock_file.read()
            lock_file.close()

        if lock_file_data:
            lock_file_json = json.loads(lock_file_data)
        else:
            lock_file_json = {}

        keys = ["id", "node_id", "html_url", "tarball_url", "zipball_url", "url", "tag_name", "published_at"]

        for service in services:
            lock_file_json[service["service"]] = {}
            for key in keys:
                lock_file_json[service["service"]][key] = service["release"][key]

        with open(self.LOCK_FILE_PATH, 'w') as fp:
            json.dump(lock_file_json, fp, indent=4)

    def __print_errors(self, service):
        message = ''
        if service["error"] == self.ERR_SERVICE_NOT_FOUND:
            message = 'service not found.'
        elif service["error"] == self.ERR_VERSION_NOT_FOUND:
            message = 'no version version matches with the constraint: !B' + service["version"] + '!R!r.'
        elif service["error"] == self.ERR_COULD_NOT_GET_RELEASES:
            message = 'cloud not get any releases.'

        print(formatex('!R' + LAMBDA_BASE_REPO + '/!B!r' + service['service'] + '!R!r: ' + message))

    def __print_warns(self, service):
        if service["warns"] & self.WARN_SETUP_SCRIPT_NOT_FOUND:
            print(formatex('!R' + LAMBDA_BASE_REPO + '/!B' + service['service'] + '!R: setup script not found.'))

        if service["warns"] & self.WARN_COMPOSE_NOT_FILE_FOUND:
            print(formatex('!R' + LAMBDA_BASE_REPO + '/!B' + service['service'] + '!R: compose file not found.'))

    def __check_and_run_service_files(self, service):
        warns = self.WARN_NONE
        setup_script = os.path.join(service["service_path"], self.DEFAULT_SERVICE_SETUP_SCRIPT)

        if os.path.isfile(setup_script):
            service["setup_script"] = setup_script
            os.chmod(setup_script, 0o755)
            print(run_read_sync(setup_script))
        else:
            warns |= self.WARN_SETUP_SCRIPT_NOT_FOUND

        compose_file = os.path.join(service["service_path"], self.DEFAULT_SERVICE_COMPOSE_FILE)

        if os.path.isfile(compose_file):
            service["compose_file"] = compose_file
        else:
            warns |= self.WARN_COMPOSE_NOT_FILE_FOUND

        service["warns"] = warns

    def __split_service_name_version(self, service):
        re_result = re.match(r"([^@]+)(?:@(.+))?", service)
        name = re_result.group(1)
        version_constraint = re_result.group(2)

        if version_constraint is None:
            version_constraint = self.LATEST_RELEASE_IDENTIFIER

        return name, version_constraint

    def __require_service(self, service, version_constraint):
        release = {
            "service": service,
            "version_constraint": version_constraint,
        }

        release.update(self.__get_release(service, version_constraint))

        if release["error"] > self.ERR_NONE:
            return release

        if self.__get_is_release_installed(release):
            return release

        release_asset = self.__get_asset(release)

        target_path = self.__extract_release_asset(service, release_asset)
        release["service_path"] = target_path

        self.__install_sub_dependencies(target_path)

        return release

    def __get_is_release_installed(self, release):
        release_path = os.path.join(self.DEFAULT_SERVICES_PATH, release['service'], release['release']['tag_name'])

        return os.path.isdir(release_path)

    def __get_release(self, service, version_constraint):
        try:
            self.gh.get_repo(service)
        except GHRequestError:
            return {
                "release": None,
                "error": self.ERR_SERVICE_NOT_FOUND,
                "warns": self.WARN_NONE,
            }

        release = None

        if version_constraint is self.LATEST_RELEASE_IDENTIFIER:
            try:
                return {
                    "release": self.gh.get_latest_release(service),
                    "error": self.ERR_NONE,
                    "warns": self.WARN_NONE,
                }
            except GHRequestError:
                return {
                    "release": None,
                    "error": self.ERR_VERSION_NOT_FOUND,
                    "warns": self.WARN_NONE,
                }

        releases = []
        if release is None:
            try:
                releases = self.gh.get_releases(service)
            except GHRequestError:
                return {
                    "release": None,
                    "error": self.ERR_COULD_NOT_GET_RELEASES,
                    "warns": self.WARN_NONE,
                }

        for release_buffer in releases:
            raw_version = release_buffer['tag_name']
            release_version = raw_version[1:] if raw_version.startswith('v') else raw_version

            if Spec(version_constraint).match(Version(release_version)):
                release = release_buffer
                break

        if release is None:
            return {
                "release": None,
                "error": self.ERR_VERSION_NOT_FOUND,
                "warns": self.WARN_NONE,
            }

        return {
            "release": release,
            "error": self.ERR_NONE,
            "warns": self.WARN_NONE,
        }

    def __get_asset(self, service_release):
        target_path = os.path.join(self.DEFAULT_SERVICES_PATH, service_release["service"])

        if not os.path.isdir(target_path):
            os.makedirs(target_path)

        target_file = os.path.join(target_path, str(service_release["release"]["id"]) + '.tar.gz')

        if os.path.isfile(target_file):
            return target_file

        response = self.gh.request('GET', service_release["release"]["tarball_url"])

        open(target_file, "wb").write(response.content)

        return target_file

    def __extract_release_asset(self, service, asset):
        tar = tarfile.open(asset)

        target_path = os.path.join(self.DEFAULT_SERVICES_PATH, service["service"])

        original_dest_folder = re.sub(r"/.*", "", tar.getnames()[0])
        extracted_target_path = os.path.join(target_path, original_dest_folder)
        new_target_path = self.__format_service_target_path(service["service"], service["release"])

        if not os.path.isdir(target_path):
            os.makedirs(target_path)

        if os.path.isdir(new_target_path):
            return new_target_path

        tar.extractall(target_path)
        os.rename(extracted_target_path, new_target_path)

        return new_target_path

    def __format_service_target_path(self, service_name, service):
        return os.path.join(self.DEFAULT_SERVICES_PATH, service_name, service["tag_name"])
