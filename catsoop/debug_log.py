# This file is part of CAT-SOOP

import logging

def setup_logging(context):
    logging.getLogger('pylti.common').setLevel(getattr(logging, context.get('cs_lti_debug_level', 'WARNING')))
    logging.getLogger("cs").setLevel(getattr(logging, context.get('cs_debug_level', 'WARNING')))

LOGGER = logging.getLogger("cs")
    
