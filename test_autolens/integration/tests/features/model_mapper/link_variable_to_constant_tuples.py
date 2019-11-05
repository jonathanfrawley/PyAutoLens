import autofit as af
import autolens as al
from test_autolens.integration.tests import runner

test_type = "model_mapper"
test_name = "link_variable_to_constant_tuples"
data_type = "lens_light_dev_vaucouleurs"
data_resolution = "LSST"


def make_pipeline(name, phase_folders, optimizer_class=af.MultiNest):
    class MMPhase(al.PhaseImaging):
        def customize_priors(self, results):

            self.galaxies.lens.light.centre_0 = 1.0
            self.galaxies.lens.light.centre_1 = 2.0

    phase1 = MMPhase(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(lens=al.GalaxyModel(redshift=0.5, light=al.lp.EllipticalSersic)),
        optimizer_class=optimizer_class,
    )

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 20
    phase1.optimizer.sampling_efficiency = 0.8

    class MMPhase2(al.PhaseImaging):
        def customize_priors(self, results):

            self.galaxies.lens.light.centre = results.from_phase(
                "phase_1"
            ).constant.galaxies.lens.light.centre

    phase2 = MMPhase2(
        phase_name="phase_2",
        phase_folders=phase_folders,
        galaxies=dict(lens=al.GalaxyModel(redshift=0.5, light=al.lp.EllipticalSersic)),
        optimizer_class=optimizer_class,
    )

    phase2.optimizer.const_efficiency_mode = True
    phase2.optimizer.n_live_points = 20
    phase2.optimizer.sampling_efficiency = 0.8

    return al.PipelineDataset(name, phase1, phase2)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])