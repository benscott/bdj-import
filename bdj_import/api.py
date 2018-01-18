"""Summary
"""
import os
import requests
from xml.etree import ElementTree
from configparser import ConfigParser
import xmltodict


class API:

    """Summary

    Attributes:
        api_key (TYPE): Description
        endpoint (str): Description
        username (TYPE): Description
    """

    endpoint = 'https://arpha.pensoft.net/api.php'

    def __init__(self):
        """Summary
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.cfg'))
        self.username = config.get('credentials', 'username')
        self.api_key = config.get('credentials', 'api_key')

    def authenticate(self):
        '''
        Authenticate API
        '''
        self.request(action='authenticate')

    def validate_document(self, xml):
        """Summary

        Args:
            xml (TYPE): Description
        """

        response = self.request(action='validate_document', xml=xml)
        print(response)

    def request(self, **params):
        """Summary

        Args:
            **params: function params

        Returns:
            TYPE: Description

        Raises:
            Exception: Description
        """
        default_params = {
            'username': self.username,
            'api_key': self.api_key
        }
        params.update(default_params)
        r = requests.post(self.endpoint, data=params)
        r.raise_for_status()
        response = xmltodict.parse(r.content).get('result')
        if response['returnCode'] != '0':
            raise Exception('API Error: {}'.format(response['errorMsg']))
        return response

    def hey():

        pass

        # print(tree)
