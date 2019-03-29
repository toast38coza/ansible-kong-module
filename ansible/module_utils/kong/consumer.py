"""
ansible.module_utils.kong.consumer implements Consumer operations on the Kong Admin API.

:authors: Timo Beckers
:license: MIT
"""

import uuid

import requests
from ansible.module_utils.kong import Kong
from ansible.module_utils.six import iteritems

AUTH_PRIMARY_KEY = {
    'basic-auth': 'username',
    'hmac-auth': 'username',
    'oauth2': 'name',
    'jwt': 'key',
}


class KongConsumer(Kong):
    """KongConsumer is a Kong subclass implementing Consumer operations."""

    def consumer_list(self):
        """
        Get a list of consumers configured in Kong.

        :return: a dictionary of consumer info
        :rtype: dict
        """
        return self._get_multipart('consumers')

    def consumer_query(self, consumer_id=None, custom_id=None, username=None):
        """
        Query Kong for a consumer matching the given properties.

        Raises requests.HTTPError and ValueError.

        :param consumer_id: 'id' field (UUID)
        :type consumer_id: str
        :param custom_id: 'custom_id' field
        :type custom_id: str
        :param username: 'username' field
        :type username: str
        :return: dictionary with 'total' and 'data' keys
        :rtype: dict
        """
        if consumer_id is custom_id is username is None:
            raise ValueError(
                "Need at least one of 'consumer_id', 'custom_id' or 'username'")

        params = {}

        if consumer_id is not None:
            # Validate the given UUID, can raise ValueError
            # Querying for an invalid UUID will return a 400
            uuid.UUID(consumer_id)

            params['id'] = consumer_id

        if custom_id is not None:
            params['custom_id'] = custom_id

        if username is not None:
            params['username'] = username

        # Can raise requests.HTTPError
        return self._get_multipart('consumers')

    def consumer_get(self, idname):
        """
        Get the consumer based on its unique name or id.

        :param idname: name or id
        :type idname: str
        :return: None or the Consumer's info
        :rtype: dict
        """
        try:
            r = self._get(['consumers', idname])
        except requests.HTTPError:
            return None
        else:
            return r

    def consumer_apply(self, username=None, custom_id=None):
        """
        Apply a Consumer configuration.

        :param username: username of the Consumer
        :type username: str
        :param custom_id: custom ID of the consumer
        :type custom_id: str
        :return: Consumer object if created, False if no action taken
        :rtype: dict | bool
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
            return self._put(['consumers', idname], data=data)

        return False

    def consumer_delete(self, idname):
        """
        Delete the Consumer if it exists.

        :param idname: name of the Consumer
        :type idname: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.consumer_get(idname):
            return self._delete(['consumers', idname])

        return False

    def credential_query(self, consumer_idname, auth_type, config=None):
        """
        Query a Consumer credential.

        If `auth_type` appears as a key in AUTH_PRIMARY_KEY, `config` needs to
        have that value as a key, eg. 'basic-auth' needs a 'username' config
        entry. All other auth_types are matched when all values in the given
        `config` appear in and are identical to the ones in the Consumer
        credential.

        :param consumer_idname: the ID or name of the Consumer to configure
        :type consumer_idname: str
        :param auth_type: the authentication type
        :type auth_type: str
        :param config: credential configuration
        :type config: dict
        :return: the data portion of the Kong response
        :rtype: list
        """
        # Check if Consumer exists
        if not self.consumer_get(consumer_idname):
            raise ValueError(
                "Consumer '{}' does not exist".format(consumer_idname))

        # Gets the name of the primary key of the auth plugin, and throws if
        # the key is not present in the configuration dictionary.
        pk = auth_primary_key(auth_type, config)

        q = self._get_multipart(['consumers', consumer_idname, auth_type])

        # If the auth plugin has a primary key, only use that one for
        # filtering the results.
        if pk:
            return [cred for cred in q if cred.get(pk) == config[pk]]

        creds = []

        # Step into a credential returned from the API.
        for cred in q:
            # Look up all config keys in the credential.
            for k, v in iteritems(config):
                # Skip the item when the key is missing or value doesn't match.
                if cred.get(k) != v:
                    break
            else:
                # Append the item if the config lookup ran successfully.
                creds.append(cred)

        return creds

    def credential_apply(self, consumer_idname, auth_type, config=None):
        """
        Apply a Consumer credential.

        `auth_type`s that appear in the AUTH_PRIMARY_KEY dict will be patched
        when a lookup on their primary key is successful.

        :param consumer_idname: the Consumer's ID or username
        :type consumer_idname: str
        :param auth_type: the authentication type
        :type auth_type: str
        :param config: credential configuration
        :type config: dict
        :return: the created or modified object
        :rtype: dict
        """
        # Check if Consumer exists
        if not self.consumer_get(consumer_idname):
            raise ValueError(
                "Consumer '{}' does not exist".format(consumer_idname))

        # Check if the Consumer credential configuration exists
        cq = self.credential_query(consumer_idname, auth_type, config=config)

        if len(cq) > 1:
            raise ValueError('Credential query returned multiple results')

        # If the auth type has a primary key and exists, patch instead of post.
        if cq and auth_primary_key(auth_type, config):
            cid = cq[0].get('id')
            return self._patch(['consumers', consumer_idname, auth_type, cid], data=config)

        # No credentials found, create the Consumer credential configuration
        if not cq:
            return self._post(['consumers', consumer_idname, auth_type], data=config)

        return cq[0]

    def credential_delete(self, consumer_idname, auth_type, config=None):
        """
        Delete a Consumer Plugin configuration.

        :param consumer_idname: the Consumer's ID or username
        :type consumer_idname: str
        :param auth_type: the authentication type
        :type auth_type: str
        :param config: credential configuration
        :type config: dict
        :return: the object has been successfully deleted
        :rtype: bool
        """
        # Check if Consumer exists
        if not self.consumer_get(consumer_idname):
            raise ValueError(
                "Consumer '{}' does not exist".format(consumer_idname))

        # Check if the Consumer Plugin configuration exists
        cq = self.credential_query(consumer_idname, auth_type, config)
        if len(cq) > 1:
            raise ValueError('Credential query returned multiple results')

        if cq:
            # Found the Configuration, delete it
            return self._delete(['consumers', consumer_idname, auth_type, cq[0].get('id')])

        return False


def auth_primary_key(auth_type, config):
    """
    Check `config` for the `auth_type`s primary key if it has one.

    Look up the given `auth_type` in the AUTH_PRIMARY_KEY dict. If the auth_type
    has a primary key, assert that it's present in the given `config` dict.

    :param auth_type: the authentication type
    :type auth_type: str
    :param config: credential configuration
    :type config: dict
    :return: name of the auth_type's primary key 
    :rtype: str
    """
    if config is None:
        raise ValueError("Config is None")

    pk_name = AUTH_PRIMARY_KEY.get(auth_type, None)
    if not pk_name:
        return None

    # Check if the primary key is present in the config dictionary.
    if not config.get(pk_name):
        raise ValueError(
            "Consumer plugin '{}' needs key '{}' in config".format(auth_type, pk_name))

    return pk_name
