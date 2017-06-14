#!/usr/bin/python

import requests

class KongPlugin:

    def __init__(self, base_url, api_name, auth_username=None, auth_password=None):
        self.base_url = "{}/apis/{}/plugins" . format(base_url, api_name)
        if auth_username is not None and auth_password is not None:
            self.auth = (auth_username, auth_password)
        else:
            self.auth = None
        self.api = api_name

    def list(self):
        
        return requests.get(self.base_url, auth=self.auth)

    def _get_plugin_id(self, name, plugins_list):
        """Scans the list of plugins for an ID. 
        returns None if no matching name is found"""

        for plugin in plugins_list:
            if plugin.get("name") == name:
                return plugin.get("id")

        return None

    def add_or_update(self, name, config=None):
        
        # does it exist already?
        plugins_response = self.list()
        plugins_list = plugins_response.json().get('data', [])

        data = {
            "name": name,
        }
        if config is not None:
            data.update(config)   

        plugin_id = self._get_plugin_id(name, plugins_list)
        if plugin_id is None:            
            return requests.post(self.base_url, data, auth=self.auth)
        else:
            url = "{}/{}" . format (self.base_url, plugin_id)
            return requests.patch(url, data, auth=self.auth)

    def delete(self, id):

        url = "{}/{}" . format (self.base_url, id)
        return requests.delete(url, auth=self.auth)


class ModuleHelper:
    
    def get_module(self):

        args = dict(
            kong_admin_uri = dict(required=True, type='str'),
            kong_admin_username = dict(required=False, type='str'),
            kong_admin_password = dict(required=False, type='str'),
            api_name = dict(required=False, type='str'),
            plugin_name = dict(required=False, type='str'),
            plugin_id = dict(required=False, type='str'),
            config = dict(required=False, type='dict'),
            state = dict(required=False, default="present", choices=['present', 'absent', 'list'], type='str'),    
        )
        return AnsibleModule(argument_spec=args,supports_check_mode=False)

    def prepare_inputs(self, module):
        url = module.params['kong_admin_uri']
        auth_user = module.params['kong_admin_username']
        auth_password = module.params['kong_admin_password']
        api_name = module.params['api_name']
        state = module.params['state']    
        data = {
            "name": module.params['plugin_name'], 
            "config": module.params['config']        
        }

        return (url, api_name, data, state, auth_user, auth_password)

    def get_response(self, response, state):

        if state == "present":
            meta = json.dumps(response.content)
            has_changed = response.status_code == 201
            
        if state == "absent":
            meta = {}
            has_changed = response.status_code == 204

        if state == "list":
            meta = response.json()
            has_changed = False

        return (has_changed, meta)

    
def main():

    state_to_method = {
        "present": "add",
        "absent": "delete"
    }
    helper = ModuleHelper()

    global module # might not need this
    module = helper.get_module()
    base_url, api_name, data, state, auth_user, auth_password = helper.prepare_inputs(module)

    method_to_call = state_to_method.get(state)

    api = KongPlugin(base_url, api_name, auth_user, auth_password)
    if state == "present":
        response = api.add_or_update(**data)
    if state == "absent":
        response = api.delete(module.params['plugin_id'])
    if state == "list":
        response = api.list()

    if response.status_code == 401:
        module.fail_json(msg="Please specify kong_admin_username and kong_admin_password", meta=response.json())
    elif response.status_code == 403:
        module.fail_json(msg="Please check kong_admin_username and kong_admin_password", meta=response.json())
    else:
        has_changed, meta = helper.get_response(response, state)
        module.exit_json(changed=has_changed, meta=meta)


from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()        