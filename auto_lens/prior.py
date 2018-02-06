import math
from scipy.special import erfinv
import inspect
from ConfigParser import ConfigParser
import os

path = os.path.dirname(os.path.realpath(__file__))


class ClassMap(object):
    """A collection of priors formed by passing in classes to be reconstructed"""

    def __init__(self, config=None, **classes):
        """
        Parameters
        ----------
        config: Config
            An object that wraps a configuration

        Examples
        --------
        # A ClassMap keeps track of priors associated with the attributes required to construct
        # instances of classes.

        # A config is passed into the collection to provide default setup values for the priors:

        collection = ClassMap(config)

        # All class instances that are to be generated by the collection are specified by passing their name and class:

        collection.add_class("sersic_1", light_profile.SersicLightProfile)
        collection.add_class("sersic_2", light_profile.SersicLightProfile)
        collection.add_class("other_instance", SomeClass)

        # A PriorModel instance is created each time we add a class to the collection. We can access those models using
        # their name:

        sersic_model_1 = collection.sersic_1

        # This allows us to replace the default priors:

        collection.sersic_1.intensity = GaussianPrior(2., 5.)

        # Or maybe we want to tie two priors together:

        collection.sersic_1.intensity = collection.sersic_2.intensity

        # This statement reduces the number of priors by one and means that the two sersic instances will always share
        # the same centre.

        # We can then create instances of every class for a unit hypercube vector with length equal to
        # len(collection.priors):

        reconstruction = collection.reconstruction_for_vector([.4, .2, .3, .1])

        # The attributes of the reconstruction are named the same as those of the collection:

        sersic_1 = collection.sersic_1

        # But this attribute is an instance of the actual SersicLightProfile class

        # A ClassMap can be concisely constructed using keyword arguments:

        collection = prior.ClassMap(config, source_light_profile=light_profile.SersicLightProfile,
                                    lens_mass_profile=mass_profile.CoredEllipticalIsothermalMassProfile,
                                    lens_light_profile=light_profile.CoreSersicLightProfile)
        """
        super(ClassMap, self).__init__()

        self.config = (config if config is not None else Config("{}/config".format(path)))

        for name, cls in classes.iteritems():
            self.add_class(name, cls)

    def make_prior(self, attribute_name, cls):
        config_arr = self.config.get_for_nearest_ancestor(cls, attribute_name)
        if config_arr[0] == "u":
            return UniformPrior(config_arr[1], config_arr[2])
        elif config_arr[0] == "g":
            return GaussianPrior(config_arr[1], config_arr[2])

    def add_class(self, name, cls):
        """
        Add a class to this collection. Priors are automatically generated for __init__ arguments. Prior type and
        configuration is taken from matching module.class.attribute entries in the config.

        Parameters
        ----------
        name: String
            The name of this class. This is also the attribute name for the class in the collection and reconstruction.
        cls: class
            The class for which priors are to be generated.

        """

        arg_spec = inspect.getargspec(cls.__init__)
        try:
            defaults = dict(zip(arg_spec.args[-len(arg_spec.defaults):], arg_spec.defaults))
        except TypeError:
            defaults = {}
        args = arg_spec.args[1:]

        prior_model = PriorModel(cls)

        for arg in args:
            if arg in defaults and isinstance(defaults[arg], tuple):
                tuple_prior = TuplePrior()
                for i in range(len(defaults[arg])):
                    attribute_name = "{}_{}".format(arg, i)
                    setattr(tuple_prior, attribute_name, self.make_prior(attribute_name, cls))
                setattr(prior_model, arg, tuple_prior)
            else:
                setattr(prior_model, arg, self.make_prior(arg, cls))

        setattr(self, name, prior_model)

    @property
    def prior_models(self):
        return filter(lambda t: isinstance(t[1], PriorModel), self.__dict__.iteritems())

    @property
    def prior_set(self):
        """
        Returns
        -------
        prior_set: set()
            The set of all priors associated with this collection
        """
        return {prior[1]: prior for _, prior_model in self.prior_models for prior in prior_model.priors}.values()

    @property
    def priors(self):
        """
        Returns
        -------
        priors: [Prior]
            An ordered list of unique priors associated with this collection
        """
        return sorted(list(self.prior_set), key=lambda prior: prior[1].id)

    def reconstruction_for_vector(self, vector):
        """
        Creates a Reconstruction, which has an attribute and class instance corresponding to every PriorModel attributed
        to this instance.

        Parameters
        ----------
        vector: [float]
            A unit hypercube vector

        Returns
        -------
        reconstruction: Reconstruction
            An object containing reconstructed model instances

        """
        arguments = dict(map(lambda prior, unit: (prior[1], prior[1].value_for(unit)), self.priors, vector))

        reconstruction = Reconstruction()

        for prior_model in self.prior_models:
            setattr(reconstruction, prior_model[0], prior_model[1].instance_for_arguments(arguments))

        return reconstruction


prior_number = 0


