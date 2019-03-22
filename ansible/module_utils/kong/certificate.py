from ansible.module_utils.kong import Kong
import requests


class KongCertificate(Kong):

    def certificate_list(self):
        """
        Get a list of Certificates configured in Kong.

        :return: a dictionary of Certificates info
        :rtype: dict
        """
        return self._get('certificates')

    def certificate_get(self, sni):
        """
        Look up a specific Certificate in Kong.

        :param name: SNI to fetch the Certificate for
        :type name: str
        :return: Certificate data
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
        Declaratively apply the Certificate object configuration to the server.
        Will choose to POST or PATCH depending on whether the Certificate for SNI already exists or not.
        See Kong Certificate documentation for more info on the arguments of this method.

        :param snis: SNIs to associate the Certificate with
        :type snis: str
        :param cert: certificate in PKE format
        :type cert: str
        :param key: certificate private key in PKE format
        :type key: str
        :return: interpreted Kong response
        :rtype: dict
        """

        if snis is None:
            raise ValueError('snis needs to be specified.')

        if cert is None:
            raise ValueError('cert needs to be specified.')

        if key is None:
            raise ValueError('key needs to be specified.')

        data = {
            'snis': snis,
            'cert': cert,
            'key': key,
        }

        # Support only one SNI per Certificate
        sni = snis[0]

        # check if the Certificate for SNI is already defined in Kong
        if self.certificate_get(sni):
            # patch the resource at /certificates/{sni}
            r = self._patch(['certificates', sni], data=data)
        else:
            # post new service to the root of /certificates
            r = self._post('certificates', data=data)

        return r

    def certificate_delete(self, sni):
        """
        Delete the Certificate if it exists.

        :param sni: SNI to delete the Certificate assigned to
        :type sni: str
        :return: True on a successful delete, False if it didn't exist
        :rtype: bool
        """
        if self.certificate_get(sni):
            return self._delete(['certificates', sni])

        return False
