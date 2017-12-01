from ansible.module_utils.kong import Kong
from ansible.module_utils.helpers import version_compare
from ansible.module_utils.basic import *


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

    def params_fields_lookup(self, module):

        # Look up all keys mentioned in 'fields' in the module parameters, get their values
        return {x: module.params[x] for x in self.fields if module.params.get(x, None) is not None}

    def get_response(self, response, state):

        meta = {}
        has_changed = False

        return (has_changed, meta)

def main():

    module = AnsibleModule(
        argument_spec = dict(
            kong_admin_uri = dict(required=True, type='str'),
            kong_admin_username = dict(required=False, type='str'),
            kong_admin_password = dict(required=False, type='str'),
            name = dict(required=True, type='str'),
            upstream_url = dict(required=False, type='str'),
            hosts = dict(required=False, type='list'),
            uris = dict(required=False, type='list'),
            methods = dict(required=False, type='list'),
            strip_uri = dict(required=False, default=False, type='bool'),
            preserve_host = dict(required=False, default=False, type='bool'),
            state = dict(required=False, default="present", choices=['present', 'absent'], type='str'),
        ),
        required_if=[
            ('state', 'present', ['upstream_url'])
        ],
        supports_check_mode=True
    )

    result = {}

    # Emulates 'required_one_of' argument spec, as it cannot be made conditional
    if module.params['state'] == 'present' and \
        module.params['hosts'] is None and \
        module.params['uris'] is None and \
        module.params['methods'] is None:
        module.fail_json(msg="At least one of hosts, uris or methods is required when state is 'present'")

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
    data = b.params_fields_lookup(module)

    # Admin endpoint & auth
    url = module.params['kong_admin_uri']
    auth_user = module.params['kong_admin_username']
    auth_pass = module.params['kong_admin_password']

    # Target state
    state = module.params['state']

    # Create Kong client instance
    k = Kong(url, auth_user=auth_user, auth_pass=auth_pass)

    kong_version = k.version
    if not version_compare(kong_version, MIN_VERSION):
        module.warn('Module supports Kong {} and up (found {})'.format(MIN_VERSION, kong_version))

    if state == "present":
        r = k.api_apply(**data)

        result.update(
            dict(
                changed=None,
                response=r
            )
        )

    # Ensure the API is deleted
    if state == "absent":
        r = k.api_delete(data.get("name"))

        result.update(
            dict(
                changed=r
            )
        )

    module.exit_json(**result)

if __name__ == '__main__':
    main()

