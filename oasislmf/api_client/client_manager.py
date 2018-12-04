#!/bin/env python

import io
import logging
import os
import sys
import time

from requests.exceptions import *
from requests_toolbelt import MultipartEncoder
from .session_manager import SessionManager

from ..utils.exceptions import OasisException

__all__ = [
    'ApiEndpoint',
    'FileEndpoint',
    'API_models',
    'API_portfolios',
    'API_analyses',
    'APIClient'
]

# --- API Endpoint mapping to functions ------------------------------------- #

class ApiEndpoint(object):
    """
    Used to Implement the default requests common to all Oasis API
    End points.
    """
    def __init__(self, session, url_endpoint, logger=None):
        self.logger = logger or logging.getLogger()
        self.session = session
        self.url_endpoint = url_endpoint

    def create(self, data):
        return self.session.post(self.url_endpoint, json=data)

    def get(self, ID=None):
        if ID:
            return self.session.get('{}{}/'.format(self.url_endpoint, ID))
        return self.session.get(self.url_endpoint)

    def delete(self, ID):
        return self.session.delete('{}{}/'.format(self.url_endpoint, ID))

class FileEndpoint(object):
    """
    File Resources Endpoint for Upload / Downloading
    """
    def __init__(self, session, url_endpoint, url_resource, logger=None):
        self.logger = logger or logging.getLogger()

        self.session = session
        self.url_endpoint = url_endpoint
        self.url_resource = url_resource

    def _build_url(self, ID):
        return '{}{}/{}'.format(
            self.url_endpoint,
            ID,
            self.url_resource
        )

    def upload(self, ID, file_path, content_type='text/csv'):
        try:
            abs_fp = os.path.realpath(os.path.expanduser(file_path))
            with io.open(abs_fp, 'rb') as f:
                m = MultipartEncoder(fields={'file': (os.path.basename(file_path), f, content_type)})
                r = self.session.post(self._build_url(ID), data=m, headers={'Content-Type': m.content_type})
                r.raise_for_status()
                return r
        except HTTPError as e:
            err_msg = 'File upload Failed: {}, file: {},  url: {}, msg: {}'.format(r.status_code, file_path, r.url, r.text)
            self.logger.debug(err_msg)

    def download(self, ID, file_path, chuck_size=1024, overrwrite=False):
        abs_fp = os.path.realpath(os.path.expanduser(file_path))

        # Check and create base dir
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        # Check if file exists
        if os.path.exists(abs_fp) and not overrwrite:
            error_message = 'Local file alreday exists: {}'.format(abs_fp)
            #self._logger.error(error_message)
            #raise OasisException(error_message)
            raise IOError(error_message)

        r = self.session.get(self._build_url(ID), stream=True)
        if  r.ok:
            with io.open(abs_fp, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chuck_size):
                    f.write(chunk)
        else:
            self.logger.info('Download failed')
           # exception_message = 'GET {} failed: {}'.format(response.request.url, response.status_code)
           # self._logger.error(exception_message)
           # raise OasisException(exception_message)
        return r

    def get(self, ID):
        ## fetch file into memory
        return self.session.get(self._build_url(ID))

    def post(self, ID, data_object, content_type='application/json'):
        ## Update data as object -
        # https://toolbelt.readthedocs.io/en/latest/uploading-data.html
        m = MultipartEncoder(fields={'file': ('data', data_object, content_type)})
        r = self.session.post(self._build_url(ID),
                                 data=m,
                                 headers={'Content-Type': m.content_type})
        if not r.ok:
            err_msg = 'Data_Object upload Failed'
            self.logger.info(err_msg)
            #self._logger.error(error_message)
            #raise OasisException(error_message)
        return r

    def delete(self, ID):
        return self.session.delete(self._build_url(ID))


