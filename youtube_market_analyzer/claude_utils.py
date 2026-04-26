"""
Claude API Utilities - Production Optimized with Accurate Pricing

This module provides a streamlined interface for Claude API with:
- Real-time token-by-token streaming
- Optimized web search support with clear logging
- Extended thinking (Claude 4)
- Image processing
- Clean event format for frontend integration
- ACCURATE model-specific pricing calculations

Compatible with chat_utils.py streaming format and optimized chat_processing.py
"""

import os
import base64
import logging
import time
from typing import List, Dict, Any, Optional, Iterator
from utilities.anthropic_logger import new_client
import json

# Configure logger
logger = logging.getLogger("claude_utils")

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Latest Claude models with performance characteristics
CLAUDE_MODELS = {
    # WARNING: opus-4 has 35+ second response time - may cause timeouts
    "opus-4": "claude-opus-4-20250514",          # ⚠️ ~35s response time - NOT recommended for real-time
    "opus-4.1": "claude-opus-4-1-20250805",      # ✅ ~3.5s - Latest Opus, much faster than 4.0
    "sonnet-4": "claude-sonnet-4-20250514",      # ✅ ~2s - Fast, capable, web search enabled
    "sonnet-3.7": "claude-3-7-sonnet-20250219",  # ✅ ~2.3s - Good balance
    "sonnet-3.5": "claude-3-5-sonnet-latest",    # ✅ ~1.4s - Recommended default, reliable
    "haiku-3.5": "claude-3-5-haiku-latest",      # ⚡ ~0.5s - Fastest, best for simple tasks
    "opus-3.5": "claude-3-5-opus-latest",        # ❌ Model doesn't exist - will return 404
}

# ACCURATE MODEL PRICING (per token, not per million tokens)
MODEL_PRICING = {
    # Claude 4.1 models
    'claude-opus-4-1': {'input': 0.000020, 'output': 0.000080},  # $20/$80 per million
    
    # Claude 4 models
    'claude-opus-4': {'input': 0.000015, 'output': 0.000075},    # $15/$75 per million
    'claude-sonnet-4': {'input': 0.000003, 'output': 0.000015},  # $3/$15 per million
    
    # Claude 3.7 models  
    'claude-3-7-sonnet': {'input': 0.000003, 'output': 0.000015}, # $3/$15 per million
    
    # Claude 3.5 models
    'claude-3-5-sonnet': {'input': 0.000003, 'output': 0.000015}, # $3/$15 per million
    'claude-3-5-haiku': {'input': 0.00000025, 'output': 0.00000125}, # $0.25/$1.25 per million
    
    # Default fallback (Sonnet pricing)
    'default': {'input': 0.000003, 'output': 0.000015}
}

# Response time expectations (based on testing):
# - Haiku 3.5: ~0.5s (fastest, simple tasks)
# - Sonnet 3.5: ~1.4s (best balance)
# - Sonnet 4: ~2s (enhanced capabilities)
# - Sonnet 3.7: ~2.3s (good alternative)
# - Opus 4.1: ~3.5s (most capable, acceptable speed)
# - Opus 4: ~35s (NOT RECOMMENDED - will cause timeouts)

def get_model_pricing(model_name: str) -> Dict[str, float]:
    """Get accurate pricing per token for different Claude models"""
    model_lower = model_name.lower()
    
    # Find exact match first
    for model_key, prices in MODEL_PRICING.items():
        if model_key in model_lower:
            return prices
    
    # Fallback to partial matches
    if 'haiku' in model_lower:
        return MODEL_PRICING['claude-3-5-haiku']
    elif 'sonnet-4' in model_lower:
        return MODEL_PRICING['claude-sonnet-4']
    elif 'sonnet' in model_lower:
        return MODEL_PRICING['claude-3-5-sonnet']
    elif 'opus-4-1' in model_lower:
        return MODEL_PRICING['claude-opus-4-1']
    elif 'opus' in model_lower:
        return MODEL_PRICING['claude-opus-4']
    
    return MODEL_PRICING['default']

