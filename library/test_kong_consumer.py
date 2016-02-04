import unittest, responses, requests, json, mock
from mock import call
from urlparse import parse_qsl, parse_qs
from kong_consumer import KongConsumer, ModuleHelper, main

from ansible.module_utils.basic import *

# python3 compatible imports:
from six.moves.urllib.parse import parse_qsl, parse_qs



mock_kong_admin_url = "http://192.168.99.100:8001"

class KongPluginTestCase(unittest.TestCase):

	def setUp(self):
		self.api = KongConsumer(mock_kong_admin_url)

	@responses.activate
	def test_list(self):
		expected_url = "{}/consumers" . format(mock_kong_admin_url)
		responses.add(responses.GET, expected_url)
		response = self.api.list()

	@responses.activate
	def test_delete(self):
		
		expected_url = "{}/consumers/{}" . format(mock_kong_admin_url, 123)
		responses.add(responses.DELETE, expected_url, status=204)
		response = self.api.delete(123)

		assert response.status_code == 204

	@responses.activate 
	def test_add(self):

		expected_url = "{}/consumers" . format(mock_kong_admin_url)
		responses.add(responses.POST, expected_url, status=201)

		response = self.api.add(username='joesoap')
		assert response.status_code == 201


	@responses.activate
	def test_configure_for_plugin(self):

		expected_url = "{}/consumers/joe/auth-key" . format (mock_kong_admin_url)
		responses.add(responses.POST, expected_url, status=201)

		data = { "key": "123" }
		response = self.api.configure_for_plugin("joe", "auth-key", data)

		assert response.status_code == 201

		body = parse_qs(responses.calls[0].request.body)
		body_exactly = parse_qsl(responses.calls[0].request.body)
		assert body['key'][0] == "123", \
			"Expect correct. data to be sent. Got: {}" . format (body_exactly)

	@responses.activate 
	def test_add_invalid_inputs(self):
		self.assertRaises(AssertionError, self.api.add)

class ModuleHelperTestCase(unittest.TestCase):

	def setUp(self):
		self.helper = ModuleHelper()

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'add')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_add(self, mock_prepare_inputs, mock_module, mock_add, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "present", None, None)
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_add.called		

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'delete')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_delete(self, mock_prepare_inputs, mock_module, mock_delete, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "absent", None, None)
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_delete.called		
	
	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'list')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_list(self, mock_prepare_inputs, mock_module, mock_list, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "list", None, None)
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_list.called			

	@mock.patch.object(ModuleHelper, 'get_response')
	@mock.patch.object(AnsibleModule, 'exit_json')
	@mock.patch.object(KongConsumer, 'configure_for_plugin')
	@mock.patch.object(ModuleHelper, 'get_module')
	@mock.patch.object(ModuleHelper, 'prepare_inputs')
	def test_main_list(self, mock_prepare_inputs, mock_module, mock_configure_for_plugin, mock_exit_json, mock_get_response):

		mock_prepare_inputs.return_value = (mock_kong_admin_url, "1","joesoap", "configure", "auth-key", {"key": "123"})
		mock_get_response.return_value = (True, requests.Response())
		main()

		assert mock_configure_for_plugin.called				

		expected_call = call('1', 'auth-key', {'key': '123'})
		assert mock_configure_for_plugin.call_args_list[0] == expected_call


	def test_prepare_inputs(self):
		class MockModule:
			pass

		mock_module = MockModule()
		mock_module.params = {
			'kong_admin_uri': mock_kong_admin_url,
			'state': 'present',
			'username': 'joesoap',
		}
		url, username, id, state, api_name, data = self.helper.prepare_inputs(mock_module)

		assert url == mock_kong_admin_url
		assert state == 'present'
		assert username == 'joesoap'
		assert id == None
		assert data is None



if __name__ == '__main__':
    unittest.main()   