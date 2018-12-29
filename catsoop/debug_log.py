# This file is part of CAT-SOOP

import logging

def setup_logging(context):
    logging.getLogger('pylti.common').setLevel(context.get('cs_lti_debug_level', 'WARNING'))
    logging.getLogger("cs").setLevel(context.get('cs_debug_level', 'WARNING'))

    ch = logging.StreamHandler()	# console handler for logging
    ch.setLevel(context.get('cs_debug_level', 'WARNING'))
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    ch.setFormatter(formatter)
    logging.getLogger("cs").addHandler(ch)

LOGGER = logging.getLogger("cs")

