import os
import json
import time
import requests
from glom import glom
from requests.exceptions import HTTPError
import shutil


class Registry:
    def __init__(self, gpg_public_key="None", gpg_keyid="None"):
        self.github_orga = os.getenv("github_orga", None)
        try:
            os.environ["gpg_public_key"].replace(r"\n", "\n") and os.environ[
                "gpg_keyid"
            ] and os.environ["go_os"] and os.environ["go_arch"] and os.environ[
                "server_name"
            ] and os.environ[
                "github_repo"
            ] and os.environ[
                "github_token"
            ] and os.environ[
                "github_max_release"
            ]
            self.dir_name = os.path.dirname(os.path.realpath(__file__)) + "/registry"
            self.gpg_public_key = os.environ["gpg_public_key"]
            self.gpg_keyid = os.environ["gpg_keyid"]
            self.go_os = os.environ["go_os"]
            self.server_name = os.environ["server_name"]
            self.go_arch = os.environ["go_arch"]
            self.github_repo = os.environ["github_repo"]
            self.github_token = os.environ["github_token"]
            self.github_max_release = os.environ["github_max_release"]
            self.release_tags = dict()
            self.release = dict()
            self.extension = "zip"
        except KeyError:
            print("Please set the environment variable gpg")
            exit(1)

    def request_github(self, url, accept, msg="-> request API github"):
        print(msg)
        headers = {
            "Accept": accept,
            "Authorization": "token " + self.github_token,
        }
        max_attempts = 3
        attempts = 1
        sleeptime = 0  # in seconds, no reason to continuously try if network is down

        while attempts < max_attempts:
            time.sleep(sleeptime)
            attempts += 1
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
            except HTTPError as http_err:
                print(f"HTTP error occurred: {http_err}")
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
            else:
                return response
        if attempts == max_attempts:
            print("You used the maximum number of attempts, sorry!")
            quit()

    def download_release_setInEnv(self):
        if not self.release_tags:
            print("Error with get_tags_release()")
            exit()
        for release_name in self.release:
            for tags in self.release[release_name]:
                print("   -> download assets for tags: " + tags)
                asset_id = self.release[release_name][tags].get("asset_id")
                asset_name = self.release[release_name][tags].get("asset_name")
                accept = "application/octet-stream"
                path_download = (
                    os.path.dirname(os.path.realpath(__file__))
                    + "/download/"
                    + release_name
                )
                os.makedirs(path_download, exist_ok=True)
                for i in range(0, len(asset_id)):
                    url = (
                        "https://api.github.com/repos/"
                        + release_name
                        + "/releases/assets/"
                        + str(asset_id[i])
                    )

                    ####################################
                    #  To uncomment for download providers
                    ################################

                    response = self.request_github(
                        url, accept, "   -> download: " + str(asset_name[i])
                    )
                    with open(path_download + "/" + asset_name[i], "wb") as outfile:
                        outfile.write(response.content)

    def get_release_setInEnv(self):
        try:
            l_release_name = self.github_repo.split(",")
            if len(l_release_name) <= 0:
                print("Error with split function")
                exit()

            for n in range(len(l_release_name)):
                print("-> get tags setInEnv " + str(n) + " for " + l_release_name[n])
                name_user = l_release_name[n].split("/")
                if name_user[0] == self.github_orga:
                    print(
                        "-> get " + l_release_name[n] + " for orga:" + self.github_orga
                    )
                    dict_get_tags_release = self.get_tags_release(l_release_name[n])
                else:
                    print("-> get " + l_release_name[n] + " for user:" + name_user[0])
                    dict_get_tags_release = self.get_tags_release(l_release_name[n])
                self.release_tags.update({l_release_name[n]: dict_get_tags_release})
            for n in range(len(l_release_name)):
                print("-> get assets setInEnv " + str(n) + " for " + l_release_name[n])
                dict_tags = dict()
                for tags_name in self.release_tags[l_release_name[n]]:
                    dict_assets = self.get_tags_assets(l_release_name[n], tags_name)
                    if dict_assets:
                        dict_tags.update({tags_name: dict_assets})
                self.release.update({l_release_name[n]: dict_tags})
        except ValueError:
            print("Error with split() function, check github_repo env vars...")
            exit()

    def get_tags_assets(self, release_name, tags_name):
        print("   -> get_assets for release: " + tags_name)
        path_download = os.path.dirname(os.path.realpath(__file__)) + "/download/"
        os.makedirs(path_download, exist_ok=True)
        accept = "none"
        url = (
            "https://api.github.com/repos/"
            + release_name
            + "/releases/tags/"
            + tags_name
        )
        response = self.request_github(url, accept, "   -> get_assets API request")
        with open(path_download + "release.json", "wb") as outfile:
            outfile.write(response.content)

        with open(path_download + "release.json") as readfile:
            data = json.load(readfile)
        spec = {"asset_id": ("assets", ["id"]), "asset_name": ("assets", ["name"])}
        dict_res = glom(data, spec)
        if len(dict_res.get("asset_id")) != 0 and dict_res.get("asset_id") != "none":
            if self.checkIfAssetHasRightFormat(dict_res.get("asset_name")):
                return dict_res
            else:
                print("You need to check the previous Step GoReleaser")
                return None
        else:
            print("You need to check the previous Step GoReleaser")
            exit()

    def get_tags_release(self, release_name):
        path_download = os.path.dirname(os.path.realpath(__file__)) + "/download/"
        os.makedirs(path_download, exist_ok=True)
        accept = "none"
        url = "https://api.github.com/repos/" + release_name + "/releases"
        response = self.request_github(url, accept, "-> get all tags for Repo")
        with open(path_download + "release.json", "wb") as outfile:
            outfile.write(response.content)

        with open(path_download + "release.json") as readfile:
            data = json.load(readfile)
        l_res = glom(data, (["tag_name"]))
        l_tag_name = []
        cp = 1
        for i in l_res:
            if cp <= int(self.github_max_release):
                cp += 1
                l_tag_name.append(i)
        if len(l_tag_name) != 0 and l_tag_name:
            return l_tag_name
        else:
            print("There is no release(s) on this Repo: " + release_name)
            exit()

    def download_release(self):
        print("## get release ##")
        self.get_release_setInEnv()
        print("## download release ##")
        self.download_release_setInEnv()

    def copy_release(self):
        # We copy release in registry
        for release_name in self.release:
            for tags in self.release[release_name]:
                str_search = "provider-"
                start = release_name.find(str_search) + len(str_search)
                provider_name = release_name[start:]
                path_download = (
                    os.path.dirname(os.path.realpath(__file__))
                    + "/download/"
                    + release_name
                    + "/"
                )
                file_provider = os.path.join(
                    path_download,
                    "terraform-provider-" + provider_name + "_" + tags[1:],
                )
                dir_registry = os.path.join(
                    self.dir_name, "terraform-provider-" + provider_name + "/"
                )
                file_shasum = file_provider + ".SHA256SUMS"
                file_shasum_sig = file_provider + ".SHA256SUMS.sig"
                l_os = self.go_os.split(",")
                l_arch = self.go_arch.split(",")
                for var_os in l_os:
                    for var_arch in l_arch:
                        src = (
                            file_provider
                            + "_"
                            + var_os
                            + "_"
                            + var_arch
                            + "."
                            + self.extension
                        )
                        dst = dir_registry + var_os + "/" + var_arch
                        if os.path.isfile(src):
                            shutil.copy2(src, dst)
                        else:
                            print(
                                "-> Provider Release: "
                                + provider_name
                                + " Is not available for this kind of Architecture var_os:["
                                + var_os
                                + "] var_arch:["
                                + var_arch
                                + "]"
                            )
                        shutil.copy2(file_shasum, dst)
                        shutil.copy2(file_shasum_sig, dst)

    def get_shasum(self, release_name, release_tag, var_os, var_arch):
        print("## get shasum ##")
        path_download = (
            os.path.dirname(os.path.realpath(__file__)) + "/download/" + release_name
        )
        str_search = "provider-"
        start = release_name.find(str_search) + len(str_search)
        provider_name = release_name[start:]
        name_shasum_file = os.path.join(
            path_download,
            "terraform-provider-"
            + provider_name
            + "_"
            + release_tag[1:]
            + ".SHA256SUMS",
        )
        if os.path.isfile(name_shasum_file):
            print("-> shasum file exist")
        else:
            print("File not exist")
            exit()
        try:
            with open(name_shasum_file, "r") as outfile:
                for line in outfile:
                    if var_os in line and var_arch in line:
                        shasum = line.split()
                        return shasum[0]
                return (
                    "the shasum file is missing for: "
                    + provider_name
                    + " var_os: "
                    + var_os
                    + " var_arch: "
                    + var_arch
                )

        except IOError:
            print("Error Opening sha256sum File")
        if not shasum[0]:
            return False

    def create_directory(self):
        print("-> create directory name")
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name, exist_ok=True)
        if not os.path.exists(self.dir_name + "/.well-known"):
            os.mkdir(os.path.join(self.dir_name, ".well-known"))

        l_release_name = self.github_repo.split(",")
        for release_name in l_release_name:
            str_search = "provider-"
            start = release_name.find(str_search) + len(str_search)
            provider_name = release_name[start:]
            dir_provider = os.path.join(
                self.dir_name, "terraform-provider-" + provider_name
            )
            if not os.path.exists(dir_provider):
                os.makedirs(dir_provider, exist_ok=True)
            try:
                l_os = self.go_os.split(",")
                l_arch = self.go_arch.split(",")
                for var_os in l_os:
                    os_dirertory = dir_provider + "/" + var_os

                    for var_arch in l_arch:
                        arch_dirertory = os_dirertory + "/" + var_arch
                        os.makedirs(arch_dirertory, exist_ok=True)
            except ValueError:
                print("Error with split function")
            provider_name_dir = (
                self.dir_name + "/terraform/providers/v1/dkt/" + provider_name
            )
            if not os.path.exists(provider_name_dir):
                os.makedirs(provider_name_dir, exist_ok=True)
            for release_tag in self.release[release_name]:
                print("-> create directory version " + release_tag[1:])
                dir_provider_version = (
                    provider_name_dir + "/" + release_tag[1:] + "/download"
                )
                if not os.path.exists(dir_provider_version):
                    os.makedirs(dir_provider_version, exist_ok=True)

                l_os = self.go_os.split(",")
                for var_os in l_os:
                    os_dirertory = dir_provider_version + "/" + var_os
                    if not os.path.exists(os_dirertory):
                        os.makedirs(os_dirertory, exist_ok=True)

    def generate_arch_file(self):
        print("-> generate arch File")
        l_release_name = self.github_repo.split(",")
        for release_name in l_release_name:
            str_search = "provider-"
            start = release_name.find(str_search) + len(str_search)
            provider_name = release_name[start:]
            file_json_arch = dict()
            provider_name_dir = (
                self.dir_name + "/terraform/providers/v1/dkt/" + provider_name
            )
            for release_tag in self.release[release_name]:
                dir_provider_version = (
                    provider_name_dir + "/" + release_tag[1:] + "/download"
                )
                try:
                    l_os = self.go_os.split(",")
                    l_arch = self.go_arch.split(",")
                    for var_os in l_os:
                        os.makedirs(dir_provider_version + "/" + var_os, exist_ok=True)
                        for var_arch in l_arch:
                            arch_file = (
                                dir_provider_version + "/" + var_os + "/" + var_arch
                            )
                            file_json_arch.update({"protocols": ["4.0", "5.1"]})
                            file_json_arch.update({"os": var_os})
                            file_json_arch.update({"arch": var_arch})
                            url_base = (
                                "https://"
                                + self.server_name
                                + "/terraform-provider-"
                                + provider_name
                                + "/"
                                + var_os
                                + "/"
                                + var_arch
                                + "/"
                            )
                            file_name_base = (
                                "terraform-provider-"
                                + provider_name
                                + "_"
                                + release_tag[1:]
                            )
                            filename = (
                                file_name_base
                                + "_"
                                + var_os
                                + "_"
                                + var_arch
                                + "."
                                + self.extension
                            )
                            shasums_url = file_name_base + ".SHA256SUMS"
                            shasums_signature_url = shasums_url + ".sig"
                            file_json_arch.update({"filename": filename})
                            download_url = url_base + filename
                            shasums_url = url_base + shasums_url
                            shasums_signature_url = url_base + shasums_signature_url
                            file_json_arch.update({"download_url": download_url})
                            file_json_arch.update({"shasums_url": shasums_url})
                            file_json_arch.update(
                                {"shasums_signature_url": shasums_signature_url}
                            )
                            file_json_arch.update(
                                {
                                    "shasum": self.get_shasum(
                                        release_name, release_tag, var_os, var_arch
                                    )
                                }
                            )
                            gpg_public_keys = list()
                            signing_keys = {"gpg_public_keys": gpg_public_keys}
                            entry_gpg_public_keys = {"key_id": self.gpg_keyid}
                            entry_gpg_public_keys.update(
                                {
                                    "ascii_armor": self.gpg_public_key.replace(
                                        r"\n", "\n"
                                    ),
                                }
                            )
                            gpg_public_keys.append(entry_gpg_public_keys)
                            file_json_arch.update({"signing_keys": signing_keys})
                            try:
                                with open(arch_file, "w") as outfile:
                                    json.dump(file_json_arch, outfile, indent=1)
                            except IOError:
                                print("Error creating File Arch Json")

                except ValueError:
                    print("Error with split function")
                    exit()

    def checkIfAssetHasRightFormat(self, asset_name):
        print("   -> Check If Asset has Right Format")
        cp = 0
        for fullstring in asset_name:
            if fullstring.find("SHA256SUMS.sig") != -1:
                cp += 1
        if cp >= 1:
            return True
        else:
            print("   -> This Asset has not the Right Format !!!")
            return False

    def generate_terraformjson(self):
        print("-> generate terraform.json")
        dict_terraform = dict()
        dict_terraform.update({"providers.v1": "/terraform/providers/v1/"})
        try:
            with open(
                self.dir_name + "/" + ".well-known" + "/terraform.json", "w"
            ) as outfile:
                json.dump(dict_terraform, outfile, indent=1)
        except IOError:
            print("Error creating Terraform Json File")

    def generate_versions(self):
        print("-> generate versions")
        l_release_name = self.github_repo.split(",")
        for release_name in l_release_name:
            str_search = "provider-"
            start = release_name.find(str_search) + len(str_search)
            provider_name = release_name[start:]
            provider_name_dir = (
                self.dir_name + "/terraform/providers/v1/dkt/" + provider_name
            )
            try:
                l_os = self.go_os.split(",")
                l_arch = self.go_arch.split(",")
                list_platforms = list()
                for os in l_os:
                    for arch in l_arch:
                        dict_p = {"os": os, "arch": arch}
                        list_platforms.append(dict_p)
                dict_versions = dict()
                list_versions = list()
                for release_tag in self.release[release_name]:
                    dict_version = {"version": release_tag[1:]}
                    dict_version.update({"protocols": ["4.0", "5.1"]})
                    dict_version.update({"platforms": list_platforms})
                    list_versions.append(dict_version)
                dict_versions.update({"versions": list_versions})
                try:
                    with open(provider_name_dir + "/versions", "w") as outfile:
                        json.dump(dict_versions, outfile, indent=1)
                except IOError:
                    print("Error creating Versions File")
            except ValueError:
                print("Error in function split")

    def generate_release(self):
        print(os.path.dirname(os.path.realpath(__file__)))
        self.download_release()
        print("## generate directory ##")
        self.create_directory()
        print("## generate files ##")
        self.generate_versions()  # file versions
        self.generate_terraformjson()  # file terraform.json
        self.generate_arch_file()  # file amd64
        print("## copy release ##")
        self.copy_release()


rel = Registry()
rel.generate_release()
