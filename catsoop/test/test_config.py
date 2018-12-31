import os

cs_dummy_username = 'tester'

cs_lti_config = {'consumers': {"__consumer_key__" : { "secret": "__lti_secret__" },
                               },
                 'session_key': "12i9slfd",
                 'pylti_url_fix': {"https://localhost": {"https://localhost": "http://192.168.33.10"}},
                 'lti_username_prefix': "lti_",
                 'force_username_from_id': False,
}

cs_data_root = os.environ['CATSOOP_DATA_DIR']

cs_unit_test_course = "test_course"
