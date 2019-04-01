"""
ansible.module_utils.kong.certificate implements Certificate operations on the Kong Admin API.

:authors: Timo Beckers, Roman Komkov
:license: MIT
"""
import requests
from ansible.module_utils.kong import Kong


class KongCertificate(Kong):
    """Execute the Kong Certificate module."""

    def certificate_list(self):
        """
        Get a list of Certificates configured in Kong.

        :return: the Certificate object
        :rtype: dict
        """
        return self._get_multipart('certificates')

    def certificate_get(self, sni):
        """
        Look up a specific Certificate in Kong.

        :param name: SNI to fetch the Certificate for
        :type name: str
        :return: the Certificate object
        :rtype: dict
        """
        try:
            r = self._get(['certificates', sni])
        except requests.HTTPError:
            return None
        else:
            return r

    def certificate_apply(self, snis, cert, key):
        """
        Apply the Certificate object configuration.

        :param snis: SNIs to associate the Certificate with
        :type snis: list
        :param cert: certificate in PKE format
        :type cert: str
        :param key: certificate private key in PKE format
        :type key: str
        :return: the Certificate object
        :rtype: dict
        """
        if not snis:
            raise ValueError('snis needs to contain at least one entry')

        if None in (cert, key):
            raise ValueError('cert and key need to be specified')

        data = {
            'snis': snis,
            'cert': cert,
            'key': key,
        }

        # Query only one SNI per certificate.
        sni = snis[0]

        if self.certificate_get(sni):
            r = self._patch(['certificates', sni], data=data)
        else:
            r = self._post('certificates', data=data)

        return r

    def certificate_delete(self, sni):
        """
        Delete the Certificate if it exists.

        :param sni: SNI of the Certificate to delete
        :type sni: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.certificate_get(sni):
            return self._delete(['certificates', sni])

        return False
