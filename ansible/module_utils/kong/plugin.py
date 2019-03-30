"""
ansible.module_utils.kong.plugin implements Plugin operations on the Kong Admin API.

:authors: Timo Beckers
:license: MIT
"""
import uuid

from ansible.module_utils.kong import Kong
from ansible.module_utils.kong.consumer import KongConsumer
from ansible.module_utils.kong.route import KongRoute
from ansible.module_utils.kong.service import KongService
from ansible.module_utils.six import iteritems


class KongPlugin(KongRoute, KongConsumer, Kong):
    """
    KongPlugin manages Plugin objects in Kong.

    Uses KongRoute and KongConsumer as mixins to query Routes and Consumers.
    """

    def plugin_list(self):
        """
        Get a list of Plugins configured in Kong.

        :return: a list of Plugins
        :rtype: dict
        """
        return self._get_multipart('plugins')

    def plugin_get(self, plugin_id):
        """
        Get a Plugin by its ID.

        :param plugin_id: the UUID of the Plugin
        :type plugin_id: str
        :return: the Plugin object
        :rtype: dict
        """
        return self._get(['plugins', plugin_id])

    def plugin_query(self, name, service_name=None, route_name=None, consumer_name=None):
        """
        Query Kong for a Plugin matching the given properties.

        Raises requests.HTTPError and ValueError.
        Any given Service, Route or Consumer names are resolved to IDs
        before filtering the Plugin list.

        :param name: Plugin name (type)
        :type name: str
        :param service_name: name of the Service to resolve
        :type service_name: str
        :param route_name: name of the Route to resolve
        :type route_name: str
        :param consumer_name: name of the Consumer to resolve
        :type consumer_name: str
        :return: list of Plugins
        :rtype: list
        """
        if name is None:
            raise ValueError("'name' is required")

        service_id = None
        route_id = None
        consumer_id = None

        # Resolve service_name to a Service ID.
        if service_name:
            s = self.service_get(service_name)
            if s is None:
                raise ValueError(
                    "Service '{}' not found.".format(service_name))

            service_id = s.get('id')
            uuid.UUID(service_id)

        # Resolve route_name to a Route ID.
        if route_name:
            r = self.route_get(route_name)
            if r is None:
                raise ValueError("Route '{}' not found.".format(route_name))

            route_id = r.get('id')
            uuid.UUID(route_id)

        # Resolve consumer_name to a Consumer ID.
        if consumer_name:
            c = self.consumer_get(consumer_name)
            if c is None:
                raise ValueError(
                    "Consumer '{}' not found.".format(consumer_name))

            consumer_id = c.get('id')
            uuid.UUID(consumer_id)

        plugins = self.plugin_list()

        out = []

        for p in plugins:

            p_consumer = p.get('consumer')
            p_service = p.get('service')
            p_route = p.get('route')

            if p.get('name') != name:
                continue

            # Require the Plugin's consumer to be set if consumer is provided.
            if (p_consumer is None) != (consumer_id is None):
                continue
            # Require the Plugin's consumer ID to match if given.
            if p_consumer and p_consumer.get('id') != consumer_id:
                continue

            # Require the Plugin's service to be set if service is provided.
            if (p_service is None) != (service_id is None):
                continue
            # Require the Plugin's service ID to match if given.
            if p_service and p_service.get('id') != service_id:
                continue

            # Require the Plugin's route to be set if route is provided.
            if (p_route is None) != (route_id is None):
                continue
            # Require the Plugin's route ID to match if given.
            if p_route and p_route.get('id') != route_id:
                continue

            out.append(p)

        return out

    def plugin_apply(self, name, config=None, service_name=None,
                     route_name=None, consumer_name=False):
        """
        Apply the given Plugin configuration.

        :param name: name of the Plugin to configure
        :type name: str
        :param config: configuration parameters for the Plugin
        :type config: dict
        :param service_name: name of the Service to configure the Plugin for
        :type service_name: str
        :param route_name: name of the Route to configure the Plugin for
        :type route_name: str
        :param consumer_name: name of the Consumer to configure the plugin for
        :type consumer_name: str
        :return: the resulting Plugin object
        :rtype: dict
        """
        if config and not isinstance(config, dict):
            raise ValueError("'config' parameter is not a dict")

        data = {
            'name': name,
            'config': config,
        }

        if service_name:
            s = self.service_get(service_name)
            if s is None:
                raise ValueError(
                    "Service '{}' not found.".format(service_name))

            data['service'] = s

        if route_name:
            r = self.route_get(route_name)
            if r is None:
                raise ValueError("Route '{}' not found.".format(route_name))

            data['route'] = r

        if consumer_name:
            c = self.consumer_get(consumer_name)
            if c is None:
                raise ValueError(
                    "Consumer '{}' not found.".format(consumer_name))

            data['consumer'] = c

        # Query the plugin with the given attributes.
        p = self.plugin_query(name=name, service_name=service_name,
                              route_name=route_name, consumer_name=consumer_name)

        if len(p) > 1:
            raise ValueError("Multiple Plugin records for name: '{}', service: '{}', route: '{}', consumer: '{}'".
                             format(name, service_name, route_name, consumer_name))

        if p:
            # Update existing Plugin.
            return self._patch(['plugins', p[0].get('id')], data=data)

        # Insert new Plugin.
        return self._post(['plugins'], data=data)

    def plugin_delete(self, name, service_name=None, route_name=None, consumer_name=False):
        """
        Delete the Plugin if it exists.

        :param name: name (type) of the Plugin
        :type name: str
        :param consumer_name: name of the Consumer to delete the Plugin from
        :type consumer_name: str
        :param route_name: name of the Route to delete the Plugin from
        :type route_name: str
        :param service_name: name of the Service to delete the Plugin from
        :type service_name: str
        :return: True on a successful delete, False if no action taken
        :rtype: bool
        """
        p = self.plugin_query(name=name, service_name=service_name,
                              route_name=route_name, consumer_name=consumer_name)

        if len(p) > 1:
            raise ValueError("Found multiple Plugin records for name: '{}', service: '{}', route: '{}', consumer: '{}'".
                             format(name, service_name, route_name, consumer_name))

        if p:
            return self._delete(['plugins', p[0].get('id')])

        return False
