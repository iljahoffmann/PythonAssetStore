# <<Visitor>>
class JsonVisitor:
	'''
	Other than within the standard pattern, traversal logic is implemented within this class - not within
	the visited nodes. The legitimation is, that json offers just two fixed containers.
	The Motivation is, that using this approach, all dispatching logic can be done using
	Python's "dispatch by name" pattern - here using the convention:

		_visit_<typename>(object, **kwargs)

	if no handler for 'typename' can be found, _visit_default(object, **kwargs) is called instead.

	Additionally, for the containers, _enter_<typename>(object, **kwargs) and _leave_<typename>(object, **kwargs)
	are called before, respectively after visiting the content of the container. if the _enter_* functions
	return (exactly) False, the container is skipped in the traversal.

	if the visitor is constructed with a set of given keyword arguments, these arguments will be used
	as template values, getting updated by the keyword arguments used in the actual visit-call.

	During traversal, the keyword arguments are updated:
		kwargs['container'] is the current top-most container
		kwargs['key'] is the key within the container holding the current entry.

	'''
	def __init__(self, **kwargs):
		self.kwargs = kwargs

	def accept(self, json_data, **kwargs):
		'''
		This is the single traversal entry point used by all client code. All other methods should be considered
		protected.
		'''
		if 'level' not in kwargs:
			kwargs['level'] = -1
			kwargs['container'] = None
			kwargs['key'] = None
		handler = getattr(self, f'_visit_{json_data.__class__.__name__}', self._visit_default)
		handler(json_data, **kwargs)

	def _visit_container(self, entry_generator, json_data, **kwargs):
		# the parameters in the local scope of the function on the call stack are used
		# as top-of-stack for container- and key-info.
		# So: create a private, flat copy based on __init__ keywords, updated by current kwargs
		args = {k: v for k, v in self.kwargs}
		args.update(kwargs)

		# store container info
		args['container'] = json_data
		args['level'] = args.get('level', -1) + 1

		# dispatch-by-name used for enter and leave too
		container_class_name = json_data.__class__.__name__
		do_enter = getattr(self, f'_enter_{container_class_name}')(json_data, **kwargs)
		if do_enter is False:
			return

		for key, value in entry_generator:
			# store key info
			args['key'] = key
			# enter recursion
			self.accept(value, **args)

		getattr(self, f'_leave_{container_class_name}')(json_data, **kwargs)
		pass

	def _visit_dict(self, json_data, **kwargs):
		self._visit_container(json_data.items(), json_data, **kwargs)

	def _visit_list(self, json_data, **kwargs):
		self._visit_container(enumerate(json_data), json_data, **kwargs)

	def _enter_dict(self, json_data, **kwargs):
		return True

	def _leave_dict(self, json_data, **kwargs):
		pass

	def _enter_list(self, json_data, **kwargs):
		return True

	def _leave_list(self, json_data, **kwargs):
		pass

	def _visit_default(self, json_data, **kwargs):
		pass