class API_models(ApiEndpoint):
    def search(self, metadata):
        search_string = ''
        for key in metadata:
            search_string += '?{}={}'.format(key, metadata[key])
        return self.session.get('{}{}'.format(self.url_endpoint, search_string))

    def create(self, supplier_id, model_id, version_id):
        data = {"supplier_id": supplier_id,
                "model_id": model_id,
                "version_id": version_id}
        return self.session.post(self.url_endpoint, json=data)

    def update(self, ID, supplier_id, model_id, version_id):
        data = {"supplier_id": supplier_id,
                "model_id": model_id,
                "version_id": version_id}
        return self.session.put('{}{}/'.format(self.url_endpoint, ID), json=data)


class API_portfolios(ApiEndpoint):

    def __init__(self, session, url_endpoint):
        super(API_portfolios, self).__init__(session, url_endpoint)
        self.accounts_file = FileEndpoint(self.session, self.url_endpoint, 'accounts_file/')
        self.location_file = FileEndpoint(self.session, self.url_endpoint, 'location_file/')
        self.reinsurance_info_file = FileEndpoint(self.session, self.url_endpoint, 'reinsurance_info_file/')
        self.reinsurance_source_file = FileEndpoint(self.session, self.url_endpoint, 'reinsurance_source_file/')

    def search(self, metadata):
        search_string = ''
        for key in metadata:
            search_string += '?{}={}'.format(key, metadata[key])
        return self.session.get('{}{}'.format(self.url_endpoint, search_string))

    def create(self, name):
        data = {"name": name}
        return self.session.post(self.url_endpoint, json=data)

    def update(self, ID, name):
        data = {"name": name}
        return self.session.put('{}{}/'.format(self.url_endpoint, ID), json=data)

    def create_analyses(self, ID, name, model_id):
        """ Create new analyses from Exisiting portfolio
        """
        data = {"name": name,
                "model": model_id}
        return self.session.post('{}{}/create_analysis/'.format(self.url_endpoint, ID), json=data)


class API_analyses(ApiEndpoint):

    def __init__(self, session, url_endpoint):
        super(API_analyses, self).__init__(session, url_endpoint)
        self.input_errors_file = FileEndpoint(self.session, self.url_endpoint, 'input_errors_file/')
        self.input_file = FileEndpoint(self.session, self.url_endpoint, 'input_file/')
        self.input_generation_traceback_file = FileEndpoint(self.session, self.url_endpoint, 'input_generation_traceback_file/')
        self.output_file = FileEndpoint(self.session, self.url_endpoint, 'output_file/')
        self.run_traceback_file = FileEndpoint(self.session, self.url_endpoint, 'run_traceback_file/')
        self.settings_file = FileEndpoint(self.session, self.url_endpoint, 'settings_file/')

    def search(self, metadata):
        search_string = ''
        for key in metadata:
            search_string += '?{}={}'.format(key, metadata[key])
        return self.session.get('{}{}'.format(self.url_endpoint, search_string))

    def create(self, name, portfolio_id, model_id):
        data = {"name": name,
                "portfolio": portfolio_id,
                "model": model_id }
        return self.session.post(self.url_endpoint, json=data)

    def update(self, ID, name, portfolio_id, model_id):
        data = {"name": name,
                "portfolio": portfolio_id,
                "model": model_id }
        return self.session.put('{}{}/'.format(self.url_endpoint, ID), json=data)

    def status(self, ID):
        return self.get(ID).json()['status']

    def generate(self, ID):
        return self.session.post('{}{}/generate_inputs/'.format(self.url_endpoint, ID), json={})

    def generate_cancel(self, ID):
        return self.session.post('{}{}/cancel_generate_inputs/'.format(self.url_endpoint, ID), json={})

    def run(self, ID):
        return self.session.post('{}{}/run/'.format(self.url_endpoint, ID), json={})

    def run_cancel(self, ID):
        return self.session.post('{}{}/cancel/'.format(self.url_endpoint, ID), json={})






# --- API Main Client ------------------------------------------------------- #

