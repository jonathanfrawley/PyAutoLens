import autofit as af
import autolens as al
from test.integration.tests import runner

test_type = "phase_features"
test_name = "positions"
data_type = "lens_sis__source_smooth"
data_resolution = "LSST"


def make_pipeline(name, phase_folders, optimizer_class=af.MultiNest):
    phase1 = al.PhaseImaging(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5, mass=al.mass_profiles.SphericalIsothermal
            ),
            source=al.GalaxyModel(
                redshift=1.0, light=al.light_profiles.EllipticalSersic
            ),
        ),
        positions_threshold=0.0,
        optimizer_class=optimizer_class,
    )

    phase1.optimizer.const_efficiency_mode = True
    phase1.optimizer.n_live_points = 30
    phase1.optimizer.sampling_efficiency = 0.8

    return al.PipelineImaging(name, phase1)


if __name__ == "__main__":
    import sys

    runner.run(
        sys.modules[__name__],
        positions=[[[1.6, 0.0], [0.0, 1.6], [-1.6, 0.0], [0.0, -1.6]]],
    )
