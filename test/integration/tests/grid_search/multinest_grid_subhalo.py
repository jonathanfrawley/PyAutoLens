import autofit as af
from autolens.model.galaxy import galaxy_model as gm
from autolens.model.profiles import light_profiles as lp
from autolens.model.profiles import mass_profiles as mp
from autolens.pipeline.phase import phase_imaging
from autolens.pipeline import pipeline as pl
from test.integration.tests import runner

test_type = "grid_search"
test_name = "multinest_grid_subhalo"
data_type = "no_lens_light_and_source_smooth"
data_resolution = "LSST"

def make_pipeline(name, phase_folders, optimizer_class=af.MultiNest):
    class QuickPhase(phase_imaging.PhaseImaging):
        def pass_priors(self, results):

            self.galaxies.lens.mass.centre_0 = af.UniformPrior(
                lower_limit=-0.01, upper_limit=0.01
            )
            self.galaxies.lens.mass.centre_1 = af.UniformPrior(
                lower_limit=-0.01, upper_limit=0.01
            )
            self.galaxies.lens.mass.axis_ratio = af.UniformPrior(
                lower_limit=0.65, upper_limit=0.75
            )
            self.galaxies.lens.mass.phi = af.UniformPrior(
                lower_limit=40.0, upper_limit=50.0
            )
            self.galaxies.lens.mass.einstein_radius = af.UniformPrior(
                lower_limit=1.55, upper_limit=1.65
            )

            self.galaxies.source.light.centre_0 = af.UniformPrior(
                lower_limit=-0.01, upper_limit=0.01
            )
            self.galaxies.source.light.centre_1 = af.UniformPrior(
                lower_limit=-0.01, upper_limit=0.01
            )
            self.galaxies.source.light.axis_ratio = af.UniformPrior(
                lower_limit=0.75, upper_limit=0.85
            )
            self.galaxies.source.light.phi = af.UniformPrior(
                lower_limit=50.0, upper_limit=70.0
            )
            self.galaxies.source.light.intensity = af.UniformPrior(
                lower_limit=0.35, upper_limit=0.45
            )
            self.galaxies.source.light.effective_radius = af.UniformPrior(
                lower_limit=0.45, upper_limit=0.55
            )
            self.galaxies.source.light.sersic_index = af.UniformPrior(
                lower_limit=0.9, upper_limit=1.1
            )

    phase1 = QuickPhase(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=gm.GalaxyModel(redshift=0.5, mass=mp.EllipticalIsothermal),
            source=gm.GalaxyModel(redshift=1.0, light=lp.EllipticalSersic),
        ),
        optimizer_class=optimizer_class,
    )

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 40
    phase1.optimizer.sampling_efficiency = 0.8

    class GridPhase(af.as_grid_search(phase_imaging.PhaseImaging)):
        @property
        def grid_priors(self):
            return [
                self.variable.galaxies.subhalo.mass.centre_0,
                self.variable.galaxies.subhalo.mass.centre_1,
            ]

        def pass_priors(self, results):

            ### Lens Mass, PL -> PL, Shear -> Shear ###

            # self.galaxies.lens = results.from_phase('phase_1').\
            #     constant.galaxies.lens

            ### Lens Subhalo, Adjust priors to physical masses (10^6 - 10^10) and concentrations (6-24)

            self.galaxies.subhalo.mass.kappa_s = af.UniformPrior(
                lower_limit=0.0005, upper_limit=0.2
            )
            self.galaxies.subhalo.mass.scale_radius = af.UniformPrior(
                lower_limit=0.001, upper_limit=1.0
            )
            self.galaxies.subhalo.mass.centre_0 = af.UniformPrior(
                lower_limit=-2.0, upper_limit=2.0
            )
            self.galaxies.subhalo.mass.centre_1 = af.UniformPrior(
                lower_limit=-2.0, upper_limit=2.0
            )

            ### Source Light, Sersic -> Sersic ###

            self.galaxies.source.light.centre = (
                results.from_phase("phase_1")
                .variable_absolute(a=0.05)
                .galaxies.source.light.centre
            )

            self.galaxies.source.light.intensity = (
                results.from_phase("phase_1")
                .variable_relative(r=0.5)
                .galaxies.source.light.intensity
            )

            self.galaxies.source.light.effective_radius = (
                results.from_phase("phase_1")
                .variable_relative(r=0.5)
                .galaxies.source.light.effective_radius
            )

            self.galaxies.source.light.sersic_index = (
                results.from_phase("phase_1")
                .variable_relative(r=0.5)
                .galaxies.source.light.sersic_index
            )

            self.galaxies.source.light.axis_ratio = (
                results.from_phase("phase_1")
                .variable_absolute(a=0.1)
                .galaxies.source.light.axis_ratio
            )

            self.galaxies.source.light.phi = (
                results.from_phase("phase_1")
                .variable_absolute(a=20.0)
                .galaxies.source.light.phi
            )

    phase2 = GridPhase(
        phase_name="phase_2",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=gm.GalaxyModel(redshift=0.5, mass=mp.EllipticalIsothermal),
            subhalo=gm.GalaxyModel(
                redshift=0.5, mass=mp.SphericalTruncatedNFWChallenge
            ),
            source=gm.GalaxyModel(redshift=1.0, light=lp.EllipticalSersic),
        ),
        optimizer_class=optimizer_class,
        number_of_steps=2,
    )

    phase2.optimizer.const_efficiency_mode = True

    return pl.PipelineImaging(name, phase1, phase2)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