class ClaudeClient:
    def __init__(self, 
                api_key: str,
                model: str = None,
                enable_beta_features: bool = True):
        """
        Initialize the Claude client.
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use (defaults to latest Sonnet)
            enable_beta_features: Enable beta features like web search
        """
        if not api_key:
            raise ValueError("No API key provided")
        
        # Default to Sonnet 3.5 if no model specified (fast and reliable)
        if not model:
            model = CLAUDE_MODELS.get("sonnet-3.5", "claude-3-5-sonnet-latest")
        
        # Warn about slow models
        if "claude-opus-4-20250514" in model:
            logger.warning(f"Model {model} has ~35s response time - consider using opus-4.1 or sonnet models instead")
            
        # Store configuration
        self.api_key = api_key
        self.model = model
        self.enable_beta_features = enable_beta_features
        
        # Initialize Anthropic client with appropriate timeout
        # Use longer timeout for Opus 4 original, standard for others
        timeout = 60.0 if "claude-opus-4-20250514" in model else 30.0
        
        self.client = new_client(timeout=timeout, # Dynamic timeout based on model
            max_retries=2)
        
        logger.info(f"Initialized Claude client with model: {self.model} (timeout: {timeout}s)")
        if enable_beta_features:
            logger.debug("Web search capabilities available (no beta headers required)")
    
    def _log_tokens(self, method: str, response: Any):
        """Log token usage and ACCURATE cost estimation."""
        if hasattr(response, 'usage'):
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
            
            # Get accurate model-specific pricing
            model_pricing = get_model_pricing(self.model)
            input_cost = input_tokens * model_pricing['input']
            output_cost = output_tokens * model_pricing['output']
            total_cost = input_cost + output_cost
            
            logger.info(
                f"{method} | Model: {self.model} | "
                f"Tokens: {input_tokens}→{output_tokens} (Total: {total_tokens}) | "
                f"Cost: ${total_cost:.6f}"
            )
    
    def _get_media_type(self, file_path: str) -> str:
        """Determine media type from file extension."""
        extension = file_path.lower().split('.')[-1]
        media_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return media_types.get(extension, 'application/octet-stream')
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 1024, 
                     temperature: float = 1.0) -> str:
        """
        Generate text response from Claude.
        
        Args:
            prompt: The text prompt to send to Claude
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            Generated text response
        """
        try:
            start_time = time.time()
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            
            elapsed_time = time.time() - start_time
            response_text = message.content[0].text
            
            self._log_tokens("generate_text", message)
            logger.info(f"Text generation completed in {elapsed_time:.2f}s")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating text response: {str(e)}")
            raise
    
    def process_image(self, 
                     image_path: str, 
                     prompt: str,
                     max_tokens: int = 1024,
                     temperature: float = 1.0) -> str:
        """
        Process an image file with Claude and generate a text response.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt to accompany the image
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Returns:
            Generated text response about the image
        """
        try:
            # Check if the image exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Read and base64 encode the image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")
            
            # Use the base64 processing method
            return self.process_image_base64(
                image_data=base64_image,
                media_type=self._get_media_type(image_path),
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
        except Exception as e:
            logger.error(f"Error processing image file: {str(e)}")
            raise

    def process_image_url(self, 
                         image_url: str, 
                         prompt: str,
                         max_tokens: int = 1024,
                         temperature: float = 1.0) -> str:
        """
        Process an image from a URL with Claude and generate a text response.
        
        Args:
            image_url: URL to the image
            prompt: Text prompt to accompany the image
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Returns:
            Generated text response about the image
        """
        try:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": image_url
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            
            start_time = time.time()
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": content}]
            )
            
            elapsed_time = time.time() - start_time
            response_text = message.content[0].text
            
            self._log_tokens("process_image_url", message)
            logger.info(f"Image URL processing completed in {elapsed_time:.2f}s")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing image URL: {str(e)}")
            raise

    def process_image_base64(self, 
                            image_data: str, 
                            media_type: str,
                            prompt: str,
                            max_tokens: int = 1024,
                            temperature: float = 1.0) -> str:
        """
        Process a base64-encoded image with Claude.
        
        Args:
            image_data: Base64-encoded image data
            media_type: MIME type of the image (e.g., 'image/jpeg')
            prompt: Text prompt to accompany the image
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            
        Returns:
            Generated text response about the image
        """
        try:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            
            start_time = time.time()
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": content}]
            )
            
            elapsed_time = time.time() - start_time
            response_text = message.content[0].text
            
            self._log_tokens("process_image_base64", message)
            logger.info(f"Base64 image processing completed in {elapsed_time:.2f}s")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing base64 image: {str(e)}")
            raise
    
    def chat(self, 
            messages: List[Dict[str, Any]], 
            max_tokens: int = 1024,
            temperature: float = 1.0,
            system: str = None) -> str:
        """
        Conduct a multi-turn chat conversation with Claude.
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness
            system: System prompt for context and instructions
            
        Returns:
            Generated text response for the conversation
        """
        try:
            # Validate message format
            for msg in messages:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    raise ValueError("Invalid message format. Each message must have 'role' and 'content' keys.")
                if msg['role'] not in ['user', 'assistant']:
                    raise ValueError("Message role must be either 'user' or 'assistant'.")
            
            params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            
            if system:
                params["system"] = system
            
            start_time = time.time()
            
            message = self.client.messages.create(**params)
            
            elapsed_time = time.time() - start_time
            response_text = message.content[0].text
            
            self._log_tokens("chat", message)
            logger.info(f"Chat completed in {elapsed_time:.2f}s | Messages: {len(messages)}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error in chat conversation: {str(e)}")
            raise
    
    def stream_chat(self,
                   messages: List[Dict[str, Any]],
                   max_tokens: int = 1024,
                   temperature: float = 1.0,
                   system: str = None,
                   enable_web_search: bool = False) -> Iterator[Dict[str, Any]]:
        """
        Stream a chat conversation with Claude - OPTIMIZED with clear web search logging.
        
        This method yields events in the exact format expected by chat_processing.py:
        - {"type": "start", "message_id": "..."}
        - {"type": "web_search_start"}
        - {"type": "web_search_query", "text": "..."}
        - {"type": "delta", "text": "..."}  <- Key for real-time streaming
        - {"type": "stop"}
        
        Args:
            messages: List of message objects with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Controls randomness
            system: System prompt for context and instructions
            enable_web_search: Enable web search tool
            
        Yields:
            Dictionaries containing streaming events for chat_processing.py
        """
        try:
            # Build request parameters
            params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            
            if system:
                params["system"] = system
            
            # Add web search tool if enabled and supported - with clear logging
            if enable_web_search:
                web_search_added = self.configure_web_search_tools(params)
                if web_search_added:
                    logger.info(f"🌐 Web search tools configured for {self.model}")
                else:
                    logger.info(f"💬 Using knowledge base mode for {self.model}")
            
            logger.debug(f"Starting streaming chat with model {self.model}")
            
            # Track performance
            total_input_tokens = 0
            total_output_tokens = 0
            start_time = time.time()
            
            # Create streaming request with proper event handling
            with self.client.messages.stream(**params) as stream:
                for event in stream:
                    if not hasattr(event, 'type'):
                        continue
                        
                    # Handle different Claude SDK event types
                    if event.type == 'message_start':
                        total_input_tokens = event.message.usage.input_tokens
                        logger.debug(f"Stream started - Input tokens: {total_input_tokens}")
                        
                        yield {
                            "type": "start",
                            "message_id": event.message.id,
                            "model": event.message.model
                        }
                        
                    elif event.type == 'content_block_start':
                        # Check for web search tool use - with better logging
                        if (hasattr(event, 'content_block') and 
                            hasattr(event.content_block, 'type') and
                            event.content_block.type == 'server_tool_use' and 
                            hasattr(event.content_block, 'name') and
                            event.content_block.name == 'web_search'):
                            
                            logger.info("🌐 Claude is searching the web for current information...")
                            
                            yield {
                                "type": "web_search_start"
                            }
                            
                    elif event.type == 'content_block_delta':
                        # This is the CRITICAL section for real-time streaming
                        if hasattr(event, 'delta'):
                            
                            # Handle different delta types
                            if hasattr(event.delta, 'type'):
                                
                                if event.delta.type == 'text_delta':
                                    # ✅ MAIN TEXT STREAMING - Real-time token display
                                    yield {
                                        "type": "delta",
                                        "text": event.delta.text
                                    }
                                    
                                elif event.delta.type == 'input_json_delta':
                                    # Web search query being built
                                    yield {
                                        "type": "web_search_query",
                                        "text": event.delta.partial_json if hasattr(event.delta, 'partial_json') else ''
                                    }
                                    
                                elif event.delta.type == 'thinking':
                                    # Extended thinking from Claude 4
                                    yield {
                                        "type": "thinking",
                                        "text": event.delta.text if hasattr(event.delta, 'text') else ''
                                    }
                            
                            # Fallback for any delta with text
                            elif hasattr(event.delta, 'text'):
                                yield {
                                    "type": "delta",
                                    "text": event.delta.text
                                }
                                
                    elif event.type == 'message_delta':
                        # Track output tokens
                        if hasattr(event, 'usage'):
                            total_output_tokens = event.usage.output_tokens
                            
                    elif event.type == 'message_stop':
                        # Stream completed
                        elapsed_time = time.time() - start_time
                        
                        # Log final performance with ACCURATE pricing
                        total_tokens = total_input_tokens + total_output_tokens
                        model_pricing = get_model_pricing(self.model)
                        total_cost = (total_input_tokens * model_pricing['input']) + (total_output_tokens * model_pricing['output'])
                        
                        logger.info(
                            f"stream_chat | Model: {self.model} | "
                            f"Tokens: {total_input_tokens}→{total_output_tokens} (Total: {total_tokens}) | "
                            f"Cost: ${total_cost:.6f} | "
                            f"Time: {elapsed_time:.2f}s"
                        )
                        
                        yield {
                            "type": "stop",
                            "stop_reason": event.message.stop_reason if hasattr(event, 'message') else None
                        }
                        break
                
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield {
                "type": "error",
                "error": str(e)
            }

    # NEW METHOD: Clear Web Search Tool Configuration
    def configure_web_search_tools(self, params):
        """Configure web search tools with detailed informative logging (no more red X warnings)."""
        
        # Models confirmed to support web search (tested and verified)
        # Note: Using partial string matching to handle version variations
        supported_models = [
            'claude-opus-4-1',      # ✅ Opus 4.1 - verified
            'claude-opus-4-2025',   # ✅ Opus 4 - verified (but slow)
            'claude-sonnet-4',      # ✅ Sonnet 4 - verified
            'claude-3-7-sonnet',    # ✅ Sonnet 3.7 - verified
            'claude-3-5-sonnet',    # ✅ Sonnet 3.5 - verified
            'claude-3-5-haiku',     # ✅ Haiku 3.5 - verified
        ]
        
        # Check if current model supports web search
        model_supported = any(model_prefix in self.model for model_prefix in supported_models)
        
        if model_supported:
            params["tools"] = [{
                "type": "web_search_20250305", 
                "name": "web_search"
            }]
            logger.debug(f"Added web_search_20250305 tool to request parameters")
            return True
        else:
            logger.debug(f"Model {self.model} will use training knowledge (web search not available)")
            return False

