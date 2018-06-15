#!/usr/bin/python

DOCUMENTATION = '''
---
module: kong_routes
short_description: Configure Kong Routes

'''

EXAMPLES = '''
- name: Add a route
  kong_routes: 
    kong_admin_uri: http://127.0.0.1:8001/
    serviceid: "05350c14-21f5-4cf5-acc8-684bbfb3de83"
    state: present
    protocols: ["https"]
    methods: ["GET"]
    hosts: ["example.com"]
    paths: ['/my-path']

- name: Delete a route
  kong_routes:
    kong_admin_uri: http://127.0.0.1:8001/
    routeid: ""206404e6-e382-43f8-86cf-8bd1926fe285"
    state: absent

'''

import json, requests, os

class KongRoutes:

    def __init__(self, base_url, auth_username=None, auth_password=None):
        self.base_url = base_url
        if auth_username is not None and auth_password is not None:
            self.auth = (auth_username, auth_password)
        else:
            self.auth = None

    def __url(self, path):
        return "{}{}" . format (self.base_url, path)

    def _route_exists(self, name, route_list):
        for route in route_list:
            if name == route.get("name", None):
                return True 
        return False

    def add_or_update(self, protocols, serviceid, routeid=None, hosts=None, paths=None, methods=None, strip_path=True, preserve_host=False):

        method = "post"        
        kong_url = self.__url("/routes/")
        # DESCOMENTEI ISTO
        # route_list = self.list().json().get("data", [])
        # route_exists = self._route_exists(service, route_list)

        # if route_exists:
        if routeid is not None:
            method = "patch"
            kong_url = "{}{}" . format (kong_url, routeid)
        # NOVO
        headers = {'Content-type': 'application/json'}

        data = {
            "protocols": protocols,
            "methods": methods,
            "hosts": hosts,
            "paths": paths,
            "strip_path": strip_path,
            "service": {
                "id": serviceid
            },
            "preserve_host": preserve_host
        }

        return getattr(requests, method)(kong_url, json=data, headers=headers, auth=self.auth)
        

    def list(self):
        url = self.__url("/routes")
        return requests.get(url, auth=self.auth)

    def list_by_service(self, id):
        url = self.__url("/services/{}/routes" . format (id))
        return requests.get(url, auth=self.auth)

    def info(self, id):
        url = self.__url("/routes/{}" . format (id))
        return requests.get(url, auth=self.auth)

    def delete_by_name(self, name):
        info = self.info(name)
        id = info.json().get("id")
        return self.delete(id)

    def delete(self, id):
        path = "/routes/{}" . format (id)
        url = self.__url(path)
        return requests.delete(url, auth=self.auth)

    def delete_by_service(self, id):
        url = self.__url("/services/{}/routes" . format (id))
        info = requests.get(url, auth=self.auth)
        routes = info.json().get("data")
        for route in routes:
            self.delete(route.get("id"))
        return info

class ModuleHelper:

    def __init__(self, fields):
        self.fields = fields
    
    def get_module(self):

        args = dict(
            kong_admin_uri = dict(required=False, type='str'),
            kong_admin_username = dict(required=False, type='str'),
            kong_admin_password = dict(required=False, type='str'),
            protocols = dict(required=False, type='list'),
            methods = dict(required=False, type='list'),
            hosts = dict(required=False, type='list'),    
            paths = dict(required=False, type='list'),    
            strip_path = dict(required=False, type='bool'),    
            preserve_host = dict(required=False, type='bool'),    
            service = dict(required=False, type='dict'),    
            state = dict(required=False, default="present", choices=['present', 'absent', 'latest', 'list', 'info'], type='str'),    
            serviceid = dict(required=False, type='str'),
            routeid = dict(required=False, type='str'),
        )
        return AnsibleModule(argument_spec=args,supports_check_mode=False)

    def prepare_inputs(self, module):
        url = module.params['kong_admin_uri']
        auth_user = module.params['kong_admin_username']
        auth_password = module.params['kong_admin_password']
        state = module.params['state']
        data = {}

        for field in self.fields:
            value = module.params.get(field, None)
            if value is not None:
                data[field] = value

        return (url, data, state, auth_user, auth_password)

    def get_response(self, response, state):

        if state == "present":
            meta = response.json()
            has_changed = response.status_code in [201, 200]
            
        if state == "absent":
            meta = {}
            has_changed = response.status_code == 204

        if state == "list":
            meta = response.json()
            has_changed = False

        return (has_changed, meta)

def main():

    fields = [
        'protocols', 
        'methods', 
        'hosts',
        'paths',
        'strip_path',
        'preserve_host',
        'serviceid',
        'routeid',
        'service'
    ]

    helper = ModuleHelper(fields)

    global module # might not need this
    module = helper.get_module()  
    base_url, data, state, auth_user, auth_password = helper.prepare_inputs(module)

    route = KongRoutes(base_url, auth_user, auth_password)
    if state == "present":
        response = route.add_or_update(**data)
    if state == "absent":
        if data.get("serviceid") is not None:
            response = route.delete_by_service(data.get("serviceid"))
        else:
            #response = route.delete(data.get("service").get("id"))
            response = route.delete(data.get("routeid"))
    if state == "list":
        if data.get("serviceid") is not None:
            response = route.list_by_service(data.get("serviceid"))
        else:
            response = route.list()

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

