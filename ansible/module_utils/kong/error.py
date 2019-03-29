import requests


def raise_for_error(response):
    """
    :params response: The request's Response object.
    :type response: requests.Response
    :rtype: None
    """

    if not isinstance(response, requests.Response):
        raise ValueError("response argument is not a requests.Response")

    # 4xx errors are 'normal' API error responses from Kong.
    if 400 <= response.status_code < 500:
        rj = response.json()
        raise KongError(code=rj.get('code'), fields=rj.get(
            'fields'), message=rj.get('message'), name=rj.get('name'))

    response.raise_for_status()

    return


class KongError(requests.HTTPError):

    def __init__(self, code=None, fields=None, message=None, name=None):
        requests.HTTPError.__init__(self)

        if message is None:
            raise ValueError("KongError requires a message")

        self.message = message
        self.code = code
        self.fields = fields
        self.name = name

    def __str__(self):
        return "Kong API error: " + self.message
