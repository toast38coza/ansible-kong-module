from ansible.module_utils.kong import Kong
from ansible.module_utils.helpers import *
from ansible.module_utils.basic import AnsibleModule

from ansible.module_utils.dotdiff import dotdiff


DOCUMENTATION = '''
---
module: kong
short_description: Configure a Kong API Gateway

'''

EXAMPLES = '''
- name: Register a site
  kong:
    kong_admin_uri: http://127.0.0.1:8001/apis/
    name: "Mockbin"
    taget_url: "http://mockbin.com"
    hosts: "mockbin.com"
    state: present

- name: Delete a site
  kong:
    kong_admin_uri: http://127.0.0.1:8001/apis/
    name: "Mockbin"
    state: absent

'''

MIN_VERSION = '0.11.0'


class DataBuilder:

    def __init__(self, fields):
        self.fields = fields

    def params_fields_lookup(self, amod):

        # Look up all keys mentioned in 'fields' in the module parameters, get their values
        return {x: amod.params[x] for x in self.fields if amod.params.get(x, None) is not None}


def main():

    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            name=dict(required=True, type='str'),
            upstream_url=dict(required=False, type='str'),
            hosts=dict(required=False, type='list'),
            uris=dict(required=False, type='list'),
            methods=dict(required=False, type='list'),
            strip_uri=dict(required=False, default=False, type='bool'),
            preserve_host=dict(required=False, default=False, type='bool'),
            state=dict(required=False, default="present", choices=['present', 'absent'], type='str'),
        ),
        required_if=[
            ('state', 'present', ['upstream_url'])
        ],
        supports_check_mode=True
    )

    result = {}

    # Emulates 'required_one_of' argument spec, as it cannot be made conditional
    if ansible_module.params['state'] == 'present' and \
        ansible_module.params['hosts'] is None and \
        ansible_module.params['uris'] is None and \
            ansible_module.params['methods'] is None:
        ansible_module.fail_json(msg="At least one of hosts, uris or methods is required when state is 'present'")

    # Kong 0.11.x
    api_fields = [
        'name',
        'upstream_url',
        'hosts',
        'uris',
        'methods',
        'strip_uri',
        'preserve_host',
        'retries',
        'upstream_connect_timeout',
        'upstream_read_timeout',
        'upstream_send_timeout',
        'https_only',
        'http_if_terminated'
    ]

    # Initialize helper class for building the requests
    b = DataBuilder(api_fields)
    data = b.params_fields_lookup(ansible_module)

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract other arguments
    state = ansible_module.params['state']
    name = ansible_module.params['name']

    # Create Kong client instance
    k = Kong(url, auth_user=auth_user, auth_pass=auth_pass)

    kong_version = k.version
    if not version_compare(kong_version, MIN_VERSION):
        ansible_module.warn('Module supports Kong {} and up (found {})'.format(MIN_VERSION, kong_version))

    # Default return values
    changed = False
    resp = ''

    # Ensure the API is registered in Kong
    if state == "present":

        # Check if the API exists
        orig = k.api_get(name)
        if orig is not None:

            # Diff the remote API object against the target data if it already exists
            apidiff = dotdiff(orig, data)

            # Set changed flag if there's a diff
            if apidiff:
                # Log modified state and diff result
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(apidiff))]

        else:
            # We're inserting a new API, set changed
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=name, after=data
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                resp = k.api_apply(**data)
            except Exception as e:
                ansible_module.fail_json(msg='Error applying API: {}'.format(e.message))

    # Ensure the API is deleted
    if state == "absent":

        # Check if the API exists
        orig = k.api_get(name)

        # Predict a change if the API exists
        if orig:
            changed = True
            result['state'] = 'deleted'
            result['diff'] = dict(
                before_header=name, before=orig,
                after_header='<deleted>', after='<deleted>\n'
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and orig:
            # Issue delete call to the Kong API
            try:
                resp = k.api_delete(name)
            except Exception as e:
                ansible_module.fail_json(msg='Error deleting API: {}'.format(e.message))

    # Pass through the API response if non-empty
    if resp:
        result['response'] = resp

    # Prepare module output
    result.update(
        dict(
            changed=changed,
        )
    )

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()
