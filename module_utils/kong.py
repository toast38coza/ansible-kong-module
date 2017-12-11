import requests


class Kong(object):

    # List of API resources the library supports
    resources = [
        'status',
        'consumers',
        'apis',
        'plugins'
    ]

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

        if resource not in self.resources:
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

    @property
    def status(self):
        url = self._url('status')
        r = requests.get(url)
        r.raise_for_status()

        return r.json()

    @property
    def healthy(self):
        return self.status.get('database', {}).get('reachable', False)

    # --- Split off into API subclass

    def api_list(self):
        return self._get('apis', None)

    def api_get(self, name):
        try:
            r = self._get('apis', name)
        except requests.HTTPError:
            return None
        else:
            return r

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
            # Kong API expects comma-separated values
            if isinstance(hosts, list):
                hosts = ','.join(hosts)

            data['hosts'] = hosts

        if uris is not None:
            # Kong API expects comma-separated values
            if isinstance(uris, list):
                uris = ','.join(uris)

            data['uris'] = uris

        if methods is not None:
            # Kong API expects comma-separated values
            if isinstance(methods, list):
                methods = ','.join(methods)

            data['methods'] = methods

        # check if the API is already defined in Kong
        if self.api_get(name):
            # patch the resource at /apis/{name}
            r = self._patch('apis', name, data)
        else:
            # post new API to the root of /apis
            r = self._post('apis', None, data)

        return r

    def api_delete(self, name):
        """
        Delete the API if it exists.
        :param name: name of the API
        :type name: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.api_get(name):
            return self._delete('apis', name)

        return False
