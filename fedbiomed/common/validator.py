"""
Provide Validator ans SchemeValidator classes for validating parameters against a set of validation rules.

This module provides two classes:

Validator:

  This class manage a rulebook of rules which can afterwards be accessed
  by their (registered) name.

  Values can be checked against the rules.

  Typical example:

  def my_validation_funct( value ):
      if some_python_code:
          return False
      else:
          return True

  v = Validator()
  v.register( "funky_name", my_validation_funct)
  v.register( "float_type", float)

  val = 3.14
  v.validate( val, "funky_name")
  v.validate( val, "float_type")
  v.validate( val, float)

  v.validate( "{ 'a': 1 }", dict)
  ...


SchemeValidator:

  This class provides json validation againt a scheme describing the
  expected json content.

  The scheme need to follow a specific format, which describe each
  allowed fields and their characteristics:
  - a list of associated validators to check against (aka Validator instances)
  - the field requierement (rquired on not)
  - a default value (which will be used if the field is required but not provided)

  A SchemeValidator is accepted byt the Validator class.

  Typical example:

  # direct use
  scheme = { "a" : { "rules" : [float], "required": True } }

  sc = SchemeValidator(scheme)

  value =  { "a": 3.14 }
  sc.validate(value)


  # use also the Validator class
  v = Validator()

  v.register( "message_a", sc )
  v.validate( value, "message_a" )

  # remark: all these lines are equivalent
  v.register( "message_a", sc )
  v.register( "message_a", SchemeValidator( scheme) )
  v.register( "message_a", scheme )

"""


import functools
import inspect
import sys

from enum import Enum


class ValidatorError(Exception):
    """
    Top class of all Validator/SchemaValidator exception
    """

    # as Validator can be used in other project than Fed-BioMed we
    # define our own exception, which is not a subclass of FedbiomedError
    pass


class ValidateError(ValidatorError):
    """
    Error raised then validating a value against a rule
    """

    pass


class RuleError(ValidatorError):
    """
    Error raised then the rule is badly defined
    """

    pass


class _ValidatorHookType(Enum):
    """
    List of all method available to execute a validation hook.
    """

    INVALID = 1
    TYPECHECK = 2
    FUNCTION = 3
    LAMBDA = 4
    SCHEME_VALIDATOR = 5
    SCHEME_AS_A_DICT = 6


