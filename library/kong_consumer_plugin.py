from ansible.module_utils.kong_consumer import KongConsumer
from ansible.module_utils.kong_helpers import *
from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = '''
---
module: kong_consumer_plugin
short_description: Configure a Kong Consumer Plugin object.
'''

EXAMPLES = '''
- name: Configure a Consumer's API key
  kong_consumer_plugin:
    kong_admin_uri: http://localhost:8001
    username: apiconsumer
    plugin: key-auth
    config:
      key: the-api-key
    state: present

The plugin configuration can be revoked by setting `state: absent`
on the resource. Since there can be an arbitrary amount of plugin
configurations for a Consumer, the `config` section needs to be identical.
'''

MIN_VERSION = '0.11.0'


def main():

    ansible_module = AnsibleModule(
        argument_spec=dict(
            kong_admin_uri=dict(required=True, type='str'),
            kong_admin_username=dict(required=False, type='str'),
            kong_admin_password=dict(required=False, type='str', no_log=True),
            username=dict(required=True, type='str'),
            plugin=dict(required=True, type='str'),
            config=dict(required=False, type='dict', default=dict()),
            state=dict(required=False, default="present", choices=['present', 'absent'], type='str'),
        ),
        supports_check_mode=True
    )

    # Initialize output dictionary
    result = {}

    # Admin endpoint & auth
    url = ansible_module.params['kong_admin_uri']
    auth_user = ansible_module.params['kong_admin_username']
    auth_pass = ansible_module.params['kong_admin_password']

    # Extract other arguments
    state = ansible_module.params['state']
    username = ansible_module.params['username']
    plugin = ansible_module.params['plugin']
    config = ansible_module.params['config']

    # Create KongConsumer client instance
    k = KongConsumer(url, auth_user=auth_user, auth_pass=auth_pass)

    # Contact Kong status endpoint
    kong_status_check(k, ansible_module)

    # Kong API version compatibility check
    kong_version_check(k, ansible_module, MIN_VERSION)

    # Default return values
    changed = False
    resp = ''
    diff = []

    # Check if the Consumer Plugin configuration exists
    cpq = k.consumer_plugin_query(username, plugin, config=config)
    if len(cpq) > 1:
        ansible_module.fail_json(
            msg='Got multiple results for Consumer Plugin query.',
            username=username, plugin=plugin, config=config)

    # Ensure the Consumer Plugins is configured
    if state == "present" and not cpq:

        # Insert a new Consumer Plugin configuration
        changed = True
        result['state'] = 'created'

        # Append diff entry
        diff.append(dict(
            before_header='<undefined>', before='<undefined>\n',
            after_header='{}/{}'.format(username, plugin), after=config
        ))

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and changed:
            try:
                # Apply changes to Kong
                resp = k.consumer_plugin_apply(username, plugin, config=config)

            except Exception as e:
                ansible_module.fail_json(msg='Consumer Plugin configuration rejected by Kong.', err=e.message)

    # Ensure the Consumer is deleted
    if state == "absent" and cpq:

        # Get the first (and only) element of the query
        orig = cpq[0]

        # Predict a successful delete if the Consumer Plugin is present
        changed = True
        result['state'] = 'deleted'

        diff.append(dict(
            before_header='{}/{}'.format(username, plugin), before=orig,
            after_header='<deleted>', after='\n'
        ))

        # Only make changes when Ansible is not run in check mode
        if not ansible_module.check_mode and orig:
            # Issue delete call
            try:
                resp = k.consumer_plugin_delete(consumer_idname=username, plugin_name=plugin, config=config)
            except Exception as e:
                ansible_module.fail_json(
                    msg='Error deleting Consumer Plugin.',
                    err=e.message)

    # Pass through the API response if non-empty
    if resp:
        result['response'] = resp

    # Pass through the diff result
    if diff:
        result['diff'] = diff

    # Prepare module output
    result.update(
        dict(
            changed=changed,
        )
    )

    ansible_module.exit_json(**result)


if __name__ == '__main__':
    main()
