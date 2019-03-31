"""
ansible.module_utils.kong.helpers is a helpers package for the Kong Admin API client.

:authors: Timo Beckers
:license: MIT
"""
from distutils.version import StrictVersion

MIN_VERSION = '1.0.0'


def params_fields_lookup(amod, fields):
    """
    Look up all keys mentioned in 'fields' in the module parameters and return their values.

    :param fields: a list of keys to extract from module params
    :type fields: list
    :param amod: the Ansible module to query
    :type amod: AnsibleModule
    :return: dictionary of queried values, default None
    :rtype: dict
    """
    return {x: amod.params[x] for x in fields if amod.params.get(x, None) is not None}


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


def kong_status_check(kong, amod):
    """
    Wrap the Kong status check with fail_json.

    :param kong: an initialized, configured Kong API object
    :type kong: Kong
    :param amod: the Ansible module object
    :type amod: AnsibleModule
    :return: True or fail_json call on Ansible module
    :rtype: bool
    """
    try:
        if not kong.healthy:
            amod.fail_json(
                msg='Kong database unreachable according to status endpoint')
    except Exception as e:
        amod.fail_json(msg='Unable to perform Kong status call: {}'.format(e))

    return True


def kong_version_check(kong, amod):
    """
    Wrap the Kong version check with warn.

    Calls warn() on the Ansible module if the remote endpoint
    doesn't meet the module's minimum version.

    :param kong: an initialized, configured Kong API object
    :type kong: Kong
    :param amod: the Ansible module object
    :type amod: AnsibleModule
    :return: remote endpoint meets minimum version
    :rtype: bool
    """
    kong_version = kong.version

    if not StrictVersion(kong_version) >= StrictVersion(MIN_VERSION):
        amod.warn('Module supports Kong {} and up (found {})'.format(
            MIN_VERSION, kong_version))
        return False

    return True