def validator_decorator(func):
    """
    Function decorator for simplifying the writing of validator hooks.

    The decorator catches the output of the validator hook and build
    a tuple (boolean, string) as expected by the Validator class:

    It creates an error message if not provided by the decorated function
    The error message is forced to if the decorated function returns True

    If the validator is not used to decorate a validation function/hook,
    then the user feedback will be less precie or the end-user but this
    will not change the accuracy (True/False) os the feedback.

    Args:
       func:  function to decorate

    Returns:
       decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        # execute the wrapped function
        status = func(*args, **kwargs)

        # we expect a tuple [ bolean, str] as output of func()
        # but we try to be resilient to function that simply return boolean
        # and create the tuple in case that it is not provided
        error = "validation error then calling: " + func.__name__
        if isinstance(status, tuple):
            status, *error = status

        if status:
            return status, None
        else:
            error = ''.join(error)
            return status, error

    return wrapper


class SchemeValidator(object):
    """
    Validation class for scheme (grammar) which describes a json content.

    this class uses Validator's class base functions
    """

    # necessary keys and key types
    _necessary = { 'rules': list }  # list of callable, str, class

    # optionnal keys (no type associated to default)
    # even if the default may be checked againt the list of the rules
    _optionnal = { 'default': None, 'required': bool }


    def __init__(self, scheme):
        """
        Constructor of the class.

        it requires a json grammar as argument and validate
        its again the requested json description scheme

        A valid json description is also a dictionnary
        with the following grammar:

        {
          "var_name": {
                        "rules": [ validator1, vlidator2, ...] ,
                        "default": a_default_value,
                        "required": True/False
                      },
          ...
        }

        the "rules" field is mandatory
        "default" and "required" fields are optionnal.

        Example:

        This is a valid scheme:
        { "a" : { "rules" : [float], "required": True } }

        The following json complies to this scheme:
        { "a": 3.14 }

        The following do not:
        { "a": True }
        { "b": 3.14 }

        Args:
            scheme:     scheme to validate
        """

        status = self.__validate_scheme(scheme)

        if isinstance(status, bool) and status:
            self._scheme = scheme
            self._is_valid = True

        else:
            self._scheme = None
            self._is_valid = False
            raise RuleError("scheme is not valid: " + status)


    def validate(self, value):
        """
        Validate a value against the scheme passed at creation time.

        Args:
             value:  value (json) to validate against the scheme passed
                     at __init__
        Returns:
            bool:    result of the validation test
        """

        # TODO: raises error messages
        # or store error string in self._error and provide a error() method
        if not self.is_valid():  # pragma: no cover
            return False

        if not isinstance(value, dict):
            raise ValidateError("value is not a dict")

        # check the value against the scheme
        for k, v in self._scheme.items():
            if 'required' in v and v['required'] is True and k not in value:
                raise ValidateError(str(k) + " value is required")

        for k in value:
            if k not in self._scheme:
                raise ValidateError("undefined key (" + str(k) + ") in scheme")

            for hook in self._scheme[k]['rules']:
                if not Validator().validate(value[k], hook):
                    # this should already have raises an error
                    raise ValidateError("invalid value (" + str(value[k]) + ") for key: " + str(k))  # pragma: nocover

        return True


    def populate_with_defaults( self, value):
        """
        Parse the given json value and add default value is key was required
        but not provided.
        Of course, the default value must be provided in the scheme.

        Warning: this does not parse the result agains the scheme. It has
        to be done by the user.

        Args:
            value:   a json data to verify/populate

        Return:
            json:    a json populated with default values,
                     returns an empty dict if something is wrong
        """

        if not self.is_valid():  # pragma: no cover
            return {}

        # check the value against the scheme
        result = value
        for k, v in self._scheme.items():
            if 'required' in v and v['required'] is True:

                if k in value:
                    result[k] = value[k]
                else:
                    if 'default' in v:
                        result[k] = v['default']
                    else:
                        raise RuleError("no default value for required key: "+str(k))

        return result




    def __validate_scheme(self, scheme):
        """
        Scheme validation function (internal).

        the scheme passed at __init__ is checked with this method

        Args:
            scheme:    scheme (json) to validate

        Returns:
            True      (bool) if everything is OK
            error_msg (str)  in case of error
        """

        if not isinstance(scheme, dict) or len(scheme) == 0:
            return("validator scheme must be a non empty dict")

        for n in self._necessary:
            for key in scheme:

                if not isinstance( scheme[key], dict) or len(scheme[key]) == 0 :
                    return("validator rule of (" + \
                           str(key) + \
                           ") scheme must be a non empty dict")

                if n not in scheme[key]:
                    return("required subkey (" + \
                           str(n) + \
                           ") is missing for key: " + \
                           str(key)
                        )

                value_in_scheme = scheme[key][n]
                requested_type  = self._necessary[n]
                if requested_type is not None and \
                   not isinstance(value_in_scheme, requested_type):

                    return("bad type for subkey (" + \
                           str(n) + \
                           ") for key: " + \
                           str(key)
                           )

                # special case for 'rules'
                # always False since _necessary has only the 'rules' key
                # test keeped because this may change in the future
                if not n == 'rules':  # pragma: no cover
                    continue

                # check that rules contains valid keys for Validator
                for element in scheme[key][n]:

                    if not Validator._is_hook_type_valid(element):
                        return("bad content for subkey (" + \
                               str(n) + \
                               ") for key: " + \
                               str(key)
                               )

        # check that all provided keys of scheme are accepted
        for key in scheme:
            for subkey in scheme[key]:
                if subkey not in self._necessary and subkey not in self._optionnal:
                    return ("unknown subkey (" + \
                            str(subkey) + \
                            ") provided for key: " + \
                            str(key)
                            )
                # if default value passed, it must respect the rules
                if subkey == "default":
                    def_value = scheme[key][subkey]

                    for rule in scheme[key]["rules"]:
                        try:
                            Validator().validate(def_value, rule)
                        except ValidateError:
                            # this func should not raise an Error
                            return ("default value for key (" + \
                                    str(key) + \
                                    ") does not respect its own specification (" + \
                                    str(def_value) + \
                                    ")"
                                    )

        # scheme is validated
        return True


    def is_valid(self):
        """
        Status of the scheme passed at creation time.

        Returns:
            bool  True if scheme is valid
        """
        return ( self._scheme is not None ) or self._is_valid


    def scheme(self):
        """
        Scheme getter.

        Returns:
            scheme   scheme passed at __init__ if valid, None instead
        """
        return self._scheme or None


class Validator(object):
    """
    Container class for validation functions accesible via their names.

    this class:
    - manages a catalog of tuples  ( "name", validation_hook )
      The validation_hook is validated at registration phase.
    - permit to validate a value against
        - a (named) registered hook
        - a direct validation hook passed as argument to validate()
        - a SchemeValidator for json validation
        - typechecking
    """

    _validation_rulebook = {}
    """
    Internal storage for tuples ("name", validation_hook).
    """

    def __init__(self):
        """
        Constructor, does nothing !.
        """
        pass


    def validate(self, value, rule, strict = True):
        """
        Validate a value against a validation rule.

        The rule may be one of:
        - (registered) rule
        - a provided function,
        - a simple type checking
        - a SchemeValidator

        Args:
            value:   value to check
            rule:    validation hook (registered name, typecheck, direct hook,..)

        Returns:
            bool    True if rule exists and value is compliant, False instead
        """

        # rule is in the rulebook -> execute the rule associated function
        if isinstance(rule, str) and rule in self._validation_rulebook:

            status, error = Validator._hook_execute(value,
                                                    self._validation_rulebook[rule])
            if not status:
                raise ValidateError(error)

            return status

        # rule is an unknown string
        if isinstance(rule, str):
            if strict:
                raise ValidateError("unknown rule: " + str(rule))
            else:
                sys.stdout.write("WARNING - Validator(): unknown rule: " + str(rule) + "\n")
                return True

        # consider the rule as a direct rule definition
        status, error = Validator._hook_execute(value, rule)

        if not status:
            raise ValidateError(error)

        return status


    @staticmethod
    def _hook_type(hook):
        """
        Detect the hook type agains permitter values descibred in _ValidatorHookType.

        Args:
            hook:   a hook to validate

        Returns:
            enum   return the method associated with this hook
        """

        # warning: order matters !
        if isinstance(hook, SchemeValidator):
            return _ValidatorHookType.SCHEME_VALIDATOR

        if isinstance(hook, dict):
            return _ValidatorHookType.SCHEME_AS_A_DICT

        if inspect.isclass(hook):
            return _ValidatorHookType.TYPECHECK

        _l = lambda:0
        if isinstance(hook, type(_l)) and hook.__name__ == _l.__name__:
            return _ValidatorHookType.LAMBDA

        if callable(hook):
            return _ValidatorHookType.FUNCTION

        # not valid
        return _ValidatorHookType.INVALID


    @staticmethod
    def _is_hook_type_valid(hook):
        """
        Verify that the hook type associated to a rule is valid.

        it does not validate the hook for function and SchemeValidator,
        it only verifies that the hook can be registered for later use

        Args:
            hook:   a hook to validate

        Returns:
            enum   return the method associated with this hook
        """

        hook_type = Validator._hook_type(hook)

        if hook_type == _ValidatorHookType.INVALID:
            return False
        else:
            return True


    @staticmethod
    @validator_decorator
    def _hook_execute(value, hook):
        """
        Execute the test associated with the hook on the value.

        the way the test is performed depends of the hook type

        Args:
            value:   to test
            hook:    to tests against
            strict:  boolen to decide is the test is strcit or not

        Returns:
            (boolean, string)  result of the test and optionnal error message

        """
        hook_type = Validator._hook_type(hook)

        if hook_type is _ValidatorHookType.INVALID:
            return False, "hook is not authorized"

        if hook_type is _ValidatorHookType.TYPECHECK:
            status = isinstance(value, hook)
            return status, "wrong input: " + str(value) + " should be a " + str(hook)

        if hook_type is _ValidatorHookType.LAMBDA:
            status = hook(value)
            if not status:
                return False, "error executing lambda"
            return True

        if hook_type is _ValidatorHookType.FUNCTION:
            return hook(value)

        if hook_type is _ValidatorHookType.SCHEME_VALIDATOR:
            return hook.validate(value)

        if hook_type is _ValidatorHookType.SCHEME_AS_A_DICT:
            try:
                sc = SchemeValidator( hook )
            except RuleError:
                # this func should not raise an error
                return False, "scheme is not valid"
            return sc.validate(value)


    def rule(self, rule):
        """
        Getter for the stored rule (if registered).

        Args:
            rule:   name (string) of a possibly registered hook

        Returns:
            hook:   the registered hook, None if not registered
        """
        if rule in self._validation_rulebook:
            return self._validation_rulebook[rule]
        else:
            return None


    def is_known_rule(self, rule):
        """
        Information about rule registration.

        Args:
            rule:   name (string) of a possibly registered hook

        Returns:
            bool   True if rule is registered, False instead
        """
        return (rule in self._validation_rulebook)


    def register(self, rule, hook, override = False):
        """
        Add a rule/validation_function to the rulebook.

        if the rule (entry of the catalog) was already registered,
        it will be rejected, except if ovverride is True

        Args:
            rule:      registration name (string)
            hook:      validation hook to register (the hook is checked against
                       the accepted hook types)
            override:  if True, still register the rule even if it existed

        Returns:
            bool   True if rule is accepted, False instead
        """
        if not isinstance(rule, str):
            raise RuleError("rule name must be a string")

        if not override and rule in self._validation_rulebook:
            sys.stdout.write("WARNING - Validator: rule is already registered: " + rule + "\n")
            return False

        if not Validator._is_hook_type_valid(hook):
            raise RuleError("action associated to the rule is unallowed")

        # hook is a dict, we transform it to a SchemeValidator
        if isinstance(hook, dict):
            try:
                sv = SchemeValidator( hook )
            except RuleError as e:
                raise RuleError("validator is an invalid dict: " + str(e))
            hook = sv

        # rule description is valid -> register it
        self._validation_rulebook[rule] = hook
        return True


    def delete(self, rule):
        """
        Delete a rule from the rulebook.

        Args:
            rule:   name (string) of a possibly registered hook
        """
        if rule in self._validation_rulebook:
            del self._validation_rulebook[rule]
