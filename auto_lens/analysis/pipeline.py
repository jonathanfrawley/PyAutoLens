from auto_lens.analysis import non_linear
from auto_lens.analysis import model_mapper as mm
from auto_lens.analysis import fitting
from auto_lens.imaging import grids
from auto_lens.analysis import ray_tracing


# TODO: Maybe we need a general Analysis class where each argument is either a model or model instance and any model
# TODO: is a constant and any model instance a variable? The distinction between fixed and variable objects would be
# TODO: made between the constructor and run function.


class ModelAnalysis(object):
    def __init__(self, lens_galaxy_priors, source_galaxy_priors, model_mapper=mm.ModelMapper(),
                 non_linear_optimizer=non_linear.MultiNestWrapper()):
        """
        A class encapsulating an analysis. An analysis takes an image and a set of galaxy priors describing an
        assumed model and applies a pixelization and non linear optimizer to find the best possible fit between the
        image and model.

        Parameters
        ----------
        lens_galaxy_priors: [GalaxyPrior]
            A list of prior instances describing the lens
        source_galaxy_priors: [GalaxyPrior]
            A list of prior instances describing the source
        model_mapper: ModelMapper
            A class used to bridge between non linear unit vectors and class instances
        non_linear_optimizer: NonLinearOptimizer
            A wrapper around a library that searches an n-dimensional space by providing unit vector hypercubes to
            the analysis.
        """

        self.lens_galaxy_priors = lens_galaxy_priors
        self.source_galaxy_priors = source_galaxy_priors
        self.non_linear_optimizer = non_linear_optimizer
        self.model_mapper = model_mapper

        for galaxy_prior in lens_galaxy_priors + source_galaxy_priors:
            galaxy_prior.attach_to_model_mapper(model_mapper)

    def run(self, image, mask, pixelization, instrumentation):
        """
        Run the analysis, iteratively analysing each set of values provided by the non-linear optimiser until it
        terminates.

        Parameters
        ----------
        image: Image
            An image
        mask: Mask
            A mask defining which regions of the image should be ignored
        pixelization: Pixelization
            An object determining how the source plane should be pixelized
        instrumentation: Instrumentation
            An object describing instrumental effects to be applied to generated images

        Returns
        -------
        result: Result
            The result of the analysis, comprising a likelihood and the final set of galaxies generated
        """

        # Set up expensive objects that can be used repeatedly for fittings
        image_grid_collection = grids.GridCoordsCollection.from_mask(mask)

        # TODO: Convert image to 1D and create other auxiliary data structures such as kernel makers

        # Create an instance of run that will be used for this analysis
        run = self.__class__.Run(image, image_grid_collection, self.model_mapper, self.lens_galaxy_priors,
                                 self.source_galaxy_priors, pixelization, instrumentation)

        # Run the optimiser using the fitness function. The fitness function is applied iteratively until the optimiser
        # terminates
        self.non_linear_optimizer.run(run.fitness_function, self.model_mapper.priors_ordered_by_id)
        return self.__class__.Result(run)

    class Run(object):
        def __init__(self, image, image_grid_collection, model_mapper, lens_galaxy_priors, source_galaxy_priors,
                     pixelization, instrumentation):
            self.image = image
            self.model_mapper = model_mapper
            self.lens_galaxy_priors = lens_galaxy_priors
            self.source_galaxy_priors = source_galaxy_priors
            self.lens_galaxies = []
            self.source_galaxies = []
            self.image_grid_collection = image_grid_collection
            self.pixelization = pixelization
            self.instrumentation = instrumentation
            self.likelihood = None

        def fitness_function(self, physical_values):
            """
            Generates a model instance from a set of physical values, uses this to construct galaxies and ultimately a
            tracer that can be passed to analyse.likelihood_for_tracer.

            Parameters
            ----------
            physical_values: [float]
                Physical values from a non-linear optimiser

            Returns
            -------
            likelihood: float
                A value for the likelihood associated with this set of physical values in conjunction with the provided
                model
            """

            # Recover classes from physical values
            model_instance = self.model_mapper.from_physical_vector(physical_values)
            # Construct galaxies from their priors
            self.lens_galaxies = list(map(lambda galaxy_prior: galaxy_prior.galaxy_for_model_instance(model_instance),
                                          self.lens_galaxy_priors))
            self.source_galaxies = list(map(lambda galaxy_prior: galaxy_prior.galaxy_for_model_instance(model_instance),
                                            self.source_galaxy_priors))

            # Construct a ray tracer
            tracer = ray_tracing.Tracer(self.lens_galaxies, self.source_galaxies, self.image_grid_collection)
            # Determine likelihood:
            self.likelihood = fitting.likelihood_for_image_tracer_pixelization_and_instrumentation(self.image, tracer,
                                                                                                   self.pixelization,
                                                                                                   self.instrumentation)
            return self.likelihood

    class Result(object):
        def __init__(self, run):
            """
            The result of an analysis

            Parameters
            ----------
            run: Run
                An analysis run
            """
            # The final likelihood found
            self.likelihood = run.likelihood
            # The final lens galaxies generated
            self.lens_galaxies = run.lens_galaxies
            # The final source galaxies generated
            self.source_galaxies = run.source_galaxies


