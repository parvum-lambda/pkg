import json
import os

from pkg.contants import LAMBDA_BASE_REPO, DEFAULT_SERVICES_PATH, DEFAULT_COMPOSE_FILE_ASSET_LABEL, \
    DEFAULT_SERVICE_COMPOSE_FILE, PARVUM_JSON_FILE, PARVUM_LOCK_FILE
from pkg.gh import GH, GHRequestError


class Release:
    def __init__(self, data):
        self.__release_data = {
            "id": 0,
            "url": "",
            "node_id": "",
            "tag_name": "",
            "target_commitish": "",
            "service": None,
            "name": "",
            "prerelease": False,
            "latest": False,
            "created_at": "",
            "published_at": "",
            "tarball_url": "",
            "zipball_url": "",
            "assets": [],
            "dependencies": {},
        }
        self.__gh = GH(LAMBDA_BASE_REPO)
        self.__release_data = self.__format_data(data)
        self.__fetch_dependencies()

    def __format_data(self, data):
        release_keys = list(self.__release_data.keys())
        data_buffer = {}

        for key in release_keys:
            data_buffer[key] = data[key]

        return data_buffer

    def __fetch_dependencies(self):
        file = None

        try:
            file = self.__gh.get_file(self.service().name(), PARVUM_LOCK_FILE, self.tag_name())
        except GHRequestError:
            pass

        if file is None:
            try:
                file = self.__gh.get_file(self.service().name(), PARVUM_JSON_FILE, self.tag_name())
            except GHRequestError:
                pass

        if file is None:
            return

        blob = None

        try:
            blob = self.__gh.get_blob(file["git_url"])
        except GHRequestError:
            pass

        if blob is None:
            return

        parvum_file_data = json.loads(blob)

        if 'services' not in parvum_file_data:
            services_dependencies = {}

            for service in parvum_file_data:
                version = parvum_file_data[service]['tag_name'][1:]

                services_dependencies.update({
                    service: version,
                })

            self.__release_data["dependencies"].update(services_dependencies)
        else:
            services_dependencies = {}

            for service in parvum_file_data:
                version = parvum_file_data[service]

                services_dependencies.update({
                    service: version,
                })

            self.__release_data["dependencies"].update(services_dependencies)

    def id(self):
        return self.__release_data["id"]

    def service(self):
        return self.__release_data["service"]

    def tag_name(self):
        return self.__release_data["tag_name"]

    def version(self):
        return self.__release_data["tag_name"][1:]

    def tarball_url(self):
        return self.__release_data["tarball_url"]

    def set_latest(self):
        self.__release_data["latest"] = True

        return self

    def is_latest(self):
        return self.__release_data["latest"]

    def dependencies(self):
        return self.__release_data["dependencies"]

    def data(self):
        data = {}
        excluded_keys = ["service", "dependencies"]

        for data_key in self.__release_data:
            if data_key not in excluded_keys:
                data[data_key] = self.__release_data[data_key]

        return data

    def target_service_path(self):
        return os.path.join(DEFAULT_SERVICES_PATH, self.service().name(), self.tag_name())

    def target_compose_file(self):
        return os.path.join(self.target_service_path(), DEFAULT_SERVICE_COMPOSE_FILE)

    def install(self):
        self.__download_compose_file_asset()

    def __download_compose_file_asset(self):
        compose_asset = None

        for asset in self.__release_data["assets"]:
            if asset["label"] == DEFAULT_COMPOSE_FILE_ASSET_LABEL:
                compose_asset = asset

        if compose_asset is None:
            raise BaseException(self.service().name() + ': release asset not found')

        target_path = self.target_service_path()

        if not os.path.isdir(target_path):
            os.makedirs(target_path)

        target_file = os.path.join(target_path, compose_asset['name'])

        if os.path.isfile(target_file):
            return target_file

        response = self.__gh.get_asset(compose_asset["url"])

        open(target_file, "wb").write(response.encode())

        return target_file
