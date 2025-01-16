import json
import base64

from lib.fsutil import apply_replacements
from lib.project_path import ProjectPath
from lib.visit_json import JsonVisitor

from lib.store.update_context import UpdateContext
from lib.store.action import StatelessAction
from lib.store.help import Help

from app.actions.aas.instance.upload_instance import AASInstancePut, AASInstanceDownload


def get_base64_timeseries_id(product, serial_number):
	the_id = f"http://deopp-aasinst-01/{product}/sm/0/0/{serial_number}/timeseries"
	encoded = base64.b64encode(the_id.encode())
	return encoded.decode().replace('=', '')    # drop padding


def get_timeseries_url(product, serial_number):
	timeseries_id = get_base64_timeseries_id(product, serial_number)
	url = f"http://deopp-aasinst-01:8082/submodels/{timeseries_id}/submodel-elements/Segments"
	return url


class LocateDict(JsonVisitor):
	def __init__(self, predicate):
		super().__init__()
		self.predicate = predicate
		self.found = None

	def _enter_dict(self, json_data, **kwargs):
		if self.predicate(json_data):
			self.found = json_data

		return self.found is None


class TraverseDict(JsonVisitor):
	def __init__(self, predicate, operation):
		super().__init__()
		self.predicate = predicate
		self.operation = operation

	def _enter_dict(self, json_data, **kwargs):
		if self.predicate(json_data):
			self.operation(json_data)

		return True


class InstanceDemoStep1(StatelessAction):
	def __init__(self):
		with open(ProjectPath.local('[]/data/InstanceDemo/phases.json'), 'r') as f:
			self.phases = json.load(f)

	def _get_current_timeseries(self, asset, context, product, serial_number):
		timeseries_url = get_timeseries_url(product, serial_number)
		info = AASInstanceDownload().execute(asset, context, timeseries_url)
		response = info.get_result().content
		info_json = json.loads(response.decode())
		return info_json

	def _initial_product_setup(self, asset, context, product, serial_number):
		# InternalSegment_PCB_Assembly
		timeseries_url = get_timeseries_url(product, serial_number)
		info = AASInstancePut().execute(
			asset, context,
			timeseries_url,
			file='[]/data/InstanceDemo/timeseries_empty.json',
			mime_type='application/json'
		)
		response = info.get_result().content
		pass

	@staticmethod
	def _is_carbon_entry(d):
		return 'idShort' in d and d['idShort'] == 'CO2Footprint_kg_per_kWh'

	def _add_phase_measurement(self, asset, context, product, serial_number, phase, footprint):
		current_model = self._get_current_timeseries(asset, context, product, serial_number)
		if 'value' not in current_model:
			current_model['value'] = []

		phase_name = self.phases[phase]
		fill_in_filename = f'[]/data/InstanceDemo/steps/{phase+1:02}_InternalSegment_{phase_name}.json'
		with open(ProjectPath.local(fill_in_filename), 'r') as f:
			fill_in = json.load(f)

		locator = LocateDict(self._is_carbon_entry)
			# lambda d: 'idShort' in d and d['idShort'] == 'CO2Footprint_kg_per_kWh' )
		locator.accept(fill_in)
		locator.found['value'] = footprint

		current_model['value'].append(fill_in)

		timeseries_url = get_timeseries_url(product, serial_number)
		info = AASInstancePut().execute(
			asset, context,
			timeseries_url,
			data=json.dumps(current_model),
			mime_type='application/json'
		)
		pass

	def _finalize_process(self, asset, context, product, serial_number, phase, footprint):
		def _add_to_total(entry):
			nonlocal total
			total += float(entry['value'])

		# record last measurement
		self._add_phase_measurement(asset, context, product, serial_number, phase, footprint)

		total = 0
		current_model = self._get_current_timeseries(asset, context, product, serial_number)
		collector = TraverseDict(self._is_carbon_entry, _add_to_total)
		collector.accept(current_model)

		page = context.store.query(context, 'www.files', file='instance_demo/finalize.html').get_result()
		if page.is_error():
			return page
		result = apply_replacements(
			page.get_result().decode(),
			PLACEHOLDER_FOOTPRINT_TOTAL_=f'{total:.2f}',
			PLACEHOLDER_PRODUCT_=product,
			PLACEHOLDER_SERIAL_NUMBER_=serial_number
		)
		return result

	def execute(
			self,
			asset,
			context: UpdateContext,
			product: str,
			serial_number: str,
			step: str,
			footprint: str=None,
			**kwargs
	):
		phase_number = int(step) - 1
		if phase_number < 0 or phase_number > len(self.phases):
			raise ValueError(f'non-existing phase: {phase_number}')

		if phase_number == 0:
			self._initial_product_setup(asset, context, product, serial_number)
		elif phase_number < len(self.phases):
			self._add_phase_measurement(asset, context, product, serial_number, phase_number-1, footprint)
		else:
			return self._finalize_process(asset, context, product, serial_number, phase_number-1, footprint)

		phase_name = self.phases[phase_number]

		page = context.store.query(context, 'www.files', file='instance_demo/process_step.html').get_result()
		if page.is_error():
			return page
		result = apply_replacements(
			page.get_result().decode(),
			PLACEHOLDER_PHASE_NAME_=phase_name.replace('_', ' '),
			PLACEHOLDER_PRODUCT_=product,
			PLACEHOLDER_SERIAL_NUMBER_=serial_number,
			PLACEHOLDER_NEXT_STEP_=str(phase_number+2)
		)
		return result

	def get_help(self):
		return Help.make(
			"A demonstration of a process step of handling Asset Instance Administration Shells",
			"test data of different types, most likely json or html",
			product='product identification from input form',
			footprint='process data for the step'
		)

