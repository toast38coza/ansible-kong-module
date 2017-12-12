import requests


class Kong(object):

    # List of API resources the library supports
    resources = [
        'status',
        'consumers',
        'apis',
        'plugins'
    ]

    def __init__(self, base_url, auth_user=None, auth_pass=None, ping=True):

        self.base_url = base_url

        self.auth = None

        # set basic auth tuple if credentials given
        if auth_user is not None and auth_pass is not None:
            self.auth = (auth_user, auth_pass)

        # self-check by making status call to Kong
        if ping and self.status:
            return

    def _get(self, resource, action=None, params=None):
        """
        Execute GET request using the resource and action.
        """
        url = self._url(resource, action)

        r = requests.get(url, params=params, auth=self.auth)

        # Expect 200 OK
        r.raise_for_status()

        return r.json()

    def _post(self, resource, action=None, data=None):
        """
        Execute POST request using the resource, action and payload.
        """
        url = self._url(resource, action)

        r = requests.post(url, data=data, auth=self.auth)

        if r.status_code != requests.codes.created:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes.created))

        return r.json()

    def _patch(self, resource, action=None, data=None):
        """
        Execute PATCH request using the resource, action and payload.
        """
        url = self._url(resource, action)

        r = requests.patch(url, data=data, auth=self.auth)

        # Expect 200 OK
        r.raise_for_status()

        return r.json()

    def _put(self, resource, action=None, data=None):
        """
        Execute PUT request using the resource, action and payload.
        """
        url = self._url(resource, action)

        r = requests.put(url, data=data, auth=self.auth)

        if r.status_code == requests.codes.created:
            return True

        # Raise if status is not 200 OK
        r.raise_for_status()

        # Report no change
        return False

    def _delete(self, resource, action=None):
        """
        Execute DELETE request using the resource and action.
        """
        url = self._url(resource, action)

        r = requests.delete(url, auth=self.auth)

        if r.status_code != requests.codes.no_content:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes.no_content))

        return True

    def _url(self, *args):
        """
        Assemble a URL based on the base_url with a URI joined by slashes.
        """

        # Just return the base url if no arguments are given
        if not args:
            return self.base_url

        resource = args[0]

        if resource not in self.resources:
            raise ValueError("Resource '{}' none of {}".format(resource, self.resources))

        url = [self.base_url]
        url.extend(args)

        return '/'.join(url)

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