class Prior(object):
    """An object used to map a unit value to an attribute value for a specific class attribute"""

    def __init__(self):
        global prior_number
        self.id = prior_number
        prior_number += 1

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return "<Prior id={}>".format(self.id)


class UniformPrior(Prior):
    """A prior with a uniform distribution between a lower and upper limit"""

    def __init__(self, lower_limit=0., upper_limit=1.):
        """

        Parameters
        ----------
        lower_limit: Float
            The lowest value this prior can return
        upper_limit: Float
            The highest value this prior can return
        """
        super(UniformPrior, self).__init__()
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit

    def value_for(self, unit):
        """

        Parameters
        ----------
        unit: Float
            A unit hypercube value between 0 and 1
        Returns
        -------
        value: Float
            A value for the attribute between the upper and lower limits
        """
        return self.lower_limit + unit * (self.upper_limit - self.lower_limit)


class GaussianPrior(Prior):
    """A prior with a gaussian distribution"""

    def __init__(self, mean, sigma):
        super(GaussianPrior, self).__init__()
        self.mean = mean
        self.sigma = sigma

    def value_for(self, unit):
        """

        Parameters
        ----------
        unit: Float
            A unit hypercube value between 0 and 1
        Returns
        -------
        value: Float
            A value for the attribute biased to the gaussian distribution
        """
        return self.mean + (self.sigma * math.sqrt(2) * erfinv((unit * 2.0) - 1.0))


class PriorModel(object):
    """Object comprising class and associated priors"""

    def __init__(self, cls):
        """
        Parameters
        ----------
        cls: class
            The class associated with this instance
        """
        self.cls = cls

    @property
    def tuple_priors(self):
        return filter(lambda t: isinstance(t[1], TuplePrior), self.__dict__.iteritems())

    @property
    def direct_priors(self):
        return filter(lambda t: isinstance(t[1], Prior), self.__dict__.iteritems())

    @property
    def priors(self):
        return self.direct_priors + [prior for tuple_prior in self.tuple_priors for prior in tuple_prior[1].priors]

    def instance_for_arguments(self, arguments):
        """
        Create an instance of the associated class for a set of arguments

        Parameters
        ----------
        arguments: {Prior: value}
            Dictionary mapping priors to attribute name and value pairs

        Returns
        -------
            An instance of the class
        """
        model_arguments = {t[0]: arguments[t[1]] for t in self.direct_priors}
        for tuple_prior in self.tuple_priors:
            model_arguments[tuple_prior[0]] = tuple_prior[1].value_for_arguments(arguments)
        return self.cls(**model_arguments)


class TuplePrior(object):
    @property
    def priors(self):
        return filter(lambda t: isinstance(t[1], Prior), self.__dict__.iteritems())

    def value_for_arguments(self, arguments):
        return tuple([arguments[prior[1]] for prior in self.priors])


class Reconstruction(object):
    pass


class PriorException(Exception):
    pass


class Config(object):
    """Parses prior config"""

    def __init__(self, path):
        """
        Parameters
        ----------
        path: String
            The path to the prior config folder
        """
        self.path = path
        self.parser = ConfigParser()

    def read(self, module_name):
        """
        Read a particular config file

        Parameters
        ----------
        module_name: String
            The name of the module for which a config is to be read (priors relate one to one with configs).

        """
        self.parser.read("{}/{}.ini".format(self.path, module_name.split(".")[-1]))

    def get_for_nearest_ancestor(self, cls, attribute_name):
        """
        Find a prior with the attribute name from the config for this class or one of its ancestors

        Parameters
        ----------
        cls: class
            The class of interest
        attribute_name: String
            The name of the attribute
        Returns
        -------
        prior_array: []
            An array describing this prior
        """

        def family(current_class):
            yield current_class
            for next_class in current_class.__bases__:
                for val in family(next_class):
                    yield val

        for family_cls in family(cls):
            if self.has(family_cls.__module__, family_cls.__name__, attribute_name):
                return self.get(family_cls.__module__, family_cls.__name__, attribute_name)
        raise PriorException(
            "The prior config for {}.{} and the prior configs of its parents do no contain {}".format(cls.__module__,
                                                                                                      cls.__name__,
                                                                                                      attribute_name))

    def get(self, module_name, class_name, attribute_name):
        """

        Parameters
        ----------
        module_name: String
            The name of the module
        class_name: String
            The name of the class
        attribute_name: String
            The name of the attribute

        Returns
        -------
        prior_array: []
            An array describing a prior
        """
        self.read(module_name)
        arr = self.parser.get(class_name, attribute_name).replace(" ", "").split(",")
        return [arr[0]] + map(float, arr[1:])

    def has(self, module_name, class_name, attribute_name):
        """
        Parameters
        ----------
        module_name: String
            The name of the module
        class_name: String
            The name of the class
        attribute_name: String
            The name of the attribute

        Returns
        -------
        has_prior: bool
            True iff a prior exists for the module, class and attribute
        """
        self.read(module_name)
        return self.parser.has_option(class_name, attribute_name)
