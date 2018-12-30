import os
from abc import ABC, abstractmethod

from med_objects.med_volume import MedicalVolume
from utils import io_utils
from utils.quant_vals import QuantitativeValues, QuantitativeValue

WEIGHTS_FILE_EXT = 'h5'


class Tissue(ABC):
    """Handles analysis for all tissues
    Technically this includes non-tissue anatomy, like bone
    """
    ID = -1  # should be unique to all tissues, and should not change - replace with a unique identifier
    STR_ID = ''  # short hand string id such as 'fc' for femoral cartilage
    FULL_NAME = ''  # full name of tissue 'femoral cartilage' for femoral cartilage

    # Expected quantitative param values
    T1_EXPECTED = None

    # quantitative value list
    quantitative_values = []

    def __init__(self, weights_dir=None, medial_to_lateral=None):
        """
        :param weights_dir: Directory with segmentation weights
        """
        self.pid = None
        self.__mask__ = None
        self.quant_vals = dict()
        self.weights_filepath = None

        if weights_dir is not None:
            self.weights_filepath = self.find_weights(weights_dir)

        self.medial_to_lateral = medial_to_lateral

    @abstractmethod
    def split_regions(self, base_map):
        """
        Split mask into anatomical regions
        :param base_map: a 3D numpy array
        :return: a 4D numpy array (region, height, width, depth) - save in variable self.regions
        """
        pass

    def calc_quant_vals(self):
        """
        Get all quantitative values for tissue
        :param quant_map: a 3D numpy array for quantitative measures (t2, t2*, t1-rho, etc)
        :param map_type: an enum instance of QuantitativeValue
        :return: a list of dictionaries of quantitative values, save in quant_vals
        """
        for qv in self.quantitative_values:
            self.__calc_quant_vals__(qv.volumetric_map, qv.get_enum())

    @abstractmethod
    def __calc_quant_vals__(self, quant_map, map_type):
        """
        Private method to get quantitative values for tissue - implemented by tissue
        :param quant_map: a 3D numpy array for quantitative measures (t2, t2*, t1-rho, etc)
        :param map_type: an enum instance of QuantitativeValue
        :return: a dictionary of quantitative values, save in quant_vals
        """

        assert type(quant_map) is MedicalVolume
        assert type(map_type) is QuantitativeValues

        pass

    def __store_quant_vals__(self, quant_map, quant_df, map_type):
        self.quant_vals[map_type.name] = (quant_map, quant_df)

    def find_weights(self, weights_dir):
        """
        Search for weights file in weights directory
        :param weights_dir: directory where weights are stored
        :return: filepath to weights corresponding to tissue
        """

        # Find weights file with NAME in the filename, like 'fc_weights.h5'
        files = os.listdir(weights_dir)
        weights_file = None
        for f in files:
            file = os.path.join(weights_dir, f)
            if os.path.isfile(file) and file.endswith(WEIGHTS_FILE_EXT) and self.STR_ID in file:
                if weights_file is not None:
                    raise ValueError('There are multiple weights files, please remove duplicates')
                weights_file = file

        if weights_file is None:
            raise ValueError('No file found that contains \'%s\' and ends in \'%s\'' % (self.STR_ID, WEIGHTS_FILE_EXT))

        self.weights_filepath = weights_file

        return weights_file

    def save_data(self, save_dirpath):
        """Save data for tissue

        Saves mask and quantitative values associated with this tissue

        Extension (Overriding) protocol: When overriding in subclasses, call super().save_data(save_dirpath) first
                                            e.g. femoral_cartilage.py

        :param save_dirpath: base path to save data
        """
        save_dirpath = self.__save_dirpath__(save_dirpath)

        if self.__mask__ is not None:
            mask_filepath = os.path.join(save_dirpath, '%s.nii.gz' % self.STR_ID)
            self.__mask__.save_volume(mask_filepath)

        for qv in self.quantitative_values:
            qv.save_data(save_dirpath)

        self.__save_quant_data__(save_dirpath)

    @abstractmethod
    def __save_quant_data__(self, dirpath):
        pass

    def load_data(self, load_dirpath):
        """Load information for tissue

        All tissue information is based on the mask.
        If mask for tissue doesn't exist, there is no information to load.

        :param load_dirpath: base path to load data (same as 'save_dirpath' arg input to self.save_data(save_dirpath))
        """
        load_dirpath = self.__save_dirpath__(load_dirpath)
        mask_filepath = os.path.join(load_dirpath, '%s.nii.gz' % self.STR_ID)

        # try to load mask, if file exists
        if os.path.isfile(mask_filepath):
            self.set_mask(io_utils.load_nifti(mask_filepath))

        self.quantitative_values = QuantitativeValue.load_qvs(load_dirpath)

    def __save_dirpath__(self, dirpath):
        """Subdirectory to store data - save_dirpath/self.STR_ID/
        :param dirpath: base dirpath
        :return:
        """
        return io_utils.check_dir(os.path.join(dirpath, '%s' % self.STR_ID))

    def set_mask(self, mask):
        """Set mask for tissue
        :param mask: a MedicalVolume
        """
        assert type(mask) is MedicalVolume, "mask for tissue must be of type MedicalVolume"
        self.__mask__ = mask

    def get_mask(self):
        # if mask is None, try loading mask
        return self.__mask__

    def add_quantitative_value(self, qv_new):
        for qv in self.quantitative_values:
            if qv_new.NAME == qv.NAME:
                raise ValueError('This quantitative value already exists. '
                                 'Only one type of quantitative value can be added per tissue')

        self.quantitative_values.append(qv_new)
