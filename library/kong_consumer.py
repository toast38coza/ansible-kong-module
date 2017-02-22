#!/usr/bin/python

import requests

class KongConsumer:

    def __init__(self, base_url, auth_username=None, auth_password=None):
        self.base_url = "{}/consumers" . format(base_url)
        if auth_username is not None and auth_password is not None:
            self.auth = (auth_username, auth_password)
        else:
            self.auth = None

    def list(self):
    	return requests.get(self.base_url, auth=self.auth)

    def add(self, username=None, custom_id=None):
    	
    	assert [username, custom_id] != [None, None], \
    		'Please provide at least one of username or custom_id'

    	data = {}
    	if username is not None:
    		data['username'] = username
    	if custom_id is not None:
    		data['custom_id'] = custom_id

    	return requests.post(self.base_url, data, auth=self.auth)

    def delete(self, id):
    	url = "{}/{}" . format (self.base_url, id)
    	return requests.delete(url, auth=self.auth)

    def configure_for_plugin(self, username_or_id, api, data):
        """This could possibly go in it's own plugin"""

        url = "{}/{}/{}" . format (self.base_url, username_or_id, api)
        return requests.post(url, data, auth=self.auth)

class ModuleHelper:
    
    def get_module(self):

        args = dict(
            kong_admin_uri = dict(required=True, type='str'),
            kong_admin_username = dict(required=False, type='str'),
            kong_admin_password = dict(required=False, type='str'),
            username = dict(required=False, type='str'),
            custom_id = dict(required=False, type='str'),
            state = dict(required=False, default="present", choices=['present', 'absent', 'list', 'configure'], type='str'),    
            data = dict(required=False, type='dict'),
            api_name = dict(required=False, type='str'),
        )
        return AnsibleModule(argument_spec=args,supports_check_mode=False)

    def prepare_inputs(self, module):
        url = module.params['kong_admin_uri']
        auth_user = module.params['kong_admin_username']
        auth_password = module.params['kong_admin_password']
        state = module.params['state']    
        username = module.params.get('username', None)
        custom_id = module.params.get('custom_id', None)
        data = module.params.get('data', None)
        api_name = module.params.get('api_name', None)
        
        return (url, username, custom_id, state, api_name, data, auth_user, auth_password)

    def get_response(self, response, state):

        if state in ["present", "configure"]:
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

    helper = ModuleHelper()

    global module # might not need this
    module = helper.get_module()  
    base_url, username, id, state, api_name, data, auth_user, auth_password = helper.prepare_inputs(module)

    api = KongConsumer(base_url, auth_user, auth_password)
    if state == "present":
        response = api.add(username, id)
    if state == "absent":
        response = api.delete(username)
    if state == "configure":
        response = api.configure_for_plugin(username, api_name, data)
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