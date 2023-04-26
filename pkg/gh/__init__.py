import os.path as path

import requests
import yaml

from pkg.contants import GH_CACHE_DIR

GH_HOST_FILE = path.join(GH_CACHE_DIR, 'hosts.yml')


class GH:
    def __init__(self, org):
        self.org = org
        self.oauth_token = self.get_oauth_token()
        self.base_url = 'https://api.github.com'
        self.base_headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + self.oauth_token,
            'X-GitHub-Api-Version': '2022-11-28',
        }
        self.check_user()

    def get_oauth_token(self):
        yaml_config = self.load_yaml()

        if 'github.com' not in yaml_config:
            raise GHConfigError

        if 'oauth_token' not in yaml_config['github.com']:
            raise GHConfigError

        return yaml_config['github.com']['oauth_token']

    @staticmethod
    def load_yaml():
        if not path.isfile(GH_HOST_FILE):
            return {}

        with open(GH_HOST_FILE, 'r') as stream:
            hosts_config = yaml.safe_load(stream)

        return hosts_config

    def check_user(self):
        try:
            requests.get(self.base_url + '/orgs/' + self.org + '/repos', headers=self.base_headers)
        except Exception:
            raise GHInvalidToken

    def get_repos(self):
        response = requests.get(self.base_url + '/orgs/' + self.org + '/repos', headers=self.base_headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting repo list", response.json()['message'], response.status_code)

        return response.json()

    def get_repo(self, repo):
        response = requests.get(self.base_url + '/repos/' + self.org + '/' + repo, headers=self.base_headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting repository", response.json()['message'], response.status_code)

        return response.json()

    def get_release(self, repo, tag):
        response = requests.get(self.base_url + '/repos/' + self.org + '/' + repo + '/releases/' + tag,
                                headers=self.base_headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting latest release", response.json()['message'], response.status_code)

        return response.json()

    def get_latest_release(self, repo):
        response = requests.get(self.base_url + '/repos/' + self.org + '/' + repo + '/releases/latest',
                                headers=self.base_headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting latest release", response.json()['message'], response.status_code)

        return response.json()

    def get_releases(self, repo):
        response = requests.get(self.base_url + '/repos/' + self.org + '/' + repo + '/releases',
                                headers=self.base_headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting releases", response.json()['message'], response.status_code)

        return response.json()

    def request(self, method, url, headers=None):
        if headers is None:
            headers = {}

        return requests.request(method, url, headers=headers | self.base_headers)

    def get_files(self, repo, ref="main"):
        response = requests.get(self.base_url + '/repos/' + self.org + '/' + repo + '/contents',
                                headers=self.base_headers,
                                params={
                                    "ref": ref
                                })

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting file", response.json()['message'], response.status_code)

        return response.json()

    def get_file(self, repo, file_name, ref="main"):
        response = requests.get(self.base_url + '/repos/' + self.org + '/' + repo + '/contents/' + file_name,
                                headers=self.base_headers,
                                params={
                                    "ref": ref
                                })

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting file", response.json()['message'], response.status_code)

        return response.json()

    def get_blob(self, url):
        headers = self.base_headers.copy()
        headers["Accept"] = "application/vnd.github.v4.raw"
        response = requests.get(url, headers=headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting file", response.json()['message'], response.status_code)

        return response.content.decode()

    def get_asset(self, url):
        headers = self.base_headers.copy()
        headers["Accept"] = "application/octet-stream"
        response = requests.get(url, headers=headers)

        if response.status_code > requests.codes.ok:
            raise GHRequestError("Error getting file", response.json()['message'], response.status_code)

        return response.content.decode()


class GHConfigError(BaseException):
    def __init__(self):
        self.message = "Cannot get GH config"


class GHInvalidToken(BaseException):
    def __init__(self):
        self.message = "Invalid GH token"


class GHRequestError(Exception):
    def __init__(self, message, gh_message, code):
        self.message = message + '. ' + gh_message + ' (' + str(code) + ')'
        super().__init__(self.message)
