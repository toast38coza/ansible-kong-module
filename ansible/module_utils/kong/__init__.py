"""
ansible.module_utils.kong implements the HTTP calls to the Kong Admin API.

:authors: Timo Beckers
:license: MIT
"""

import requests
from ansible.module_utils.kong.error import raise_for_error


class Kong(object):
    """Kong is a superclass that implements requests to the Kong API."""

    # List of API resources the library supports
    resources = [
        'status',
        'services',
        'routes',
        'plugins',
        'consumers',
        'certificates',
    ]

    def __init__(self, base_url, auth_user=None, auth_pass=None, ping=True):
        """
        Initialize a Kong object.

        Requires both `auth_user` and `auth_pass` to be set for the API client
        to perform password authentication to the Kong API.

        :param base_url: base URL of the Kong API endpoint
        :type base_url: str
        :param auth_user: user for basic authentication to the admin API
        :type auth_user: str
        :param auth_pass: password for basic authentication to the admin API
        :type auth_pass: str
        :param ping: whether or not to call /status on the admin API upon init
        :type ping: bool
        :return: None
        """
        self.base_url = base_url

        self.auth = None

        # set basic auth tuple if credentials given
        if auth_user is not None and auth_pass is not None:
            self.auth = (auth_user, auth_pass)

        # self-check by making status call to Kong
        if ping and self.status:
            return

    def _get(self, uri):
        """
        Execute a GET request on the given URI.

        The base URL gets automatically appended.

        :param uri: the URI of the request
        :type uri: str
        :return: JSON-parsed payload of the request
        :rtype: dict
        """
        url = self._url(uri)

        r = requests.get(url, auth=self.auth)

        # Expect 200 OK
        raise_for_error(r)

        return r.json()

    def _get_multipart(self, uri):
        """
        Execute a multipart GET request on the given URI.

        Follows any URLs sent in the 'next' field of the response.
        Returns a joined list of objects in the 'data' fields of all requests.

        :param uri: the URI of the request
        :type uri: str
        :return: JSON-parsed payload of the request
        :rtype: dict
        """
        # The initial request does not have a hostname. Payload URLs sent
        # in the 'next' key in the response are fully qualified.
        url = self._url(uri)

        out = []

        while url is not None:

            r = requests.get(url, auth=self.auth)
            raise_for_error(r)

            p = r.json()

            # Check if the response contains 'data' key.
            data = p.get('data', None)
            if data is None:
                raise Exception(
                    "Expected 'data' key in multipart response: {}".format(p))

            # Extend output list with data objects.
            out.extend(data)

            # Set the URL for the next request.
            url = p.get('next', None)

        return out

    def _post(self, uri, data=None):
        """
        Execute a POST request on the given URI.

        The endpoint must return 201 Created, or an exception is raised.
        Any Kong schema errors are raised as KongError.

        :param uri: the URI of the request
        :type uri: str
        :param data: dictionary to send as JSON-encoded body
        :type data: dict
        :return: JSON-parsed payload of the request
        :rtype: dict
        """
        url = self._url(uri)

        r = requests.post(url, json=data, auth=self.auth)

        raise_for_error(r)

        if r.status_code == requests.codes['created']:
            return r.json()
        else:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes['created']))

    def _patch(self, uri, data=None):
        """
        Execute a PATCH request on the given URI.

        Any Kong schema errors are raised as KongError.

        :param uri: the URI of the request
        :type uri: str
        :param data: dictionary to send as JSON-encoded body
        :type data: dict
        :return: JSON-parsed payload of the request
        :rtype: dict
        """
        url = self._url(uri)

        r = requests.patch(url, json=data, auth=self.auth)

        raise_for_error(r)

        return r.json()

    def _put(self, uri, data=None):
        """
        Execute a PUT request using the given URI.

        The endpoint must return 201 Created, or an exception is raised.
        Any Kong schema errors are raised as KongError.

        :param uri: the URI of the request
        :type uri: str
        :param data: dictionary to send as JSON-encoded body
        :type data: dict
        :return: JSON-parsed payload of the request
        :rtype: dict
        """
        url = self._url(uri)

        r = requests.put(url, data=data, auth=self.auth)

        raise_for_error(r)

        if r.status_code == requests.codes['created']:
            return True

        # Report no change
        return False

    def _delete(self, uri):
        """
        Execute a DELETE request using the given URI.

        The endpoint must return 204 No Content, or an exception is raised.
        Any Kong schema errors are raised as KongError.

        :param uri: the URI of the request
        :type uri: str
        :return: True
        :rtype: bool
        """
        url = self._url(uri)

        r = requests.delete(url, auth=self.auth)

        raise_for_error(r)

        if r.status_code != requests.codes['no_content']:
            raise Exception('Unexpected HTTP code {}, expected {}'
                            .format(r.status_code, requests.codes['no_content']))

        return True

    def _url(self, *args):
        """
        Assemble a fully-qualified URL based on Kong.base_url and URI segments.

        The first element in the list must appear in Kong.resources.
        None entries are trimmed from args.

        :param *args: list of URI segments
        :type *args: list
        :return: the base_url extended by the given URI segments
        :rtype str
        """
        # Tolerate the first argument being a list, step into it
        if isinstance(args[0], (list, tuple)):
            args = args[0]

        # Remove None entries from args
        args = [x for x in args if x is not None]

        # Just return the base url if no arguments are given
        if not args:
            return self.base_url

        resource = args[0]

        if resource not in self.resources:
            raise ValueError("Resource '{}' none of {}".format(
                resource, self.resources))

        url = [self.base_url]
        url.extend(args)

        return '/'.join(url)

    @property
    def version(self):
        """Get the version of the connected Kong instance."""
        r = requests.get(self.base_url)
        r.raise_for_status()

        return r.json().get('version', None)

    @property
    def status(self):
        """Call the /status endpoint on the connected Kong instance."""
        r = requests.get(self._url('status'))
        r.raise_for_status()

        return r.json()

    @property
    def healthy(self):
        """Kong database reachability health check."""
        return self.status.get('database', {}).get('reachable', False)
