"""
ansible.modules.kong.kong_service performs Service operations on the Kong Admin API.

:authors: Timo Beckers, Roman Komkov
:license: MIT
"""
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dotdiff import dotdiff
from ansible.module_utils.kong.helpers import (kong_status_check,
                                               kong_version_check,
                                               params_fields_lookup,
                                               render_list)
from ansible.module_utils.kong.service import KongService

DOCUMENTATION = '''
---
module: kong_service
short_description: Configure a Kong Service object.
'''

EXAMPLES = '''
- name: Configure a Service
  kong_service:
    kong_admin_uri: http://localhost:8001
    name: mockbin
    protocol: https
    host: mockbin.com

- name: Delete a Service
  kong_api:
    kong_admin_uri: http://localhost:8001
    name: mockbin
    state: absent
'''


def main():
    """Execute the Kong Service module."""
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

    # Create Kong client instance.
    k = KongService(url, auth_user=auth_user, auth_pass=auth_pass)
    kong_status_check(k, ansible_module)
    kong_version_check(k, ansible_module)

    # Default return values.
    result = {}
    changed = False
    resp = ''

    # Ensure the Service is configured.
    if state == "present":

        orig = k.service_get(name)
        if orig is not None:
            # Diff the existing object against the target data if it already exists.
            servicediff = dotdiff(orig, data)
            if servicediff:
                changed = True
                result['state'] = 'modified'
                result['diff'] = [dict(prepared=render_list(servicediff))]

        else:
            # Insert a new Service, set changed.
            changed = True
            result['state'] = 'created'
            result['diff'] = dict(
                before_header='<undefined>', before='<undefined>\n',
                after_header=name, after=data
            )

        if not ansible_module.check_mode and changed:
            try:
                resp = k.service_apply(**data)
            except requests.HTTPError as e:
                ansible_module.fail_json(
                    msg='Error applying Service: {}'.format(e))

    # Ensure the Service is deleted.
    if state == "absent":

        orig = k.service_get(name)
        if orig:
            changed = True
            result['state'] = 'deleted'
            result['diff'] = dict(
                before_header=name, before=orig,
                after_header='<deleted>', after='\n'
            )

        if not ansible_module.check_mode and orig:
            try:
                resp = k.service_delete(name)
            except requests.HTTPError as e:
                ansible_module.fail_json(
                    msg='Error deleting Service: {}'.format(e))

    # Prepare module output
    result.update(changed=changed)

    # Pass through the API response if non-empty
    if resp:
        result['response'] = resp

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()
