
def default_or_raise(default_value, message=None):
    """
    Handles a default_value that may be an exception or a valid value.
    It is a service function for get-accessors, that should either return a value, or throw an
    exception (most likely) on miss.

    If the default_value is an instance of an Exception, the function raises it.
    If a message is provided, it augments the exception with additional context.
    If the default_value is not an exception, it simply returns the default_value.

    Parameters:
    default_value (any): The value to be checked. This can be a valid default_value or an exception instance.
    message (str, optional): An optional message to augment the exception. Defaults to None.

    Returns:
    any: The input default_value if it is not an exception.

    Raises:
    Exception: If the default_value is an instance of an Exception, it is raised. If a message is provided,
               the exception is augmented with the message.
    """
    def _exception_with_comment(exception_instance):
        """
        Augments an exception instance with additional context in its arguments.

        Parameters:
        exception_instance (Exception): The exception to be augmented.

        Returns:
        Exception: The modified exception instance with updated arguments.
        """
        try:
            raise exception_instance
        except Exception as exception:
            if exception.args and isinstance(exception.args[0], str):
                new_args = (f"{exception.args[0]} | {message}",) + exception.args[1:]
            else:
                # if the 1st arg is not a string, prepend the additional message as a new argument
                new_args = (message,) + exception.args
            exception.args = new_args
            return exception

    if isinstance(default_value, Exception):
        if message:
            raise _exception_with_comment(default_value)
        else:
            raise default_value

    return default_value
