import os
import logging

logger = logging.getLogger(__name__)

def generate_with_fallback(prompt, model=None, provider=None):
    """
    Generate text using the configured provider, with a deterministic fallback.
    """
    try:
        # In a real implementation, this would call the actual LLM API.
        # For this demo/stub, we check if we have credentials, otherwise fallback.
        if os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY"):
             # Placeholder for actual call
             pass
        
        # Fallback for demo/testing or if API fails
        logger.info(f"Using fallback for prompt: {prompt[:20]}...")
        return f"Stub response for: {prompt[:30]}..."
        
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return "I apologize, but I'm having trouble connecting to my brain right now."

class LLMFactory:
    @staticmethod
    def create(provider, model):
        return generate_with_fallback
