"""
ansible.module_utils.kong.service implements Service operations on the Kong Admin API.

:authors: Timo Beckers, Roman Komkov
:license: MIT
"""
import requests
from ansible.module_utils.kong import Kong


class KongService(Kong):
    """KongService manages Service objects in Kong."""

    def service_list(self):
        """
        Get a list of Services configured in Kong.

        :return: the Service object
        :rtype: dict
        """
        return self._get_multipart('services')

    def service_get(self, idname):
        """
        Look up a Service by name or ID.

        :param idname: ID or name of the Service
        :type idname: str
        :return: the Service object
        :rtype: dict
        """
        try:
            r = self._get(['services', idname])
        except requests.HTTPError:
            return None
        else:
            return r

    def service_apply(self, name, host, port=None, protocol=None, path=None, retries=None,
                      connect_timeout=None, write_timeout=None, read_timeout=None):
        """
        Apply the Service configuration.

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
        :param connect_timeout: upstream connection timeout in milliseconds
        :type connect_timeout: int
        :param write_timeout: upstream write timeout in milliseconds
        :type write_timeout: int
        :param read_timeout: upstream read timeout in milliseconds
        :type read_timeout: int
        :return: the resulting Service object
        :rtype: dict
        """
        if host is None:
            raise ValueError('host needs to be specified.')

        if name is None:
            raise ValueError('name needs to be specified.')

        data = {
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

        if self.service_get(name):
            r = self._patch(['services', name], data=data)
        else:
            r = self._post('services', data=data)

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
