from maven_repo_util import slashAtTheEnd

import json
import logging
import requests


class UrlRequester:

    def _getRequestDict(self, params, data, headers):
        requestKwargs = {}

        if params:
            assert isinstance(
                params, dict), 'Params must be a dict, got %s' % repr(params)
            requestKwargs['params'] = params

        if headers:
            assert isinstance(
                headers, dict), 'headers must be a dict, got %s' % repr(headers)
            requestKwargs['headers'] = headers

        if data:
            requestKwargs['data'] = data

        return requestKwargs

    def _getUrl(self, url, params=None, headers=None):
        requestKwargs = self._getRequestDict(params, None, headers)
        return requests.get(url, **requestKwargs)

    def _postUrl(self, url, params=None, data=None, headers=None):
        requestKwargs = self._getRequestDict(params, data, headers)
        return requests.post(url, **requestKwargs)

    def _putUrl(self, url, params=None, data=None, headers=None):
        requestKwargs = self._getRequestDict(params, data, headers)
        return requests.put(url, **requestKwargs)

    def _deleteUrl(self, url, params=None, headers=None):
        requestKwargs = self._getRequestDict(params, None, headers)
        return requests.delete(url, **requestKwargs)


class AproxApi10(UrlRequester):
    """
    Class allowing to communicate with the AProx REST API v1.0.
    """

    API_PATH = "api/1.0/"

    def __init__(self, aprox_url):
        self._aprox_url = slashAtTheEnd(aprox_url)

    def createWorkspace(self):
        """
        Creates new workspace. Example of returned object:
            {
                "config": {
                    "forceVersions": true
                },
                "selectedVersions": {},
                "wildcardSelectedVersions": {},
                "id": "1",
                "open": true,
                "lastAccess": 1377090886682
            }

        :returns: created workspace structure as returned by AProx
        """
        url = self._aprox_url + self.API_PATH + "depgraph/ws/new"
        logging.info("Creating new AProx workspace")
        response = self._postUrl(url)
        if response.status_code == 201:
            responseJson = response.json()
            logging.info("Created AProx workspace with ID %s", responseJson["id"])
            return responseJson
        else:
            raise Exception("Failed to create new AProx workspace, status code %i, content: %s"
                            % (response.status_code, response.content))

    def deleteWorkspace(self, wsid):
        """
        Deletes a specified workspace.

        :param wsid: workspace ID
        """
        strWsid = str(wsid)
        url = (self._aprox_url + self.API_PATH + "depgraph/ws/%s") % strWsid
        logging.info("Deleting AProx workspace with ID %s", strWsid)
        response = self._deleteUrl(url)
        if response.status_code == 200:
            logging.info("AProx workspace with ID %s was deleted", strWsid)
        else:
            logging.warning("An error occured while deleting AProx workspace with ID %s, status code %i.",
                            strWsid, response.status_code)

    def urlmap(self, wsid, sourceKey, gavs, allclassifiers, preset="sob", resolve=True):
        """
        Requests creation of the urlmap. It creates the configfile, posts it to AProx server
        and process the result, which has following structure:
            {
                "group:artifact:1.0": {
                    "files": [
                        "artifact-1.0.pom",
                        "artifact-1.0.pom.md5",
                        "artifact-1.0.pom.sha1"
                    ],
                    "repoUrl": "http://maven.repo.org/repos/repo1/"
                },
                "group:artifact2:1.1": {
                    "files": [
                        "artifact2-1.1.pom",
                        "artifact2-1.1.pom.md5",
                        "artifact2-1.1.pom.sha1"
                        "artifact2-1.1.jar",
                        "artifact2-1.1.jar.md5",
                        "artifact2-1.1.jar.sha1"
                        "artifact2-1.1-sources.jar",
                        "artifact2-1.1-sources.jar.md5",
                        "artifact2-1.1-sources.jar.sha1"
                    ],
                    "repoUrl": "http://maven.repo.org/repos/repo1/"
                },
                ...
            }

        :param wsid: AProx workspace ID
        :param gavs: list of GAV as strings
        :param sourceKey: the AProx artifact source key, consisting of the source type and
                          its name of the form <{repository|deploy|group}:<name>>
        :param preset: preset used while creating the urlmap
        :param resolve: TODO
        :returns: the requested urlmap
        """
        url = self._aprox_url + self.API_PATH + "depgraph/repo/urlmap"

        request = {}
        request["roots"] = gavs
        # TODO: handle extras for allclassifiers = True
        request["workspaceId"] = wsid
        request["source"] = sourceKey
        request["preset"] = preset
        request["resolve"] = resolve
        data = json.dumps(request)

        logging.debug("Requesting urlmap with config '%s'", data)

        response = self._postUrl(url, data=data)

        if response.status_code == 200:
            logging.debug("AProx urlmap created")
            return response.json()
        else:
            logging.warning("An error occured while creating AProx urlmap, status code %i, content '%s'.",
                            response.status_code, response.content)
            return {}