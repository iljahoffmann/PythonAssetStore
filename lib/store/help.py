
class Variant:
	def __init__(self, returns, **kwargs):
		self.returns = returns
		self.param = kwargs

	def entry(self):
		return {
			'returns': self.returns,
			'param': self.param
		}


class Help:
	@staticmethod
	def make(summary, returns, **parameter):
		return {
			'summary': summary,
			'param': parameter,
			'returns': returns
		}
