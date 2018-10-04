import uuid
from ansible.module_utils.kong import Kong
from ansible.module_utils.kong_api import KongAPI
from ansible.module_utils.kong_consumer import KongConsumer
from ansible.module_utils.six import iteritems


class KongPlugin(KongAPI, KongConsumer, Kong):
    """
    KongPlugin manages Plugin objects in Kong.
    Uses KongAPI and KongConsumer as mixins to query APIs and Consumers.
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

    def plugin_query(self, name, api_name=None, consumer_name=None, plugin_id=None):
        """
        Query Kong for a Plugin matching the given properties.
        Raises requests.HTTPError and ValueError.

        :param plugin_id: 'id' field (UUID)
        :type plugin_id: str
        :param name: 'name' field
        :type name: str
        :param api_name: name of the API to resolve
        :type api_name: str
        :param consumer_name: name of the Consumer to resolve
        :type consumer_name: str
        :return: dictionary with 'total' and 'data' keys
        :rtype: dict
        """

        if plugin_id is name is api_name is consumer_name is None:
            raise ValueError("Need at least one of 'plugin_id', 'name', 'api_name' or 'consumer_name'")

        params = {
            'name': name
        }

        if plugin_id is not None:
            # Validate the given UUID, can raise ValueError
            # Querying for an invalid UUID will return a 400
            uuid.UUID(plugin_id)
            params['id'] = plugin_id

        # Resolve api_name to an API ID
        if api_name is not None:
            a = self.api_get(api_name)

            if a is None:
                raise ValueError('API {} not found. Has it been created?'.format(api_name))

            api_id = a.get('id')

            uuid.UUID(api_id)

            params['api_id'] = api_id

        # Resolve consumer_name to a Consumer ID
        # consumer_name can be False, in which case the result is filtered to
        # only contain plugins without `consumer_id`s.
        if consumer_name:
            c = self.consumer_get(consumer_name)

            if c is None:
                raise ValueError('Consumer {} not found. Has it been created?'.format(consumer_name))

            consumer_id = c.get('id')

            uuid.UUID(consumer_id)

            params['consumer_id'] = consumer_id

        # Can raise requests.HTTPError
        p = self._get('plugins', params=params).get('data', None)

        # Remove plugin entries that have a `consumer_id` set
        if consumer_name is False:
            p = [x for x in p if not x.get('consumer_id')]

        return p

    def plugin_apply(self, name, config=None, api_name=None, consumer_name=False):
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
        :param api_name: name of the API to configure the Plugin on
        :type api_name: str
        :param consumer_name: name of the Consumer to configure the plugin for
        :type consumer_name: str
        :return: whether the Plugin resource was touched or not
        :rtype: bool
        """

        uri = ['plugins']

        if api_name:
            uri = ['apis', api_name, 'plugins']

        data = {
            'name': name,
        }

        if config is not None:
            if not isinstance(config, dict):
                raise ValueError("'config' parameter is not a dict")

            # Merge config entries into payload
            data.update(self._prepare_config(config))

        if consumer_name:
            c = self.consumer_get(consumer_name)

            if c is None:
                raise ValueError('Consumer {} not found. Has it been created?'.format(consumer_name))

            consumer_id = c.get('id')

            uuid.UUID(consumer_id)

            data['consumer_id'] = consumer_id

        # Check if API exists first
        if self.api_get(api_name) is None:
            raise ValueError("API '{}' not found. Has it been created?".format(api_name))

        # Query the plugin with the given criteria
        p = self.plugin_query(name=name, consumer_name=consumer_name, api_name=api_name)
        if len(p) > 1:
            raise ValueError("Found multiple Plugin records for name: '{}', consumer_name: '{}', api_name: '{}'".
                             format(name, consumer_name, api_name))

        # Set the Plugin ID in the PUT request if the Plugin entry already exists
        if p:
            data['id'] = p[0].get('id')
            data['created_at'] = p[0].get('created_at')

        r = self._put(uri, data=data)

        return r

    def plugin_delete(self, name, consumer_name=False, api_name=None):
        """
        Delete the API if it exists.

        :param name: name of the API to remove the Plugin configuration from
        :type name: str
        :param consumer_name: name of the Consumer to delete the Plugin from
        :type consumer_name: str
        :param api_name: name of the API to delete the Plugin from
        :type api_name: str
        :return: True on a successful delete, False if no action taken
        :rtype: bool
        """

        p = self.plugin_query(name=name, consumer_name=consumer_name, api_name=api_name)
        if len(p) > 1:
            raise ValueError("Found multiple Plugin records for name: '{}', consumer_name: '{}', api_name: '{}'".
                             format(name, consumer_name, api_name))

        # Delete the Plugin configuration if it exists
        if p:
            return self._delete(['apis', api_name, 'plugins', p[0].get('id')])

        return False
