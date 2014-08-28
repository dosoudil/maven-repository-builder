from maven_repo_util import slashAtTheEnd

import hashlib
import httplib
import json
import logging
import os
import urllib
import urlparse
from configuration import Configuration


class UrlRequester:

    def _request(self, method, url, params, data, headers):
        """
        Makes request defined by input params.

        :returns: instance of httplib.HTTPResponse
        """
        parsed_url = urlparse.urlparse(url)
        protocol = parsed_url[0]
        if params:
            encParams = urllib.urlencode(params)
        else:
            encParams = ""
        if protocol == 'http':
            connection = httplib.HTTPConnection(parsed_url[1])
        else:
            connection = httplib.HTTPSConnection(parsed_url[1])
        if not headers:
            headers = {}
        connection.request(method, parsed_url[2] + "?" + encParams, data, headers)
        response = connection.getresponse()
        if response.status in (301, 302):
            location = response.getheader("Location")
            parsed_loc = urlparse.urlparse(location)
            if not parsed_loc.scheme:
                target = urlparse.urlunparse([parsed_url.scheme, parsed_url.netloc, parsed_loc.path, parsed_loc.params,
                                              parsed_loc.query, parsed_loc.fragment])
            else:
                target = location
            return self._request(method, target, params, data, headers)
        else:
            return response

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
    CACHE_PATH = "cache"

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
            return True
        else:
            logging.warning("An error occurred while deleting AProx workspace with ID %s, status code %i.",
                            strWsid, status)
            return False

    def urlmap(self, wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds, resolve=True):
        """
        See urlmap_nocache() for method docs. This is caching version of the method.
        """
        cached = self.get_cached_urlmap(wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds,
                                        resolve)
        if cached:
            logging.info("Using cached version of AProx urlmap for roots %s", "-".join(gavs))
            return json.loads(cached)
        else:
            response = self.urlmap_response(wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds,
                                            resolve)
            if response != "{}":
                self.store_urlmap_cache(response, wsid, sourceKey, gavs, addclassifiers, excludedSources, preset,
                                        patcherIds, resolve)
            return json.loads(response)

    def urlmap_nocache(self, wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds, resolve=True):
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
        :param sourceKey: the AProx artifact source key, consisting of the source type and
                          its name of the form <{repository|deploy|group}:<name>>
        :param gavs: list of GAV as strings
        :param addclassifiers: list of dictionaries with structure {"type": "<type>", "classifier": "<classifier>"}, any
                               value can be replaced by a star to include all types/classifiers
        :param excludedSources: list of excluded sources' keys
        :param preset: preset used while creating the urlmap
        :param patcherIds: list of patcher ID strings for AProx
        :param resolve: flag to tell AProx to run resolve for given roots
        :returns: the requested urlmap
        """
        return json.loads(self.urlmap_response(wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds, resolve))

    def urlmap_response(self, wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds, resolve=True):
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
        :param sourceKey: the AProx artifact source key, consisting of the source type and
                          its name of the form <{repository|deploy|group}:<name>>
        :param gavs: list of GAV as strings
        :param addclassifiers: list of dictionaries with structure {"type": "<type>", "classifier": "<classifier>"}, any
                               value can be replaced by a star to include all types/classifiers
        :param excludedSources: list of excluded sources' keys
        :param preset: preset used while creating the urlmap
        :param patcherIds: list of patcher ID strings for AProx
        :param resolve: flag to tell AProx to run resolve for given roots
        :returns: the response string of the requested urlmap
        """
        url = self._aprox_url + self.API_PATH + "depgraph/repo/urlmap"

        request = {}
        if addclassifiers:
            if addclassifiers == Configuration.ALL_CLASSIFIERS_VALUE:
                request["extras"] = [{"classifier": "*", "type": "*"}]
            else:
                request["extras"] = addclassifiers
        request["workspaceId"] = wsid
        request["source"] = sourceKey
        if len(excludedSources):
            request["excludedSources"] = excludedSources
        request["resolve"] = resolve
        request["graphComposition"] = {"graphs": [{"roots": gavs, "preset": preset}]}
        if len(patcherIds):
            request["patcherIds"] = patcherIds
        data = json.dumps(request)

        logging.debug("Requesting urlmap with config '%s'", data)

        response = self._postUrl(url, data=data)

        if response.status == 200:
            responseContent = response.read()
            logging.debug("AProx urlmap created. Response content:\n%s", responseContent)
            return responseContent
        else:
            logging.warning("An error occurred while creating AProx urlmap, status code %i, content '%s'.",
                            response.status, response.read())
            return "{}"

    def get_cached_urlmap(self, wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds, resolve):
        """
        Gets cache urlmap response if exists for given parameters.

        :param wsid: AProx workspace ID
        :param sourceKey: the AProx artifact source key, consisting of the source type and
                          its name of the form <{repository|deploy|group}:<name>>
        :param gavs: list of GAV as strings
        :param addclassifiers: list of dictionaries with structure {"type": "<type>", "classifier": "<classifier>"}, any
                               value can be replaced by a star to include all types/classifiers
        :param excludedSources: list of excluded sources' keys
        :param preset: preset used while creating the urlmap
        :param patcherIds: list of patcher ID strings for AProx
        :param resolve: flag to tell AProx to run resolve for given roots
        :returns: the cached response or None if no cached response exists
        """
        cache_filename = self.get_cache_filename(sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds)
        if os.path.isfile(cache_filename):
            with open(cache_filename) as cache_file:
                return cache_file.read()
        else:
            logging.info("Cache file %s not found.", cache_filename)
            return None

    def store_urlmap_cache(self, response, wsid, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds,
                    resolve):
        """
        Stores urlmap response to cache.

        :param response: the response to store
        :param wsid: AProx workspace ID
        :param sourceKey: the AProx artifact source key, consisting of the source type and
                          its name of the form <{repository|deploy|group}:<name>>
        :param gavs: list of GAV as strings
        :param addclassifiers: list of dictionaries with structure {"type": "<type>", "classifier": "<classifier>"}, any
                               value can be replaced by a star to include all types/classifiers
        :param excludedSources: list of excluded sources' keys
        :param preset: preset used while creating the urlmap
        :param patcherIds: list of patcher ID strings for AProx
        :param resolve: flag to tell AProx to run resolve for given roots
        """
        cache_filename = self.get_cache_filename(sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds)
        if not os.path.exists(self.CACHE_PATH):
            os.makedirs(self.CACHE_PATH)
        with open(cache_filename, "w") as cache_file:
            cache_file.write(response)

    def get_cache_filename(self, sourceKey, gavs, addclassifiers, excludedSources, preset, patcherIds):
        """
        Creates a cache filename to use for urlmap request.

        :param sourceKey: the AProx artifact source key, consisting of the source type and
                          its name of the form <{repository|deploy|group}:<name>>
        :param gavs: list of GAV as strings
        :param addclassifiers: list of dictionaries with structure {"type": "<type>", "classifier": "<classifier>"}, any
                               value can be replaced by a star to include all types/classifiers
        :param excludedSources: list of excluded sources' keys
        :param preset: preset used while creating the urlmap
        :param patcherIds: list of patcher ID strings for AProx
        :param resolve: flag to tell AProx to run resolve for given roots
        """
        cache_filename = "%s_%s_%s_%s_%s_%s" % (sourceKey, "-".join(gavs), addclassifiers, "-".join(excludedSources),
                                               preset, "-".join(patcherIds))
        if len(cache_filename) > 250:
            sha256 = hashlib.sha256(cache_filename)
            cache_filename = "%s_%s" % ("-".join(gavs), sha256.hexdigest())
            if len(cache_filename) > 250:
                cache_filename = sha256.hexdigest()
        return "%s/%s.cache" % (self.CACHE_PATH, cache_filename)
