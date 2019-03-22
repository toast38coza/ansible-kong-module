import requests
from ansible.module_utils.kong import Kong


class KongService(Kong):

    def service_list(self):
        """
        Get a list of Services configured in Kong.

        :return: a dictionary of Services info
        :rtype: dict
        """
        return self._get('services')

    def service_get(self, name):
        """
        Look up a specific Service in Kong.

        :param name: name of the Service to fetch
        :type name: str
        :return: all properties of the Service
        :rtype: dict
        """
        try:
            r = self._get(['services', name])
        except requests.HTTPError:
            return None
        else:
            return r

    def service_apply(self, name, host, port=None, protocol=None, path=None, retries=None,
                      connect_timeout=None, write_timeout=None, read_timeout=None):
        """
        Declaratively apply the service configuration to the server.
        Will choose to POST or PATCH depending on whether the service already exists or not.
        See Kong service documentation for more info on the arguments of this method.

        :param name: name of the service to manage
        :type name: str
        :param protocol: protocol used to communicate with the upstream (http or https)
        :type protocol: str
        :param host: host of the upstream server
        :type host: str
        :param port: uptream server port
        :type port: int
        :param path: path to be used in requests to the upstream server
        :type path: str
        :param retries: number of retries to execute upon failure to proxy
        :type retries: int
        :param connect_timeout: timeout in milliseconds for establishing a connection to the upstream server
        :type connect_timeout: int
        :param write_timeout: timeout in milliseconds for establishing a connection to the upstream server
        :type write_timeout: int
        :param read_timeout: timeout in milliseconds for establishing a connection to the upstream server
        :type read_timeout: int
        :return: interpreted Kong response
        :rtype: dict
        """

        if host is None:
            raise ValueError('host needs to be specified.')

        if name is None:
            raise ValueError('name needs to be specified.')

        payload = {
            'name': name,
            'protocol': protocol,
            'host': host,
            'port': port,
            'path': path,
            'retries': retries,
            'connect_timeout': connect_timeout,
            'write_timeout': write_timeout,
            'read_timeout': read_timeout
        }

        # check if the service is already defined in Kong
        if self.service_get(name):
            # patch the resource at /services/{name}
            r = self._patch(['services', name], data=payload)
        else:
            # post new service to the root of /services
            r = self._post('services', data=payload)

        return r

    def service_delete(self, name):
        """
        Delete the service if it exists.

        :param name: name of the service
        :type name: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.service_get(name):
            return self._delete(['services', name])

        return False
