# This file is part of CAT-SOOP

import logging

def setup_logging(context):
    logging.getLogger('pylti.common').setLevel(context.get('cs_lti_debug_level', 'WARNING'))
    logging.getLogger("cs").setLevel(context.get('cs_debug_level', 'WARNING'))
    logging.basicConfig(format='%(asctime)s - %(message)s')

LOGGER = logging.getLogger("cs")

