# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import

import re

__all__ = [
    'OasisKeysLookupFactory',
    'OasisBaseKeysLookup',
]

import csv
import io
import json
import importlib
import os
import pandas as pd
import sys

from ..utils.exceptions import OasisException
from ..utils.log import oasis_log
from ..utils.status import KEYS_STATUS_NOMATCH, KEYS_STATUS_SUCCESS


__author__ = "Sandeep Murthy"
__copyright__ = "2017, Oasis Loss Modelling Framework"


UNKNOWN_ID = -1


class OasisBaseKeysLookup(object):
    """
    A base class / interface that serves a template for model-specific keys
    lookup classes.
    """
    @oasis_log()
    def __init__(
        self,
        keys_data_directory=None,
        supplier=None,
        model_name=None,
        model_version=None
    ):
        """
        Class constructor
        """
        if keys_data_directory is not None:
            self.keys_data_directory = keys_data_directory
        else:
            self.keys_data_directory = os.path.join(os.sep, 'var', 'oasis', 'keys_data')

        self.supplier = supplier
        self.model_name = model_name
        self.model_version = model_version

    @oasis_log()
    def process_locations(self, loc_df):
        """
        Process location rows - passed in as a pandas dataframe.
        """
        pass

    def _get_location_record(self, raw_loc_item):
        """
        Returns a dict of standard location keys and values based on
        a raw location item, which is a row in a Pandas dataframe.
        """
        pass

    def _get_area_peril_id(self, record):
        """
        Get the area peril ID for a particular location record.
        """
        return UNKNOWN_ID, "Not implemented"

    def _get_vulnerability_id(self, record):
        """
        Get the vulnerability ID for a particular location record.
        """
        return UNKNOWN_ID, "Not implemented"

    @oasis_log()
    def _get_area_peril_ids(self, loc_data, include_context=True):
        """
        Generates area peril IDs in two modes - if include_context is
        True (default) it will generate location records/rows including
        the area peril IDs, otherwise it will generate pairs of location
        IDs and the corresponding area peril IDs.
        """
        pass

    @oasis_log()
    def _get_vulnerability_ids(self, loc_data, include_context=True):
        """
        Generates vulnerability IDs in two modes - if include_context is
        True (default) it will generate location records/rows including
        the area peril IDs, otherwise it will generate pairs of location
        IDs and the corresponding vulnerability IDs.
        """
        pass

    def _get_lookup_success(self, ap_id, vul_id):
        """
        Determine the status of the keys lookup.
        """
        if ap_id == UNKNOWN_ID or vul_id == UNKNOWN_ID:
            return KEYS_STATUS_NOMATCH
        return KEYS_STATUS_SUCCESS


