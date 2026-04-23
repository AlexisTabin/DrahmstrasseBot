import logging

# Setup logging
logger = logging.getLogger(__name__)

def is_present_dinner():
    """
    Returns the dinner question for the group.
    """
    question = "Pouet l'ekip qui AL pour le SOUPER ce soir?"
    logger.info("Generated dinner question: %s", question)
    return question

