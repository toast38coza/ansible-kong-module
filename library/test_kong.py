import unittest, responses, json, mock, requests
from urlparse import parse_qsl, parse_qs
from kong_api import KongAPI, ModuleHelper, main
from ansible.module_utils.basic import AnsibleModule

mock_kong_admin_url = "http://192.168.99.100:8001"

class ModuleHelperTestCase(unittest.TestCase):

	def setUp(self):
		class MockModule: 
			pass
		fields = [
            "name", 
            "upstream_url", 
            "request_host", 
            "request_path", 
            "strip_request_path", 
            "preserve_host"
        ]
		self.helper = ModuleHelper(fields)
		self.module = MockModule()
		self.module.params = {
			"kong_admin_uri": mock_kong_admin_url,
            "name": "mockbin", 
            "request_host": "mockbin.com", 
            "request_path": "/mockbin", 
            "strip_request_path": True, 
            "preserve_host": False,
            "upstream_url": "http://mockbin.com",
			"state": "present"
		}

	def test_prepare_inputs(self):
		
		url, data, state = self.helper.prepare_inputs(self.module)

		assert url == mock_kong_admin_url
		assert state == "present"
		for field in self.helper.fields:
			value = data.get(field, None)
			assert value is not None, \
				"Expect field {} to be set. Actual value was {}" . format (field, value)



class MainTestCase(unittest.TestCase):

	def setUp(self):
		class MockModule: 
			pass

		fields = [
	        'name', 
	        'upstream_url', 
	        'request_host',
	        'request_path',
	        'strip_request_path',
	        'preserve_host'
	    ]

		self.helper = ModuleHelper(fields)
		self.module = MockModule()
		self.module.params = {
			"kong_admin_uri": "http://192.168.99.100:8001",
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com"
		}

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongAPI, 'add_or_update')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_add(self, mock_prepare_inputs, mock_module, mock_add, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, {}, "present")
		mock_get_response.return_value = (True, {})
		main()

		assert mock_add.called		

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongAPI, 'delete_by_name')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_delete(self, mock_prepare_inputs, mock_module, mock_delete, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, {}, "absent")
		mock_get_response.return_value = (True, {})
		main()

		assert mock_delete.called	

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongAPI, 'list')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_add(self, mock_prepare_inputs, mock_module, mock_list, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, {}, "list")
		mock_get_response.return_value = (True, {})
		main()

		assert mock_list.called			



class KongAPITestCase(unittest.TestCase):

	def setUp(self):
		self.api = KongAPI(mock_kong_admin_url)

	def test__api_exists(self):
		api_list = [
			{"name": "foo"},
			{"name": "bar"},
		]
		exists = self.api._api_exists("foo", api_list)
		assert exists == True

	def test__api_doesnt_exist(self):
		api_list = [
			{"name": "foo"},
			{"name": "bar"},
		]
		exists = self.api._api_exists("baz", api_list)
		assert exists == False

	@responses.activate
	def test_api_add_new(self):
		
		api_list = {'data': [
			{"name": "foo"},
			{"name": "bar"},
		]}
		expected_url = '{}/apis' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=201, body=json.dumps(api_list))

		expected_url = '{}/apis/' . format (mock_kong_admin_url)
		responses.add(responses.POST, expected_url, status=201)

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com",
			"request_path" : "/mockbin" 
		}
		response = self.api.add_or_update(**request_data)

		assert response.status_code == 201

		data = parse_qs(responses.calls[1].request.body)
		expected_keys = ['name', 'upstream_url', 'request_host', 'request_path', 'strip_request_path', 'preserve_host']
		for key in expected_keys:
			assert data.get(key, None) is not None, \
				"Expect all required data to have been sent. What was actually sent: {}" . format (data)

	@responses.activate
	def test_api_add_update(self):
		
		api_list = {'data': [
			{"name": "foo"},
			{"name": "bar"},
			{"name": "mockbin"}
		]}
		expected_url = '{}/apis' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=201, body=json.dumps(api_list))

		expected_url = '{}/apis/mockbin' . format (mock_kong_admin_url)
		responses.add(responses.PATCH, expected_url, status=201)

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com",
			"request_path" : "/mockbin" 
		}
		response = self.api.add_or_update(**request_data)

		assert response.status_code == 201

		data = parse_qs(responses.calls[1].request.body)
		expected_keys = ['name', 'upstream_url', 'request_host', 'request_path', 'strip_request_path', 'preserve_host']
		for key in expected_keys:
			assert data.get(key, None) is not None, \
				"Expect all required data to have been sent. What was actually sent: {}" . format (data)

	@responses.activate
	def test_list_apis(self):
		expected_url = '{}/apis' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=200)
		
		response = self.api.list()
		assert response.status_code == 200

	@responses.activate
	def test_api_info(self):
		expected_url = '{}/apis/123' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_url, status=200)
		response = self.api.info("123")

		assert response.status_code == 200

	@responses.activate
	def test_api_delete(self):

		expected_url = '{}/apis/123' . format (mock_kong_admin_url)
		responses.add(responses.DELETE, expected_url, status=204)
		response = self.api.delete("123")

		assert response.status_code == 204

	@responses.activate
	def test_api_delete_by_name(self):

		expected_get_url = '{}/apis/mockbin' . format (mock_kong_admin_url)
		get_body_response = {
			"upstream_url": "https://api.github.com",
			"id": "123",
			"name": "Github",
			"created_at": 1454348543000,
			"request_host": "github.com"
		}
		expected_del_url = '{}/apis/123' . format (mock_kong_admin_url)
		responses.add(responses.GET, expected_get_url, status=200, body=json.dumps(get_body_response))
		responses.add(responses.DELETE, expected_del_url, status=204)
		
		response = self.api.delete_by_name("mockbin")

		assert response.status_code == 204, \
			"Expect 204 DELETED response. Got: {}: {}" . format (response.status_code, response.content)

		
class IntegrationTests(unittest.TestCase):

	def setUp(self):
		self.api = KongAPI("http://192.168.99.100:8001")

	@unittest.skip("integration")
	def test_add_api(self):

		request_data = {
			"name":"mockbin", 
			"upstream_url":"http://mockbin.com", 
			"request_host" : "mockbin.com",
			"request_path" : "/mockbin",
			"strip_request_path": True
		}
		response = self.api.add_or_update(**request_data)
		import pdb;pdb.set_trace()
		assert response.status_code in [201, 409], \
			"Expect status 201 Created. Got: {}: {}" . format (response.status_code, response.content)

if __name__ == '__main__':
    unittest.main()