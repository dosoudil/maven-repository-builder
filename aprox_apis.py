from maven_repo_util import slashAtTheEnd

import httplib
import json
import logging
import urllib
import urlparse


class UrlRequester:

    def _request(self, method, url, params, data, headers):
        """
        Makes request defined by input params.

        :returns: instance of httplib.HTTPResponse
        """
        parsedUrl = urlparse.urlparse(url)
        protocol = parsedUrl[0]
        if params:
            encParams = urllib.urlencode(params)
        else:
            encParams = ""
        if protocol == 'http':
            connection = httplib.HTTPConnection(parsedUrl[1])
        else:
            connection = httplib.HTTPSConnection(parsedUrl[1])
        if not headers:
            headers = {}
        connection.request(method, parsedUrl[2] + "?" + encParams, data, headers)
        return connection.getresponse()

    def _getUrl(self, url, params=None, headers=None):
        return self._request("GET", url, params, None, headers)

    def _postUrl(self, url, params=None, data=None, headers=None):
        """
        Calls POST http request to the given URL.

        :returns: instance of httplib.HTTPResponse
        """
        return self._request("POST", url, params, data, headers)

    def _putUrl(self, url, params=None, data=None, headers=None):
        """
        Calls PUT http request to the given URL.

        :returns: instance of httplib.HTTPResponse
        """
        return self._request("PUT", url, params, data, headers)

    def _deleteUrl(self, url, headers=None):
        """
        Calls DELETE http request of the given URL.

        :returns: response status code
        """
        response = self._request("DELETE", url, None, None, headers)
        return response.status


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
        if response.status == 201:
            responseJson = json.loads(response.read())
            logging.info("Created AProx workspace with ID %s", responseJson["id"])
            return responseJson
        else:
            raise Exception("Failed to create new AProx workspace, status code %i, content: %s"
                            % (response.status, response.read()))

    def deleteWorkspace(self, wsid):
        """
        Deletes a specified workspace.

        :param wsid: workspace ID
        :returns: True if the workspace was deleted, False otherwise
        """
        strWsid = str(wsid)
        url = (self._aprox_url + self.API_PATH + "depgraph/ws/%s") % strWsid
        logging.info("Deleting AProx workspace with ID %s", strWsid)
        status = self._deleteUrl(url)
        if status == 200:
            logging.info("AProx workspace with ID %s was deleted", strWsid)
        else:
            logging.warning("An error occurred while deleting AProx workspace with ID %s, status code %i.",
                            strWsid, status)
        return status == 200

    def urlmap(self, wsid, sourceKey, gavs, allclassifiers, excludedSources, preset, resolve=True):
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
        :param excludedSources: list of excluded sources' keys
        :param preset: preset used while creating the urlmap
        :param resolve: flag to tell AProx to run resolve for given roots
        :returns: the requested urlmap
        """
        url = self._aprox_url + self.API_PATH + "depgraph/repo/urlmap"

        request = {}
        request["roots"] = gavs
        if allclassifiers:
            request["extras"] = [{"classifier": "*", "type": "*"}]
        request["workspaceId"] = wsid
        request["source"] = sourceKey
        if len(excludedSources):
            request["excludedSources"] = excludedSources
        request["preset"] = preset
        request["resolve"] = resolve
        data = json.dumps(request)

        logging.debug("Requesting urlmap with config '%s'", data)

        response = self._postUrl(url, data=data)

        if response.status == 200:
            logging.debug("AProx urlmap created")
            return json.loads(response.read())
        else:
            logging.warning("An error occurred while creating AProx urlmap, status code %i, content '%s'.",
                            response.status, response.read())
            return {}