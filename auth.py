"""
Authentication module for IBM Watson Speech-to-Text service.
This module centralizes authentication logic to avoid duplication.
"""

from typing import Optional
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import IAMTokenManager
from ibm_cloud_sdk_core.authenticators import BearerTokenAuthenticator

def create_stt_service(config) -> SpeechToTextV1:
    """
    Create an authenticated Speech-to-Text service instance.
    
    Args:
        config: Config object containing authentication details
        
    Returns:
        SpeechToTextV1: Authenticated Speech-to-Text service
    """
    apikey = config.getValue("SpeechToText", "apikey")
    bearer_token = config.getValue("SpeechToText", "bearer_token", None)
    url = config.getValue("SpeechToText", "service_url")
    use_bearer_token = config.getBoolean("SpeechToText", "use_bearer_token")

    # Determine which authentication method to use
    if bearer_token is not None:
        authenticator = BearerTokenAuthenticator(bearer_token)
    elif use_bearer_token is not True:
        authenticator = IAMAuthenticator(apikey)
    else:
        iam_token_manager = IAMTokenManager(apikey=apikey)
        bearer_token = iam_token_manager.get_token()
        authenticator = BearerTokenAuthenticator(bearer_token)

    # Create and configure the service
    speech_to_text = SpeechToTextV1(authenticator=authenticator)
    speech_to_text.set_service_url(url)
    speech_to_text.set_default_headers({'x-watson-learning-opt-out': "true"})
    
    return speech_to_text
