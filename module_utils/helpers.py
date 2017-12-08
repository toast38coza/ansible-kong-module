from distutils.version import StrictVersion


def version_compare(api_version, supported_version):
    """
    Simple implementation of an equal version compare.
    Returns False if major versions differ.

    :param api_version: version of the remote API
    :type api_version: str
    :param supported_version: version the client library supports
    :type supported_version: str
    :return: whether the version matches
    :rtype: bool
    """

    return StrictVersion(api_version) >= StrictVersion(supported_version)


def render_list(inlist):
    """
    Convert a list to a string with newlines.
    :param inlist: The input list
    :type inlist: list
    :return: the list converted to a string
    """

    # Return empty string to avoid returning unnecessary newlines
    if not inlist:
        return ''

    return '\n{}\n\n'.format('\n'.join([str(x) for x in inlist]))
