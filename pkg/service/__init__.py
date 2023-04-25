import os
import shutil

from pkg.contants import LAMBDA_BASE_REPO, DEFAULT_SERVICES_PATH, LATEST_RELEASE_IDENTIFIER
from pkg.gh import GH, GHRequestError
from semantic_version import Version, NpmSpec

from pkg.service.release import Release


class Service:
    def __init__(self, name):
        self.__gh = GH(LAMBDA_BASE_REPO)
        self.__name = name
        self.__releases = []
        self.__release: Release | None = None

    def name(self):
        return self.__name

    def fetch_service(self):
        try:
            self.__gh.get_repo(self.__name)
        except GHRequestError:
            raise ServiceNotFound(self.__name)

    def releases(self):
        if not self.__releases:
            releases_raw = self.__gh.get_releases(self.__name)

            for release_raw in releases_raw:
                release_raw.update({"service": self, "latest": False, "dependencies": {}})
                self.__releases.append(Release(release_raw))

            try:
                latest_release = Release(self.__gh.get_latest_release(self.__name))

                for _release in self.__releases:
                    if _release.id() == latest_release.id():
                        _release.set_latest()
            except GHRequestError:
                pass

        return self.__releases

    def latest_release(self):
        latest = False

        for _release in self.releases():
            if _release.is_latest():
                latest = _release
                break

        return latest

    def match_release(self, version_constraint: str):
        _release = None
        if version_constraint == LATEST_RELEASE_IDENTIFIER:
            return self.latest_release()

        for release_buffer in self.releases():
            raw_version = release_buffer.version()
            release_version = raw_version[1:] if raw_version.startswith('v') else raw_version

            if Version(release_version) in NpmSpec(version_constraint):
                _release = release_buffer

                break

        if _release is None:
            raise ReleaseNotFound(self.__name, version_constraint)

        self.__release = _release

        return self

    def get_release(self) -> Release | None:
        return self.__release

    def prune(self):
        if os.path.exists(self.target_service_path()):
            shutil.rmtree(self.target_service_path())

    def target_service_path(self):
        return os.path.join(DEFAULT_SERVICES_PATH, self.name())


class ServiceNotFound(BaseException):
    def __init__(self, service_name):
        self.name = service_name


class ReleaseNotFound(BaseException):
    def __init__(self, service_name, version_constraint):
        self.service_name = service_name
        self.version_constraint = version_constraint