class HyperparameterAnalysis(object):
    def __init__(self, pixelization_class, instrumentation_class, model_mapper=mm.ModelMapper(),
                 non_linear_optimizer=non_linear.MultiNestWrapper()):
        """
        An analysis to improve hyperparameter settings. This optimizes pixelization and instrumentation.

        Parameters
        ----------
        pixelization_class
        instrumentation_class
        model_mapper
        non_linear_optimizer
        """
        self.model_mapper = model_mapper
        self.pixelization_class = pixelization_class
        self.instrumentation_class = instrumentation_class
        self.non_linear_optimizer = non_linear_optimizer

        model_mapper.add_class('pixelization', pixelization_class)
        model_mapper.add_class('instrumentation', instrumentation_class)

    def run(self, image, mask, lens_galaxies, source_galaxies):
        """
        Run the analysis, iteratively analysing each set of values provided by the non-linear optimiser until it
        terminates.

        Parameters
        ----------
        image: Image
            An image
        mask: Mask
            A mask defining which regions of the image should be ignored
        lens_galaxies: [Galaxy]

        source_galaxies: [Galaxy]


        Returns
        -------
        result: Result
            The result of the analysis, comprising a likelihood and the final pixelization and instrumentation generated
        """

        # Set up expensive objects that can be used repeatedly for fittings
        image_grid_collection = grids.GridCoordsCollection.from_mask(mask)

        # TODO: Convert image to 1D and create other auxiliary data structures such as kernel makers

        # Create an instance of run that will be used for this analysis
        run = self.__class__.Run(image, image_grid_collection, self.model_mapper, self.pixelization_class,
                                 self.instrumentation_class, lens_galaxies, source_galaxies)

        # Run the optimiser using the fitness function. The fitness function is applied iteratively until the optimiser
        # terminates
        self.non_linear_optimizer.run(run.fitness_function, self.model_mapper.priors_ordered_by_id)
        return self.__class__.Result(run)

    class Run(object):
        def __init__(self, image, image_grid_collection, model_mapper, pixelization_class, instrumentation_class,
                     lens_galaxies, source_galaxies):
            self.image = image
            self.image_grid_collection = image_grid_collection
            self.model_mapper = model_mapper
            self.pixelization_class = pixelization_class
            self.instrumentation_class = instrumentation_class
            self.lens_galaxies = lens_galaxies
            self.source_galaxies = source_galaxies
            self.pixelization = None
            self.instrumentation = None
            self.likelihood = None

        def fitness_function(self, physical_values):
            """
            Generates a model instance from a set of physical values, uses this to construct galaxies and ultimately a
            tracer that can be passed to analyse.likelihood_for_tracer.

            Parameters
            ----------
            physical_values: [float]
                Physical values from a non-linear optimiser

            Returns
            -------
            likelihood: float
                A value for the likelihood associated with this set of physical values in conjunction with the provided
                model
            """

            # Recover classes from physical values
            model_instance = self.model_mapper.from_physical_vector(physical_values)
            self.pixelization = model_instance.pixelization
            self.instrumentation = model_instance.instrumentation

            # Construct a ray tracer
            tracer = ray_tracing.Tracer(self.lens_galaxies, self.source_galaxies, self.image_grid_collection)
            # Determine likelihood:
            self.likelihood = fitting.likelihood_for_image_tracer_pixelization_and_instrumentation(self.image, tracer,
                                                                                                   self.pixelization,
                                                                                                   self.instrumentation)
            return self.likelihood

    class Result(object):
        def __init__(self, run):
            self.pixelization = run.pixelization
            self.instrumentation = run.instrumentation
            self.likelihood = run.likelihood