class APIClient(object):
    def __init__(self, api_url, api_ver, username, password, timeout=2, logger=None):
        self.logger = logger or logging.getLogger()

        self.api        = SessionManager(api_url, username, password, timeout)
        self.models     = API_models(self.api, '{}{}/models/'.format(self.api.url_base, api_ver))
        self.portfolios = API_portfolios(self.api, '{}{}/portfolios/'.format(self.api.url_base, api_ver))
        self.analyses   = API_analyses(self.api,'{}{}/analyses/'.format(self.api.url_base, api_ver))


    def upload_inputs(self, portfolio_name=None, portfolio_id=None,
                      location_fp=None, accounts_fp=None, ri_info_fp=None, ri_scope_fp=None):

        if not portfolio_name:
            portfolio_name = time.strftime("Portfolio_%d%m%Y-%H%M%S")

        try:
            if portfolio_id:
                self.logger.info('Updating exisiting portfolio')
                portfolio = self.portfolios.update(portfolio_id, portfolio_name)
            else:
                self.logger.info('Creating portfolio')
                portfolio = self.portfolios.create(portfolio_name)
                portfolio_id = portfolio.json()['id']


            ## Check or create portfolio
            if not portfolio.ok:
                err_msg = "Failed to find matching `portfolio_id = {}`".format(portfolio_id)
                self.logger.info(err_msg)
                # raise OasisException()

            ## Upload exposure
            if location_fp:
                self.portfolios.location_file.upload(portfolio_id, location_fp)
                self.logger.info("File uploaded: {}".format(location_fp))
            if accounts_fp:
                self.portfolios.accounts_file.upload(portfolio_id, accounts_fp)
                self.logger.info("File uploaded: {}".format(accounts_fp))
            if ri_info_fp:
                self.portfolios.reinsurance_info_file.upload(portfolio_id, ri_info_fp)
                self.logger.info("File uploaded: {}".format(ri_info_fp))
            if ri_scope_fp:
                self.portfolios.reinsurance_source_file.upload(portfolio_id, ri_scope_fp)
                self.logger.info("File uploaded: {}".format(ri_scope_fp))
            return portfolio.json()
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.info(err_msg)
            self.logger.info('upload_inputs: failed')
            sys.exit(1)


    def create_analysis(self, portfolio_id, model_id, analysis_name=None, analysis_settings_fp=None):
        try:
            if not analysis_name:
                analysis_name = time.strftime("Analysis_%d%m%Y-%H%M%S")

            r = self.models.get(model_id)
            r.raise_for_status()

            r = self.portfolios.get(portfolio_id)
            r.raise_for_status()

            r = self.analyses.create(analysis_name ,portfolio_id, model_id)
            r.raise_for_status()
            analyses = r.json()

            if analysis_settings_fp:
                r = self.analyses.settings_file.upload(analyses['id'], analysis_settings_fp, 'application/json')
                self.logger.info("File uploaded: {}".format(analysis_settings_fp))

            return analyses
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.info(err_msg)
            self.logger.info('create_analysis: failed ')
            sys.exit(1)


    # BLOCKING CALL
    def run_generate(self, analysis_id, poll_interval=5):
        """
        Generates the inputs for the analysis based on the portfolio.
        The analysis must have one of the following statuses, `NEW`, `INPUTS_GENERATION_ERROR`,
        `INPUTS_GENERATION_CANCELED`, `READY`, `RUN_COMPLETED`, `RUN_CANCELLED` or
        `RUN_ERROR`.
        """

        try:
            r = self.analyses.generate(analysis_id)
            r.raise_for_status()
            analysis = r.json()
            self.logger.info('Inputs Generation: Started (id={})'.format(analysis_id))
            while True:
                if analysis['status'] in ['READY']:
                    self.logger.info('Inputs Generation: Complete (id={})'.format(analysis_id))
                    return True

                elif analysis['status'] in ['INPUTS_GENERATION_CANCELED']:
                    self.logger.info('Input Generation: Cancelled (id={})'.format(analysis_id))
                    return False

                elif analysis['status'] in  ['INPUTS_GENERATION_ERROR']:
                    self.logger.info('Input Generation: failed (id={})'.format(analysis_id))
                    error_trace = analyses.input_generation_traceback_file.get(analysis_id).text
                    self.logger.debug(error_trace)
                    return False

                elif analysis['status'] in ['INPUTS_GENERATION_STARTED']:
                    #self.logger.debug('Polling - status: {}'.format(analysis['status']))
                    time.sleep(poll_interval)
                    r = self.analyses.get(analysis_id)
                    r.raise_for_status()
                    analysis = r.json()
                    continue

                else:
                    err_msg = "Inputs Generation: Unknown State'{}'".format(analysis['status'])
                    #Raise oasis Execption
                    ## Error -- Raise execption Unknown Analysis  State
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.info(err_msg)
            self.logger.info('run_generate: failed')
            sys.exit(1)

    # BLOCKING CALL
    def run_analysis(self, analysis_id, analysis_settings_fp=None, poll_interval=5):
        """
        Runs all the analysis. The analysis must have one of the following
        statuses, `NEW`, `RUN_COMPLETED`, `RUN_CANCELLED` or
        `RUN_ERROR`
        """

        try:
            if analysis_settings_fp:
                r = self.analyses.settings_file.upload(analysis_id, analysis_settings_fp, 'application/json')
                self.logger.info("File uploaded: {}".format(analysis_settings_fp))

            r = self.analyses.run(analysis_id)
            r.raise_for_status()
            analysis = r.json()
            self.logger.info('Analysis Run: Started (id={})'.format(analysis_id))

            while True:
                if analysis['status'] in ['RUN_COMPLETED']:
                    self.logger.info('Analysis Run: Complete (id={})'.format(analysis_id))
                    return True

                elif analysis['status'] in ['RUN_CANCELLED']:
                    self.logger.info('Analysis Run: Cancelled (id={})'.format(analysis_id))
                    return False

                elif analysis['status'] in  ['RUN_ERROR']:
                    self.logger.info('Analysis Run: failed (id={})'.format(analysis_id))
                    error_trace = analyses.analyses.run_traceback_file.get(analysis_id).text
                    self.logger.debug(error_trace)
                    return False

                elif analysis['status'] in ['RUN_STARTED']:
                    #self.logger.debug('Polling - status: {}'.format(analysis['status']))
                    time.sleep(poll_interval)
                    r = self.analyses.get(analysis_id)
                    r.raise_for_status()
                    analysis = r.json()
                    continue

                else:
                    err_msg = "Execution status in Unknown State: '{}'".format(analysis['status'])
                    #Raise oasis Execption
                    ## Error -- Raise execption Unknown Analysis  State
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.info(err_msg)
            self.logger.info('run_analysis: failed')
            sys.exit(1)

    def download_output(self, analysis_id, download_path, filename=None, clean_up=False, overwrite=False):
        if not filename:
            filename='analysis_{}_output'.format(analysis_id)
        try:
            output_file = os.path.join(download_path, filename + '.tar')
            r = self.analyses.output_file.download(analysis_id, output_file, overwrite)
            self.logger.info('Output Downloaded: id={}, filename={}'.format(analysis_id, output_file))
            if clean_up:
                r = self.analyses.delete(analysis_id)
                r = self.analyses.output_file.delete(analysis_id)
                r = self.analyses.input_file.delete(analysis_id)
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.info(err_msg)
            self.logger.info('download_output: Failed')
            sys.exit(1)


    def cancel_generate(self, analysis_id):
        """
        Cancels a currently inputs generation. The analysis status must be `GENERATING_INPUTS`
        """
        try:
            r = self.analyses.generate_cancel(analysis_id)
            self.logger.info('Cancelled Input generation: Id={}'.format(analysis_id))
            return True
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.debug(err_msg)
            self.logger.info('cancel_generate: Failed')
            return False


    def cancel_analysis(self, analysis_id):
        """
        Cancels a currently running analysis. The analysis must have one of the following
        statuses, `PENDING` or `STARTED`
        """
        try:
            r = self.analyses.run_cancel(analysis_id)
            self.logger.info('Cancelled analysis run: Id={}'.format(analysis_id))
            return True
        except HTTPError as e:
            err_msg = 'API Error: {}, url: {}, msg: {}'.format(r.status_code, r.url, r.text)
            self.logger.info(err_msg)
            self.logger.info('cancel_analysis: Failed')
            return False