# =====================================================
# HELPER FUNCTIONS - Simplified API
# =====================================================

def create_client(api_key: str = None, model: str = None) -> ClaudeClient:
    """
    Create a Claude client with sensible defaults.
    
    Args:
        api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        model: Model to use (defaults to Sonnet 3.5)
        
    Returns:
        Configured ClaudeClient instance
    """
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No API key provided and ANTHROPIC_API_KEY not found in environment")
    
    if not model:
        model = CLAUDE_MODELS.get("sonnet-3.5", "claude-3-5-sonnet-latest")
    
    return ClaudeClient(
        api_key=api_key, 
        model=model, 
        enable_beta_features=True
    )

def stream_response(prompt: str, 
                   api_key: str = None,
                   model: str = None,
                   system_prompt: str = None) -> Iterator[str]:
    """
    Stream a response from Claude for a simple prompt.
    
    Args:
        prompt: User prompt
        api_key: API key (optional, uses env var)
        model: Model to use (optional, defaults to Sonnet 3.5)
        system_prompt: System prompt (optional)
        
    Yields:
        Text chunks as they're generated
    """
    client = create_client(api_key, model)
    
    messages = [{"role": "user", "content": prompt}]
    
    for event in client.stream_chat(messages, system=system_prompt):
        if event["type"] == "delta" and "text" in event:
            yield event["text"]