class MainPipeline(object):
    def __init__(self, *model_analyses, hyperparameter_analysis):
        """
        The primary pipeline. This pipeline runs a series of model analyses with hyperparameter analyses in between.

        Parameters
        ----------
        model_analyses: [ModelAnalysis]
            A series of analysis, each with a fixed model, pixelization and instrumentation but variable model instance.
        hyperparameter_analysis: HyperparameterAnalysis
            An analysis with a fixed model instance but variable pixelization and instrumentation instances.
        """
        self.model_analyses = model_analyses
        self.hyperparameter_analysis = hyperparameter_analysis

    def run(self, image, mask, pixelization, instrumentation):
        """
        Run this pipeline on an image and mask with a given initial pixelization and instrumentation.

        Parameters
        ----------
        image: Image
            The image to be fit
        mask: Mask
            A mask describing which parts of the image are to be included
        pixelization: Pixelization
            The initial pixelization of the source plane
        instrumentation: Instrumentation
            The initial instrumentation

        Returns
        -------
        results_tuple: ([ModelAnalysis.Result], [HyperparameterAnalysis.Result])
            A tuple with a list of results from each model analysis and a list of results from each hyperparameter
            analysis
        """

        # Define lists to keep results in
        model_results = []
        hyperparameter_results = []

        # Run through each model analysis
        for model_analysis in self.model_analyses:
            # Analyse the model
            model_result = model_analysis.run(image, mask, pixelization, instrumentation)
            # Analyse the hyper parameters
            hyperparameter_result = self.hyperparameter_analysis.run(image, mask, model_result.lens_galaxies,
                                                                     model_result.source_galaxies)

            # Update the hyperparameters
            pixelization = hyperparameter_result.pixelization
            instrumentation = hyperparameter_result.instrumentation

            # Append results for these two analyses
            model_results.append(model_result)
            hyperparameter_results.append(hyperparameter_result)

        return model_results, hyperparameter_results


class Analysis(object):
    def __init__(self, model_mapper=mm.ModelMapper(), non_linear_optimizer=non_linear.MultiNestWrapper(), **kwargs):
        self.model_mapper = model_mapper
        self.non_linear_optimizer = non_linear_optimizer
        self.included_attributes = []

        attribute_map = {"pixelization_class": "pixelization",
                         "instrumentation_class": "instrumentation",
                         "lens_galaxy_priors": "lens_galaxies",
                         "source_galaxy_priors": "source_galaxies"}

        for key, value in kwargs.items():
            setattr(self, key, value)
            self.included_attributes.append(key)

        self.missing_attributes = [value for key, value in attribute_map.items() if key not in self.included_attributes]

    def run(self, image, mask, **kwargs):
        def one_or_other(model_name, instance_name):
            is_model = getattr(self, model_name, None)
            is_instance = instance_name in kwargs
            if is_model and is_instance:
                raise AssertionError("{} already exists in analysis".format(model_name))
            if not (is_model or is_instance):
                raise AssertionError("{} is not defined so {} is required".format(model_name, instance_name))

        one_or_other("pixelization_class", "pixelization")
        one_or_other("instrumentation_class", "instrumentation")
        one_or_other("lens_galaxy_priors", "lens_galaxies")
        one_or_other("source_galaxy_priors", "source_galaxies")
        # Pixelisation, Instrumentation, Source Galaxies, Lens Galaxies