class OasisKeysLookupFactory(object):
    """
    A factory class to load and run keys lookup services for different
    models/suppliers.
    """

    @classmethod
    def get_model_info(cls, model_version_file_path):
        """
        Get model information from the model version file.
        """
        with io.open(model_version_file_path, 'r', encoding='utf-8') as f:
            return next(csv.DictReader(
                f, fieldnames=['supplier_id', 'model_id', 'model_version_id']
            ))

    @classmethod
    def get_lookup_package(cls, lookup_package_path):
        """
        Returns the lookup service parent package (called `keys_server` and
        located in `src` in the model keys server Git repository or in
        `var/www/oasis` in the keys server Docker container) from the given
        path.
        """
        parent_dir = os.path.abspath(os.path.dirname(lookup_package_path))
        package_name = re.sub(r'\.py$', '', os.path.basename(lookup_package_path))

        sys.path.insert(0, parent_dir)
        lookup_package = importlib.import_module(package_name)
        sys.path.pop(0)

        return lookup_package

    @classmethod
    def get_lookup_class_instance(cls, lookup_package, keys_data_path, model_info):
        """
        Get the keys lookup class instance.
        """
        klc = getattr(lookup_package, '{}KeysLookup'.format(model_info['model_id']))

        return klc(
            keys_data_directory=keys_data_path,
            supplier=model_info['supplier_id'],
            model_name=model_info['model_id'],
            model_version=model_info['model_version_id']
        )

    @classmethod
    def get_model_exposures(cls, model_exposures=None, model_exposures_file_path=None):
        """
        Get the model exposures/location file data as a pandas dataframe given
        either the path of the model exposures file or the string contents of
        such a file.
        """
        loc_df = None

        if model_exposures_file_path:
            with io.open(model_exposures_file_path, 'r', encoding='utf-8') as f:
                loc_df = pd.read_csv(io.StringIO(f.read()))
        elif model_exposures:
            loc_df = pd.read_csv(io.StringIO(model_exposures))

        loc_df = loc_df.where(loc_df.notnull(), None)
        loc_df.columns = map(str.lower, loc_df.columns)

        return loc_df

    @classmethod
    def write_oasis_keys_file(cls, records, output_file_path):
        """
        Writes an Oasis keys file from an iterable of keys records.
        """
        with io.open(output_file_path, 'w', encoding='utf-8') as f:
            f.write('LocID,PerilID,CoverageID,AreaPerilID,VulnerabilityID\n')
            n = 0
            for r in records:
                n += 1
                line = '{},{},{},{},{}\n'.format(r['id'], r['peril_id'], r['coverage'], r['area_peril_id'], r['vulnerability_id'])
                f.write(line)

            return f.name, n

    @classmethod
    def write_list_keys_file(cls, records, output_file_path):
        """
        Writes the keys records as a simple list to file.
        """
        n = 0
        with io.open(output_file_path, 'w', encoding='utf-8') as f:
            for r in records:
                f.write('{},\n'.format(json.dumps(r, sort_keys=True, indent=4, separators=(',', ': '))))
                n += 1

            return f.name, n

    @classmethod
    def create(
        cls,
        model_keys_data_path=None,
        model_version_file_path=None,
        lookup_package_path=None,
    ):
        """
        Creates a keys lookup class instance for the given model and supplier -
        local file paths are required for the model keys data folder, the model
        version file and the Git repository for the model keys server. Returns a
        pair ``(model_info, klc)``, where ``model_info`` is a dictionary holding
        model information from the model version file and `klc` is the lookup
        service class instance for the model.
        """
        if model_keys_data_path:
            model_keys_data_path = os.path.abspath(model_keys_data_path)

        if model_version_file_path:
            model_version_file_path = os.path.abspath(model_version_file_path)

        if lookup_package_path:
            lookup_package_path = os.path.abspath(lookup_package_path)

        model_info = cls.get_model_info(model_version_file_path)
        lookup_package = cls.get_lookup_package(lookup_package_path)
        klc = cls.get_lookup_class_instance(lookup_package, model_keys_data_path, model_info)
        return model_info, klc

    @classmethod
    def get_keys(
        cls,
        lookup=None,
        model_exposures=None,
        model_exposures_file_path=None,
        success_only=True
    ):
        """
        Generates keys keys records (JSON) for the given model and supplier -
        requires an instance of the lookup service (which can be created using
        the `create` method in this factory class), and either the model
        location file path or the string contents of such a file.

        The optional keyword argument ``success_only`` indicates whether only
        records with successful lookups should be returned (default), or all
        records.
        """
        if not any([model_exposures, model_exposures_file_path]):
            raise OasisException('No model exposures provided')

        model_loc_df = (
            cls.get_model_exposures(
                model_exposures_file_path=os.path.abspath(model_exposures_file_path)
            ) if model_exposures_file_path
            else cls.get_model_exposures(model_exposures=model_exposures)
        )

        for record_container in lookup.process_locations(model_loc_df):
            if type(record_container) in [list, tuple, set]:
                for r in record_container:
                    if success_only:
                        if r['status'].lower() == 'success':
                            yield r
                    else:
                        yield r
            elif type(record_container) == dict:
                if success_only:
                    if record_container['status'].lower() == 'success':
                        yield record_container
                else:
                    yield record_container

    @classmethod
    def save_keys(
        cls,
        lookup=None,
        model_exposures=None,
        model_exposures_file_path=None,
        success_only=True,
        output_file_path=None,
    ):
        """
        Writes the keys keys records generated by the lookup service for the
        given model and supplier to a local file - requires a lookup service
        instance (which can be created using the `create` method in this
        factory class), the path of the model location file, the path of
        output file, and the format of the output file which can be an
        Oasis keys file (``oasis_keys``) or a simple listing of the records
        to file (``list_keys``).

        The optional keyword argument ``success_only`` indicates whether only
        records with successful lookups should be returned (default), or all
        records.

        Returns a pair ``(f, n)`` where ``f`` is the output file object
        and ``n`` is the number of records written to the file.
        """
        if not lookup:
            raise OasisException('No keys lookup service provided')

        if not any([model_exposures, model_exposures_file_path]):
            raise OasisException('No model exposures or model exposures file path provided')

        model_exposures_file_path = os.path.abspath(model_exposures_file_path) if model_exposures_file_path else None
        output_file_path = os.path.abspath(output_file_path)

        keys = cls.get_keys(
            lookup=lookup,
            model_exposures=model_exposures,
            model_exposures_file_path=model_exposures_file_path,
            success_only=success_only
        )

        return cls.write_oasis_keys_file(keys, output_file_path)
