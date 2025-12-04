import os
import logging

logger = logging.getLogger(__name__)

class StubLLM:
    def __init__(self, provider, model):
        self.provider = provider
        self.model = model

    def __call__(self, prompt):
        return generate_with_fallback(prompt, self.model, self.provider)

def generate_with_fallback(prompt, model=None, provider=None):
    """
    Generate text using the configured provider, with a deterministic fallback.
    """
    try:
        # In a real implementation, this would call the actual LLM API.
        # For this demo/stub, we check if we have credentials, otherwise fallback.
        if os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY"):
            # Placeholder for actual call - in a real app, we'd use the keys here
            # For now, we'll just log that we *could* have used them
            logger.info(f"Credentials found for {provider}, but using stub for stability.")
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
        # Return a callable object that mimics an LLM client
        return StubLLM(provider, model)
