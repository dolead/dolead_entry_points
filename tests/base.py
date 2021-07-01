import logging
# import pytest

# from flask import Flask
# from app import application as app

# from dolead_entry_points.server import _DEFAULTS

# @pytest.fixture
# def client():
#     assert app

#     with app.test_client() as client:
#         yield client

class TestCase:
    def setUp(self):
        logging.debug("Setup")

    def tearDown(self):
        logging.debug("Tear down")
