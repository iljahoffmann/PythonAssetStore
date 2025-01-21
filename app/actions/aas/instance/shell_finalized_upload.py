import json
import base64
import requests

from lib.fsutil import apply_replacements
from lib.project_path import ProjectPath
from lib.visit_json import JsonVisitor
from lib.path_op import TreePath, path_get, path_set

from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help

from app.aas_demo_generator import create_demo_aasx
from app.actions.aas.instance.upload_instance import AASInstancePut, AASInstanceDownload, AASInstanceUpload


def get_base64_pcf_id(product, serial_number):
	the_id = f"https://aas.murrelektronik.com/{product}/sm/1/0/{serial_number}/carbonfootprint"
	encoded = base64.b64encode(the_id.encode())
	return encoded.decode().replace('=', '')    # drop padding


def get_pcf_url(product, serial_number):
	pcf_id = get_base64_pcf_id(product, serial_number)
	url = f"http://193.111.103.55:8082/submodels/{pcf_id}/submodel-elements/ProductCarbonFootprints"
	return url


def get_external_product_base(product, serial_number):
	the_id = f"https://aas.murrelektronik.com/{product}/aas/1/0/{serial_number}"
	encoded = base64.b64encode(the_id.encode())
	return encoded.decode().replace('=', '')    # drop padding


def get_external_product_shell_url(product, serial_number):
	product_shell_id = get_external_product_base(product, serial_number)
	url = f"http://193.111.103.55:8082/shells/{product_shell_id}"
	return url


def external_shell_exists(product, serial_number):
	shell_url = get_external_product_shell_url(product, serial_number)
	try:
		print(shell_url)
		response = requests.get(shell_url)
		return 200 <= response.status_code < 300
	except Exception as ex:
		x = str(ex)
		return False


def get_external_upload_url():
	url = f"http://193.111.103.55:8082/upload"
	return url


# "http://deopp-aasinst-01/58841/sm/0/0/2017123456789/timeseries"
# http://193.111.103.55:8082/submodels/aHR0cHM6Ly9hYXMubXVycmVsZWt0cm9uaWsuY29tLzU0NTMwL3NtLzEvMC8yMDE3MTIzNDU2Nzg5L2NhcmJvbmZvb3RwcmludA==/submodel-elements/ProductCarbonFootprints
# "https://aas.murrelektronik.com/54530/sm/1/0/2017123456789/carbonfootprint"


class LocatePath(JsonVisitor):
	def __init__(self, predicate, find_all=False):
		super().__init__()
		self.predicate = predicate
		self.find_all = find_all
		self.found = None if not find_all else []
		self.stack = []

	def _enter_dict(self, json_data, **kwargs):
		self.stack.append(kwargs['key'])
		if self.predicate(json_data):
			path = TreePath(self.stack[1:], clone=True)
			if self.find_all:
				self.found.append(path)
			else:
				self.found = path

		return self.find_all or self.found is None

	def _leave_dict(self, json_data, **kwargs):
		self.stack.pop()
		pass

	def _enter_list(self, json_data, **kwargs):
		self.stack.append(kwargs['key'])
		pass

	def _leave_list(self, json_data, **kwargs):
		self.stack.pop()
		pass


class ShellFinalizer(StatelessAction):
	def _get_current_pcf(self, asset, context, product, serial_number):
		pcf_url = get_pcf_url(product, serial_number)
		info = AASInstanceDownload().execute(asset, context, pcf_url)
		response = info.get_result().content
		info_json = json.loads(response.decode())
		return info_json

	@staticmethod
	def _is_correct_submodel(d):
		return d.get('value') == 'A3 - production'


	@staticmethod
	def _is_pcf_entry(d):
		return d.get('idShort') == 'PcfCO2eq'


	@staticmethod
	def upload_empty_shell(asset, context: UpdateContext, product, serial_number, pcf):
		path_to_shell = create_demo_aasx(product, serial_number, 'external', pcf)
		upload_url = get_external_upload_url()
		info = AASInstanceUpload().execute(
			asset, context,
			upload_url,
			file=path_to_shell,
			mime_type='multipart/form-data'
		)
		response = info.get_result().content
		pass


	def execute(
			self,
			asset,
			context: UpdateContext,
			product: str,
			serial_number: str,
			footprint: str=None,
			**kwargs
	):
		self.upload_empty_shell(asset, context, product, serial_number, footprint)
		# pcf = self._get_current_pcf(asset, context, product, serial_number)
		# sm_locator = LocatePath(self._is_correct_submodel)
		# sm_locator.accept(pcf)
		# pcf_locator = LocatePath(self._is_pcf_entry, find_all=True)
		# pcf_locator.accept(pcf)
		# entry_path = sm_locator.found
		# model_index = entry_path[1]
		# pcf_path = pcf_locator.found[model_index]
		# pcf_entry = path_get(pcf, pcf_path)
		# pcf_entry['value'] = float(footprint)
		#
		# pcf_url = get_pcf_url(product, serial_number)
		# info = AASInstancePut().execute(
		# 	asset, context,
		# 	pcf_url,
		# 	data=json.dumps(pcf),
		# 	mime_type='application/json'
		# )
		redirect_page = context.store.query(context, 'www.files', file='instance_demo/redirect_to_start.html').get_result()
		return redirect_page

	def get_help(self):
		pass
