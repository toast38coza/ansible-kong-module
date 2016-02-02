import unittest, responses, requests, json, mock
from urlparse import parse_qsl, parse_qs
from kong_plugin import KongPlugin, \
	prepare_inputs, get_response


mock_kong_admin_url = "http://192.168.99.100:8001"

class KongPluginTestCase(unittest.TestCase):

	def setUp(self):
		self.api = KongPlugin(mock_kong_admin_url, "mockbin")

	@responses.activate
	def test_plugin_add(self):

		expected_url = "{}/apis/mockbin/plugins" . format (mock_kong_admin_url)
		responses.add(responses.POST, expected_url, status=201)
		
		example_data = {		
			"name":"request-transformer",
			"config": {
				"config.add.headers":"x-new-header:some_value, x-another-header:some_value",
				"config.add.querystring":"new-param:some_value, another-param:some_value",
				"config.add.form":"new-form-param:some_value, another-form-param:some_value",
				"config.remove.headers":"x-toremove, x-another-one",
				"config.remove.querystring":"param-toremove, param-another-one",
				"config.remove.form":"formparam-toremove, formparam-another-one"
			}
		}
		response = self.api.add_or_update(**example_data)

		assert response.status_code == 201, \
			"Expect 201 Created, got: {}: {}" . format (response.status_code, response.content)

	@responses.activate
	def test_plugin_delete(self):

		id = "123"
		expected_url = "{}/apis/mockbin/plugins/{}" . format (mock_kong_admin_url, id)
		responses.add(responses.DELETE, expected_url, status=204)
		
		self.api.delete(id)

class MainTestCase(unittest.TestCase):

	def setUp(self):
		class MockModule:
			pass

		self.module = MockModule
		self.module.params = {
			"kong_admin_uri": mock_kong_admin_url,
	        "state": "present",
	        "api_name": "mockbin",
	        "plugin_name": "request-transformer",
	        "config": {
	        	"foo": "bar"
	        }
		}
	def test_create_plugin(self):
		pass

	def test_prepare_inputs(self):

		base_url, api_name, data, state = prepare_inputs(self.module)

		assert api_name == 'mockbin', 'Expect api_name to be mockbin. Got: {}' . format (api_name)
		assert base_url == mock_kong_admin_url
		assert state == "present"

		expected_keys = ['name', 'config']
		for expected_key in expected_keys:
			assert data.get(expected_key, None) is not None

		assert data.get("config") == {"foo": "bar"}

	def test_handle_response_present_201(self):
		
		mock_response = requests.Response()
		mock_response.status_code = 201

		has_changed, meta = get_response(mock_response, "present")

		assert has_changed == True

	def test_handle_response_present_not_201(self, ):
		
		mock_response = requests.Response()
		mock_response.status_code = 409

		has_changed, meta = get_response(mock_response, "present")

		assert has_changed == False

	def test_handle_response_absent_204(self):
		
		mock_response = requests.Response()
		mock_response.status_code = 204

		has_changed, meta = get_response(mock_response, "absent")

		assert has_changed == True

	def test_handle_response_absent_not_204(self, ):
		
		mock_response = requests.Response()
		mock_response.status_code = 409

		has_changed, meta = get_response(mock_response, "absent")

		assert has_changed == False


if __name__ == '__main__':
    unittest.main()   