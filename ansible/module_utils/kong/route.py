"""
ansible.module_utils.kong.route implements Route operations on the Kong Admin API.

:authors: Timo Beckers, Roman Komkov
:license: MIT
"""
import uuid

import requests
from ansible.module_utils.kong import Kong
from ansible.module_utils.kong.helpers import sorted_dict_list
from ansible.module_utils.kong.service import KongService


class KongRoute(KongService, Kong):
    """
    KongPlugin manages Route objects in Kong.

    Uses KongService as mixins to query Services.
    """

    def route_list(self, service_idname):
        """
        Get a list of Routes for the given Service.

        :param service_idname: the ID or name of the Service
        :type service_idname: str
        :return: a list of Routes
        :rtype: list
        """
        return self._get_multipart(['services', service_idname, 'routes'])

    def route_get(self, idname):
        """
        Get a specific Route by its ID or name.

        :param idname: ID or name of the Route
        :type idname: str
        :return: Route object
        :rtype: dict
        """
        try:
            r = self._get(['routes', idname])
        except requests.HTTPError:
            return None
        else:
            return r

    def route_query(self, service_idname, protocols=[],
                    hosts=[], paths=[], methods=[], snis=[], sources=[], destinations=[]):
        """
        Query for Routes with the given attributes.

        :param service_idname: Service ID or name to query route from
        :type service_idname: str
        :param protocols: protocols of the Route
        :type protocols: list
        :param hosts: hosts of the Route
        :type hosts: list
        :param paths: paths of the Route
        :type paths: list
        :param methods: methods of the Route
        :type methods: list
        :param snis: snis of the Route
        :type snis: list
        :param sources: sources of the Route
        :type sources: list
        :param destinations: destinations of the Route
        :type destinations: list
        :return: list of Routes matching the given parameters
        :rtype: list
        """
        if not protocols:
            raise ValueError("'protocols' is required")

        if self.service_get(service_idname) is None:
            raise ValueError("Service '{}' not found".format(service_idname))

        return [r for r in self.route_list(service_idname) if
                set(r.get('protocols', []) or []) == set(protocols) and
                set(r.get('hosts', []) or []) == set(hosts) and
                set(r.get('paths', []) or []) == set(paths) and
                set(r.get('methods', []) or []) == set(methods) and
                set(r.get('snis', []) or []) == set(snis) and
                sorted_dict_list(r.get('sources', []) or []) == sorted_dict_list(sources) and
                sorted_dict_list(r.get('destinations', []) or []) ==
                sorted_dict_list(destinations)
                ]

    def route_apply(self, service_idname, name=None, protocols=[],
                    hosts=[], paths=[], methods=[],
                    snis=[], sources=[], destinations=[],
                    regex_priority=0, strip_path=False, preserve_host=False):
        """
        Apply the Route configuration.

        This method will not perform a query based on attributes if idname is
        specified. Therefore, a name cannot be set on an existing Route.

        :param service_idname: id of a Service to apply the Route to
        :type service_idname: str
        :param name: id or name of the Route to manage
        :type name: str
        :param hosts: list of hostnames the Route responds to
        :type hosts: list
        :param paths: list of paths for the Route
        :type paths: list
        :param methods: list of HTTP verbs for the Route
        :type methods: list
        :param methods: list of protocols for the Route
        :type methods: list
        :param snis: list of snis for the Route
        :type snis: list
        :param sources: list of sources for the Route
        :type sources: list
        :param destinations: list of destinations for the Route
        :type destinations: list
        :param regex_priority: numeric priority of the regex/URI match
        :type regex_priority: int
        :param strip_path: strip the URI from the request
        :type strip_uri: bool
        :param preserve_host: preserve the Host header of the request
        :type preserve_host: bool
        :return: the resulting Route object
        :rtype: dict
        """
        if not protocols:
            raise ValueError("'protocols' is required")

        if service_idname is None:
            raise ValueError("'service_idname' is required")

        if ('http' in protocols or 'https' in protocols) and (not hosts and not paths and not methods):
            raise ValueError(
                "Need at least one of hosts, paths or methods with http or https protocols")

        if ('tcp' in protocols or 'tls' in protocols) and (not snis and not sources and not destinations):
            raise ValueError(
                "Need at least one of snis, sources or destinations with tcp or tls protocols")

        s = self.service_get(service_idname)
        if s is None:
            raise ValueError("Service '{}' not found".format(service_idname))

        data = {
            'service': s,
            'protocols': protocols,
            'hosts': hosts,
            'paths': paths,
            'methods': methods,
            'snis': snis,
            'sources': sources,
            'destinations': destinations,
            'regex_priority': regex_priority,
            'strip_path': strip_path,
            'preserve_host': preserve_host,
        }

        r = None
        if name:
            # Only manage a named Route resource if name is specified.
            r = self.route_get(name)

            # If name is not a UUID, use it as the payload's 'name' key.
            try:
                uuid.UUID(name)
            except:
                data['name'] = name
        else:
            # Query the Route based on its attributes.
            rq = self.route_query(
                service_idname, protocols=protocols,
                hosts=hosts, paths=paths, methods=methods,
                snis=snis, sources=sources, destinations=destinations,
            )

            if len(rq) > 1:
                raise ValueError(
                    "Multiple Route records queried: {}".format(r))

            if rq:
                r = rq[0]

        if r:
            # Patch an existing Route.
            resp = self._patch(['routes', r.get('id')], data=data)
        else:
            # Insert new Route.
            resp = self._post(
                ['services', service_idname, 'routes'], data=data)

        return resp

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
