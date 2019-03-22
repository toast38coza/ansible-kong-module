from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.helpers import *
from ansible.module_utils.kong.service import KongService

DOCUMENTATION = '''
---
module: kong_service
short_description: Configure a Kong Service object.
'''

EXAMPLES = '''
- name: Configure an Service
  kong_service:
    kong_admin_uri: http://localhost:8001
    name: Mockbin
    protocol: https
    host: mockbin.com
    state: present

- name: Delete an API
  kong_api:
    kong_admin_uri: http://localhost:8001
    name: Mockbin
    state: absent
'''

MIN_VERSION = '0.14.0'


def main():
    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            name=dict(required=True, type='str'),
            protocol=dict(required=False, default="http",
                          choices=['http', 'https'], type='str'),
            host=dict(required=True, type='str'),
            port=dict(required=False, default=80, type='int'),
            path=dict(required=False, type='str'),
            retries=dict(required=False, default=5, type='int'),
            connect_timeout=dict(required=False, default=60000, type='int'),
            write_timeout=dict(required=False, default=60000, type='int'),
            read_timeout=dict(required=False, default=60000, type='int'),
            state=dict(required=False, default="present",
                       choices=['present', 'absent'], type='str'),
        ),
        required_if=[
            ('state', 'present', ['host', 'name'])
        ],
        supports_check_mode=True
    )

    # Initialize output dictionary
    result = {}

    # Kong 0.14.x
    api_fields = [
        'name',
        'protocol',
        'host',
        'port',
        'path',
        'retries',
        'connect_timeout',
        'write_timeout',
        'read_timeout'
    ]

    # Extract api_fields from module parameters into separate dictionary
    data = params_fields_lookup(ansible_module, api_fields)

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract other arguments
    state = ansible_module.params['state']
    name = ansible_module.params['name']

    # Create KongService client instance
    k = KongService(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    kong_status_check(k, ansible_module)

    # Kong API version compatibility check
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''

    # Ensure the service is registered in Kong
    if state == "present":

        # Check if the service exists
        orig = k.service_get(name)
        if orig is not None:

            # Diff the remote API object against the target data if it already exists
            servicediff = dotdiff(orig, data)

            # Set changed flag if there's a diff
            if servicediff:
                # Log modified state and diff result
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(servicediff))]

        else:
            # We're inserting a new service, set changed
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=name, after=data
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                resp = k.service_apply(**data)
            except Exception as e:
                app_err = "Service configuration rejected by Kong: '{}'. " \
                          "Please check configuration of the service you are trying to configure."
                ansible_module.fail_json(msg=app_err.format(e))

    # Ensure the service is deleted
    if state == "absent":

        # Check if the service exists
        orig = k.service_get(name)

        # Predict a change if the service exists
        if orig:
            changed = True
            result['state'] = 'deleted'
            result['diff'] = dict(
                before_header=name, before=orig,
                after_header='<deleted>', after='\n'
            )

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and orig:
            # Issue delete call to the Kong service
            try:
                resp = k.service_delete(name)
            except Exception as e:
                ansible_module.fail_json(
                    msg='Error deleting service: {}'.format(e))

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
