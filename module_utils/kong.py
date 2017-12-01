from distutils.version import StrictVersion

import requests


class Kong(object):

    consumers = 'consumers'
    apis = 'apis'
    plugins = 'plugins'

    def __init__(self, base_url, auth_user=None, auth_pass=None):

        self.base_url = base_url

        self.auth = None

        # set basic auth tuple if credentials given
        if auth_user is not None and auth_pass is not None:
            self.auth = (auth_user, auth_pass)

    def _get(self, resource, action):
        """
        Execute GET request using the resource and action.
        """
        url = self._url(resource, action)

        r = requests.get(url, auth=self.auth)

        # Expect 200 OK
        r.raise_for_status()

        return r.json()

    def _post(self, resource, action, data):
        """
        Execute POST request using the resource, action and payload.
        """
        url = self._url(resource, action)

        r = requests.post(url, data=data, auth=self.auth)

        if r.status_code != requests.codes.created:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes.created))

        return r.json()

    def _patch(self, resource, action, data):
        """
        Execute PATCH request using the resource, action and payload.
        """
        url = self._url(resource, action)

        r = requests.patch(url, data=data, auth=self.auth)

        # Expect 200 OK
        r.raise_for_status()

        return r.json()

    def _delete(self, resource, action):
        """
        Execute DELETE request using the resource and action.
        """
        url = self._url(resource, action)

        r = requests.delete(url, auth=self.auth)

        if r.status_code != requests.codes.no_content:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes.no_content))

        return True

    def _url(self, resource, action=None):
        """
        Assemble a URL based on the type of resource and the action.
        """

        if resource not in [Kong.consumers, Kong.apis, Kong.plugins]:
            raise ValueError("Resource '{}' is not consumers, apis or plugins".format(resource))

        # use different format string for a url with action segment
        if action is None:
            return '{}/{}'.format(self.base_url, resource)

        return '{}/{}/{}'.format(self.base_url, resource, action)

    @property
    def version(self):
        r = requests.get(self.base_url)

        r.raise_for_status()

        return r.json().get('version', None)


    # --- Split off into API subclass

    def _api_exists(self, name):
        """
        Query the Kong API to check if a certain API exists.
        """

        try:
            self.api_get(name)
        except requests.HTTPError:
            return False
        return True

    def api_list(self):
        return self._get(Kong.apis, None)

    def api_get(self, name):
        return self._get(Kong.apis, name)

    def api_apply(self, name, upstream_url, hosts=None, uris=None, methods=None, strip_uri=False,
                  preserve_host=False):

        if hosts is None and uris is None and methods is None:
            raise ValueError('Need at least one of hosts, uris or methods.')

        if name is None:
            raise ValueError('name needs to be specified.')

        if upstream_url is None:
            raise ValueError('upstream_url needs to be specified.')

        data = {
            'name': name,
            'upstream_url': upstream_url,
            'strip_uri': strip_uri,
            'preserve_host': preserve_host,
            'hosts': hosts
        }

        if hosts is not None:
            data['hosts'] = hosts

        if uris is not None:
            data['uris'] = uris

        if methods is not None:
            data['methods'] = methods

        # check if the API is already defined in Kong
        if self._api_exists(name):
            # patch the resource at /apis/{name}
            r = self._patch(Kong.apis, name, data)
        else:
            # post new API to the root of /apis
            r = self._post(Kong.apis, None, data)

        return r

    def api_delete(self, name):
        """
        Delete the API if it exists.
        :param name: name of the API
        :type name: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self._api_exists(name):
            return self._delete(Kong.apis, name)

        return False
