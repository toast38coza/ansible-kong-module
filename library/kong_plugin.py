#!/usr/bin/python

import requests

class KongPlugin:

    def __init__(self, base_url, api_name):
        self.base_url = "{}/apis/{}/plugins" . format(base_url, api_name)
        self.api = api_name

    def add(self, name, config):
        
        data = {
            "name": name,
        }
        data.update(config)   
  
        return requests.post(self.base_url, data)

    def add_or_update(self, name, config):

        return self.add(name, config)

    def delete(self, id):

        url = "{}/{}" . format (self.base_url, id)
        return requests.delete(url)


def get_module():

    args = dict(
        kong_admin_uri = dict(required=False, type='str'),
        api_name = dict(required=False, type='str'),
        plugin_name = dict(required=False, type='str'),
        plugin_id = dict(required=False, type='str'),
        config = dict(required=False, type='dict'),
        state = dict(required=False, default="present", choices=['present', 'absent'], type='str'),    
    )
    return AnsibleModule(argument_spec=args,supports_check_mode=False)

def prepare_inputs(module):
    url = module.params['kong_admin_uri']
    api_name = module.params['api_name']
    state = module.params['state']    
    data = {
        "name": module.params['plugin_name'], 
        "config": module.params['config']        
    }

    return (url, api_name, data, state)

def get_response(response, state):

    if state == "present":
        meta = json.dumps(response.content)
        has_changed = response.status_code == 201
        
    if state == "absent":
        meta = {}
        has_changed = response.status_code == 204

    return (has_changed, meta)

    
def main():

    state_to_method = {
        "present": "add",
        "absent": "delete"
    }

    global module # might not need this
    module = get_module()  
    base_url, api_name, data, state = prepare_inputs(module)

    method_to_call = state_to_method.get(state)

    api = KongPlugin(base_url, api_name)
    if state == "present":
        response = api.add(**data)
    if state == "absent":

        response = api.delete(module.params['plugin_id'])
    
    has_changed, meta = get_response(response, state)

    module.exit_json(changed=has_changed, meta=meta)


from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()        