def chat_with_history(messages: List[Dict[str, str]],
                     api_key: str = None,
                     model: str = None) -> str:
    """
    Chat with Claude using conversation history.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        api_key: API key (optional)
        model: Model to use (optional)
        
    Returns:
        Complete response string
    """
    client = create_client(api_key, model)
    return client.chat(messages, max_tokens=1024, temperature=1.0)

# =====================================================
# LEGACY FUNCTIONS - For backward compatibility
# =====================================================

def get_available_models(api_key: str) -> Dict[str, Dict]:
    """Get information about available Claude models."""
    return CLAUDE_MODELS

def get_latest_model(api_key: str, model_family: str = "claude-3-5") -> str:
    """Get the latest available Claude model from a specific family."""
    if "claude-4" in model_family:
        return CLAUDE_MODELS.get("sonnet-4", "claude-sonnet-4-20250514")
    elif "claude-3-7" in model_family:
        return CLAUDE_MODELS.get("sonnet-3.7", "claude-3-7-sonnet-20250219")
    else:
        return CLAUDE_MODELS.get("sonnet-3.5", "claude-3-5-sonnet-latest")

def generate_text(prompt: str, api_key: str, model: str, max_tokens: int, temperature: float, auto_discover: bool = False) -> str:
    """Generate text response from Claude based on a prompt."""
    client = ClaudeClient(api_key=api_key, model=model)
    return client.generate_text(prompt=prompt, max_tokens=max_tokens, temperature=temperature)

