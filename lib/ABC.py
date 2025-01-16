class AbstractBaseClassCalled(Exception):
	def __init__(self):
		super().__init__('Abstract Base Class called.')


class NotYetImplemented(Exception):
	def __init__(self):
		super().__init__('Not yet implemented.')
