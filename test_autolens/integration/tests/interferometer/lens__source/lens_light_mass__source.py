import autofit as af
import autolens as al
from test_autolens.integration.tests.interferometer import runner

test_type = "lens__source"
test_name = "lens_light_mass__source"
data_label = "lens_sie__source_smooth"
instrument = "sma"


def make_pipeline(name, phase_folders, real_space_mask, non_linear_class=af.MultiNest):

    phase1 = al.PhaseInterferometer(
        phase_name="phase_1",
        phase_folders=phase_folders,
        galaxies=dict(
            lens=al.GalaxyModel(
                redshift=0.5,
                light=al.lp.SphericalDevVaucouleurs,
                mass=al.mp.EllipticalIsothermal,
            ),
            source=al.GalaxyModel(redshift=1.0, light=al.lp.EllipticalSersic),
        ),
        real_space_mask=real_space_mask,
        non_linear_class=non_linear_class,
    )

    phase1.search.const_efficiency_mode = True
    phase1.search.n_live_points = 60
    phase1.search.sampling_efficiency = 0.8

    return al.PipelineDataset(name, phase1)


if __name__ == "__main__":
    import sys

    runner.run(sys.modules[__name__])
