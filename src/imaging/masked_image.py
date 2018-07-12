from src.imaging import image as im
from src.pixelization import frame_convolution
import numpy as np


class MaskedImage(im.AbstractImage):
    def __new__(cls, image, mask):
        return np.array(mask.masked_1d_array_from_2d_array(image), ).view(cls)

    def __init__(self, image, mask, subgrid_size=1):
        super().__init__(array=image,
                         effective_exposure_time=mask.masked_1d_array_from_2d_array(image.effective_exposure_time),
                         pixel_scale=image.pixel_scale,
                         psf=image.psf,
                         background_noise=mask.masked_1d_array_from_2d_array(image.background_noise),
                         poisson_noise=mask.masked_1d_array_from_2d_array(image.poisson_noise))
        self.border_pixel_indices = mask.border_pixel_indices
        self.coordinate_grid = mask.coordinate_grid
        self.blurring_mask = mask.blurring_mask_for_kernel_shape(image.psf.shape)
        self.blurring_coordinate_grid = self.blurring_mask.coordinate_grid
        self.kernel_convolver = frame_convolution.FrameMaker(mask).convolver_for_kernel(image.psf)
        self.sub_coordinate_grid = mask.sub_coordinate_grid_with_size(subgrid_size)
        self.sub_to_image = mask.sub_to_image_with_size(subgrid_size)