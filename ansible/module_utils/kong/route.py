import requests
from ansible.module_utils.kong import Kong
from ansible.module_utils.kong.service import KongService


class KongRoute(KongService, Kong):

    def route_list(self, service_name):
        """
        Get a list of Routes associated to a Kong Service.

        :param service_name: service name to query route from
        :type service_name: str
        :return: a list with routes
        :rtype: list
        """
        return self._get(['services', service_name, 'routes']).get('data', [])

    def route_get(self, route_id):
        """
        Get a specific Route by it's ID

        :param id: id of the Route
        :type id: str
        :return: route object
        :rtype: dict
        """
        try:
            r = self._get(['routes', route_id])
        except requests.HTTPError:
            return None
        else:
            return r

    def route_query(self, service_name, hosts=[], paths=[],
                    methods=[], protocols=[]):
        """
        Query Kong for a route matching the given attributes.

        :param service_name: service name or id to query route from
        :type service_name: str
        :param hosts: hosts, requested route should have
        :type hosts: list
        :param paths: paths, requested route should have
        :type paths: list
        :param methods: methods, requested route should have
        :type methods: list
        :param protocols: protocols, requested route should have
        :type protocols: list
        :return: a route matching a combination of hosts, paths, methods and protocols
        :rtype: dict
        """

        # Resolve service_name to a Service ID
        s = self.service_get(service_name)

        if s is None:
            raise ValueError(
                "Service '{}' not found. Has it been created?".format(service_name))

        result = []

        for r in self.route_list(service_name):
            if (cmp(sorted(r.get('hosts', [])), sorted(hosts)) == 0 and
                cmp(sorted(r.get('paths', [])), sorted(paths)) == 0 and
                cmp(sorted(r.get('methods', [])), sorted(methods)) == 0 and
                    cmp(sorted(r.get('protocols', [])), sorted(protocols)) == 0):
                result.append(r)

        if len(result) > 1:
            raise ValueError('Duplicate routes found. Clean up manually first')

        return result[0] if result else None

    def route_apply(self, service_name, hosts=None, paths=None, methods=None,
                    protocols=None, strip_path=False, preserve_host=False, route_id=None):
        """
        Declaratively apply the Route configuration to the server.
        Will choose to POST or PATCH depending on whether the API already exists or not.
        See Kong API documentation for more info on the arguments of this method.

        :param service_id: id of a Service to apply the Route to
        :type name: str
        :param hosts: list of hostnames pointing to Kong for this Route
        :type hosts: list
        :param paths: list of paths that point to the Route
        :type paths: list
        :param methods: list of methods supported by paths of the Route
        :type methods: list
        :param methods: list of protocols supported by the Route
        :type methods: list
        :param strip_path: strip the request URI from the request upstream
        :type strip_uri: bool
        :param preserve_host: preserve the hostname of the upstream request
        :type preserve_host: bool
        :return: interpreted Kong response
        :rtype: dict
        """

        if (protocols is None and hosts is None and paths is None and methods is None):
            raise ValueError(
                'Need at least one of protocols, hosts, paths or methods.')

        if service_name is None:
            raise ValueError('service_name needs to be specified.')

        s = self.service_get(service_name)

        if s is None:
            raise ValueError(
                "Service '{}' not found. Has it been created?".format(service_name))

        payload = {
            'protocols': protocols,
            'methods': methods,
            'hosts': hosts,
            'paths': paths,
            'strip_path': strip_path,
            'preserve_host': preserve_host,
            'service': {
                'id': s.get('id')
            }
        }

        # check if the API is already defined in Kong
        if route_id:
            # patch the resource at /routes/{id}
            r = self._patch(['routes', route_id], data=payload)
        else:
            # post new API to the root of /apis
            r = self._post('routes', data=payload)

        return r

    def route_delete(self, route_id):
        """
        Delete the Route if it exists.

        :param route_id: id of the Route
        :type route_id: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.route_get(route_id):
            return self._delete(['routes', route_id])

        return False