def process_image(image_path: str, prompt: str, api_key: str, model: str, max_tokens: int, temperature: float, auto_discover: bool = False) -> str:
    """Process an image with Claude and generate a text response."""
    client = ClaudeClient(api_key=api_key, model=model)
    
    # Read and base64 encode the image
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    
    # Determine media type
    media_type = client._get_media_type(image_path)
    
    return client.process_image_base64(
        image_data=base64_image,
        media_type=media_type,
        prompt=prompt, 
        max_tokens=max_tokens, 
        temperature=temperature
    )

def chat(messages: List[Dict[str, Any]], api_key: str, model: str, max_tokens: int, temperature: float, auto_discover: bool = False) -> str:
    """Conduct a multi-turn chat conversation with Claude."""
    client = ClaudeClient(api_key=api_key, model=model)
    return client.chat(messages=messages, max_tokens=max_tokens, temperature=temperature)

# =====================================================
# COLLABORATIVE CHAT FUNCTIONS - For shared conversations
# =====================================================

def generate_conversation_summary(messages: List[Dict], api_key: str = None) -> str:
    """Generate a summary of the conversation using Claude"""
    try:
        if not messages or len(messages) < 2:
            return "This conversation is just getting started."
        
        # Take recent messages for summary (limit to context window)
        recent_messages = messages[-20:] if len(messages) > 20 else messages
        
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content'][:500]}" 
            for msg in recent_messages
        ])
        
        summary_prompt = f"""Please provide a brief, helpful summary of this conversation to give context to someone joining it:

{conversation_text}

Provide a 2-3 sentence summary that captures:
1. The main topic or question being discussed
2. Key points or conclusions reached
3. The current state of the conversation

Keep it concise and welcoming for new participants."""

        client = create_client(api_key)
        summary = client.generate_text(summary_prompt, max_tokens=200, temperature=0.7)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating conversation summary: {e}")
        return "This is an ongoing conversation. Feel free to read through and join in!"

def get_claude_response_for_shared_chat(recent_messages: List[Dict], new_message: str, 
                                       participant_id: str, api_key: str = None) -> str:
    """Get Claude response for shared chat with collaborative context"""
    try:
        # Build context with awareness of multiple participants
        system_prompt = f"""You are Kumori, participating in a collaborative shared conversation. Multiple people may be contributing to this discussion. The current message is from {participant_id}.

Be welcoming to all participants, acknowledge when new people join the conversation, and help facilitate meaningful dialogue between everyone involved. Reference previous points made by different participants when relevant."""

        # Format recent messages for Claude
        messages = []
        for msg in recent_messages[-15:]:  # Last 15 messages for context
            role = msg['role']
            content = msg['content']
            participant = msg.get('participant_identifier', 'user')
            
            if role == 'user':
                content = f"[{participant}]: {content}"
            
            messages.append({'role': role, 'content': content})
        
        # Add new message
        messages.append({'role': 'user', 'content': f"[{participant_id}]: {new_message}"})
        
        client = create_client(api_key)
        response = client.chat(messages, system=system_prompt, max_tokens=1024, temperature=1.0)
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting Claude response: {e}")
        return "I'm having trouble responding right now. Please try again."