import uuid

from ansible.module_utils.kong import Kong
from ansible.module_utils.kong.consumer import KongConsumer
from ansible.module_utils.kong.route import KongRoute
from ansible.module_utils.kong.service import KongService
from ansible.module_utils.six import iteritems


class KongPlugin(KongRoute, KongConsumer, Kong):
    """
    KongPlugin manages Plugin objects in Kong.
    Uses KongServie, KongRoute and KongConsumer as mixins to query Services, Routes
    and Consumers.
    """

    @staticmethod
    def _prepare_config(config):
        """
        Takes a dictionary and prefixes the keys with 'config.'.
        The Kong Plugin endpoint does not support a native dictionary for config.

        :param config: the input config dictionary
        :type config: dict
        :return: dictionary with keys prefixed with 'config.'
        :rtype: dict
        """

        return {'config.' + k: v for k, v in iteritems(config)}

    def plugin_list(self):
        """
        Get a list of Plugins configured in Kong.

        :return: a dictionary of Plugin info
        :rtype: dict
        """

        return self._get('plugins')

    def plugin_query(self, name, service_name=None, route_attrs=None, consumer_name=None, plugin_id=None):
        """
        Query Kong for a Plugin matching the given properties.
        Raises requests.HTTPError and ValueError.

        :param plugin_id: 'id' field (UUID)
        :type plugin_id: str
        :param name: 'name' field
        :type name: str
        :param service_name: name of the Service to resolve
        :type service_name: str
        :param route_attrs: attributes of the Route to resolve
        :type route_attrs: dict
        :param consumer_name: name of the Consumer to resolve
        :type consumer_name: str
        :return: dictionary with 'total' and 'data' keys
        :rtype: dict
        """

        if plugin_id is name is None:
            raise ValueError("Need at least one of 'plugin_id' or 'name'")

        params = {
            'name': name
        }

        if plugin_id is not None:
            # Validate the given UUID, can raise ValueError
            # Querying for an invalid UUID will return a 400
            uuid.UUID(plugin_id)
            params['id'] = plugin_id

        # Resolve service_name to a Service ID
        if service_name is not None:
            s = self.service_get(service_name)

            if s is None:
                raise ValueError(
                    "Service '{}' not found. Has it been created?".format(service_name))

            service_id = s.get('id')

            uuid.UUID(service_id)

            params['service_id'] = service_id

        # Resolve route attribute dictionary to a Route ID
        if route_attrs is not None:
            r = self.route_query(**route_attrs)

            if r is None:
                raise ValueError(
                    'Route with requested attributes not found. Has it been created?')

            route_id = r.get('id')

            uuid.UUID(route_id)

            params['route_id'] = route_id

        # Resolve consumer_name to a Consumer ID
        # consumer_name can be False, in which case the result is filtered to
        # only contain plugins without `consumer_id`s.
        if consumer_name:
            c = self.consumer_get(consumer_name)

            if c is None:
                raise ValueError(
                    'Consumer {} not found. Has it been created?'.format(consumer_name))

            consumer_id = c.get('id')

            uuid.UUID(consumer_id)

            params['consumer_id'] = consumer_id

        # Can raise requests.HTTPError
        p = self._get('plugins').get('data', None)

        # Remove plugin entries that have a `consumer_id` set
        if not consumer_name:
            p = [x for x in p if not x.get('consumer_id')]

        # Remove plugin entries that have a `service_id` set
        if not service_name:
            p = [x for x in p if not x.get('service_id')]

        # Remove plugin entries that have a `route_id` set
        if not route_attrs:
            p = [x for x in p if not x.get('route_id')]

        return p

    def plugin_apply(self, name, config=None, service_name=None,
                     route_attrs=None, consumer_name=False):
        """
        Idempotently apply the Plugin configuration on the server.
        See Kong API documentation for more info on the arguments of this method.

        We want to manage one resource at a time only. If consumer_name is not given
        to this function, we want to eliminate entries from the plugin query that have
        `consumer_id` set. This behaviour is triggered by setting `consumer_name=False`
        to plugin_query().

        :param name: name of the Plugin to configure
        :type name: str
        :param config: configuration parameters for the Plugin
        :type config: dict
        :param service_name: name of the Service to configure the Plugin on
        :type service_name: str
        :param route_attrs: attributes of the Route to configure the Plugin on
        :type route_attrs: dict
        :param consumer_name: name of the Consumer to configure the plugin for
        :type consumer_name: str
        :return: whether the Plugin resource was touched or not
        :rtype: bool
        """

        uri = ['plugins']

        data = {
            'name': name,
        }

        if service_name:
            uri = ['services', service_name, 'plugins']

            # Check if Service exists
            if self.service_get(service_name) is None:
                raise ValueError(
                    "Service '{}' not found. Has it been created?".format(service_name))

        if route_attrs:
            r = self.route_query(**route_attrs)

            if r is None:
                raise ValueError(
                    'Route with requested attributes not found. Has it been created?')

            route_id = r.get('id')

            uuid.UUID(route_id)

            uri = ['routes', route_id, 'plugins']

        if consumer_name:
            c = self.consumer_get(consumer_name)

            if c is None:
                raise ValueError(
                    "Consumer '{}' not found. Has it been created?".format(consumer_name))

            consumer_id = c.get('id')

            uuid.UUID(consumer_id)

            data['consumer_id'] = consumer_id

        if config is not None:
            if not isinstance(config, dict):
                raise ValueError("'config' parameter is not a dict")

            # Merge config entries into payload
            data.update(self._prepare_config(config))

        # Query the plugin with the given criteria
        p = self.plugin_query(name=name, service_name=service_name,
                              route_attrs=route_attrs, consumer_name=consumer_name)
        if len(p) > 1:
            raise ValueError("Found multiple Plugin records for name: '{}', service: '{}', route: '{}', consumer: '{}'".
                             format(name, service_name, route_attrs, consumer_name))

        # Set the Plugin ID in the PUT request if the Plugin entry already exists
        if p:
            data['id'] = p[0].get('id')
            data['created_at'] = p[0].get('created_at')

        r = self._put(uri, data=data)

        return r

    def plugin_delete(self, name, service_name=None, route_attrs=None, consumer_name=False):
        """
        Delete the API if it exists.

        :param name: name of the API to remove the Plugin configuration from
        :type name: str
        :param consumer_name: name of the Consumer to delete the Plugin from
        :type consumer_name: str
        :param route_attrs: attributes of the Route to delete the Plugin from
        :type route_attrs: dict
        :param service_name: name of the Service to delete the Plugin from
        :type service_name: str
        :return: True on a successful delete, False if no action taken
        :rtype: bool
        """

        p = self.plugin_query(name=name, service_name=service_name,
                              route_attrs=route_attrs, consumer_name=consumer_name)
        if len(p) > 1:
            raise ValueError("Found multiple Plugin records for name: '{}', service: '{}', route: '{}', consumer: '{}'".
                             format(name, service_name, route_attrs, consumer_name))

        # Delete the Plugin configuration if it exists
        if p:
            return self._delete(['plugins', p[0].get('id')])

        return False
