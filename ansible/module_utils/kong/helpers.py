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
    out = {}
    for x in fields:
        if amod.params.get(x, None) is not None:
            # Re-write a list with a single empty string as an empty list.
            # This is to work around list module parameters that receive the
            # 'omit' value, causing Ansible to set a list with a single empty
            # string.
            if amod.params[x] == ['']:
                out[x] = []
                continue

            out[x] = amod.params[x]

    return out


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


def sorted_dict_list(inlist):
    """
    Return a sorted set of tuples from a list of non-nested dicts.

    d.items() returns a list of k, v tuples of the dictionary's items.
    That list of tuples is sorted for stability between runs.
    tuple() converts the list of tuples to a tuple of tuples.
    Finally, set() ensures all entries are unique and makes the return
    value comparable.

    :param inlist: list of non-nested dictionaries
    :type inlist: list
    :return: set of sorted tuples of the list's dicts
    """
    if not isinstance(inlist, list):
        raise ValueError('input value is not a list')

    for i in inlist:

        # Ignore empty strings caused by setting omit on a module parameter.
        if not i:
            continue

        if not isinstance(i, dict):
            raise ValueError(
                "input list is not a list of dicts (got {}): '{}'".format(type(i), inlist))

        for v in i.values():
            if isinstance(v, dict):
                raise ValueError('input list contains a nested dict')

    return set(tuple(sorted(d.items())) for d in inlist if d)


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
