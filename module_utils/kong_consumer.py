from ansible.module_utils.kong import Kong

import requests
import uuid


class KongConsumer(Kong):

    def consumer_list(self):
        """
        Get a list of consumers configured in Kong.

        :return: a dictionary of consumer info
        :rtype: dict
        """
        return self._get('consumers')

    def consumer_query(self, id=None, custom_id=None, username=None):
        """
        Query Kong for a consumer matching the given properties.
        Raises requests.HTTPError and ValueError.

        :param id: 'id' field (UUID)
        :type id: str
        :param custom_id: 'custom_id' field
        :type custom_id: str
        :param username: 'username' field
        :type username: str
        :return: dictionary with 'total' and 'data' keys
        :rtype: dict
        """

        if id is custom_id is username is None:
            raise ValueError("Need at least one of 'id', 'custom_id' or 'username'")

        params = {}

        if id is not None:
            # Validate the given UUID, can raise ValueError
            # Querying for an invalid UUID will return a 400
            uuid.UUID(id)

            params['id'] = id

        if custom_id is not None:
            params['custom_id'] = custom_id

        if username is not None:
            params['username'] = username

        # Can raise requests.HTTPError
        return self._get('consumers', params=params)

    def consumer_get(self, idname):
        """
        Get the consumer based on its unique name or id.

        :param idname: name or id
        :type idname: str
        :return: None or the Consumer's info
        :rtype: dict
        """
        try:
            r = self._get('consumers', idname)
        except requests.HTTPError:
            return None
        else:
            return r

    def consumer_apply(self, username=None, custom_id=None):
        """
        Declaratively install the consumer to the server.

        :param username: username of the Consumer
        :type username: str
        :param custom_id: custom ID of the consumer
        :type custom_id: str
        :return: True if created, False if no action taken
        :rtype: bool
        """

        if username is custom_id is None:
            raise ValueError('Need at least one of name or custom_id.')

        if username and custom_id:
            raise ValueError('name and custom_id are mutually exclusive.')

        # Pick either value for the GET request
        idname = username if username is not None else custom_id

        data = {}

        # Build the request, name and custom_id are mutually exclusive
        if username:
            data['username'] = username
        elif custom_id:
            data['custom_id'] = custom_id

        # Only apply if the consumer does not already exist
        if not self.consumer_get(idname):
            return self._put('consumers', data=data)

        return False

    def consumer_delete(self, idname):
        """
        Delete the Consumer if it exists.

        :param name: name of the Consumer
        :type name: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.consumer_get(idname):
            return self._delete('consumers', idname)

        return False
