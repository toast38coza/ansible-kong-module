from ansible.module_utils.kong import Kong
import requests


class KongAPI(Kong):

    def api_list(self):
        """
        Get a list of APIs configured in Kong.

        :return: a dictionary of API info
        :rtype: dict
        """
        return self._get('apis')

    def api_get(self, name):
        """
        Look up a specific API in Kong.

        :param name: name of the API to fetch
        :type name: str
        :return: all properties of the API
        :rtype: dict
        """
        try:
            r = self._get(['apis', name])
        except requests.HTTPError:
            return None
        else:
            return r

    def api_apply(self, name, upstream_url, hosts=None, uris=None,
                  methods=None, strip_uri=False, preserve_host=False):
        """
        Declaratively apply the API configuration to the server.
        Will choose to POST or PATCH depending on whether the API already exists or not.
        See Kong API documentation for more info on the arguments of this method.

        :param name: name of the API to manage
        :type name: str
        :param upstream_url: upstream URL of the API
        :type upstream_url: str
        :param hosts: list of hostnames pointing to Kong for this API
        :type hosts: list
        :param uris: list of URI prefixes that point to the API
        :type uris: list
        :param methods: list of methods supported by / routed to the API
        :type methods: list
        :param strip_uri: strip the request URI from the request upstream
        :type strip_uri: bool
        :param preserve_host: preserve the hostname of the upstream request
        :type preserve_host: bool
        :return: interpreted Kong response
        :rtype: dict
        """

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
            r = self._patch(['apis', name], data=data)
        else:
            # post new API to the root of /apis
            r = self._post('apis', data)

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
            return self._delete(['apis', name])

        return False
