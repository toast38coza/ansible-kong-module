#!/usr/bin/python

import requests

class KongConsumer:

    def __init__(self, base_url):
        self.base_url = "{}/consumers" . format(base_url)
        

    def list(self):
    	return requests.get(self.base_url)

    def add(self, username=None, custom_id=None):
    	
    	assert [username, custom_id] != [None, None], \
    		'Please provide at least one of username or custom_id'

    	data = {}
    	if username is not None:
    		data['username'] = username
    	if custom_id is not None:
    		data['custom_id'] = custom_id

    	return requests.post(self.base_url, data)

    def delete(self, id):
    	url = "{}/{}" . format (self.base_url, id)
    	return requests.delete(url)

class ModuleHelper:
    
    def get_module(self):

        args = dict(
            kong_admin_uri = dict(required=True, type='str'),
            username = dict(required=False, type='str'),
            custom_id = dict(required=False, type='str'),
            state = dict(required=False, default="present", choices=['present', 'absent', 'list'], type='str'),    
        )
        return AnsibleModule(argument_spec=args,supports_check_mode=False)

    def prepare_inputs(self, module):
        url = module.params['kong_admin_uri']
        state = module.params['state']    
        username = module.params.get('username', None)
        custom_id = module.params.get('custom_id', None)
        
        return (url, username, custom_id, state)

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
    base_url, username, id, state = helper.prepare_inputs(module)

    api = KongConsumer(base_url)
    if state == "present":
        response = api.add(username, id)
    if state == "absent":
        response = api.delete(username)
    if state == "list":
        response = api.list()
    
    has_changed, meta = helper.get_response(response, state)
    module.exit_json(changed=has_changed, meta=meta)


from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()