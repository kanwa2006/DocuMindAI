import logging
import time
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Type, TypeVar, List
from pydantic import BaseModel, ValidationError
from app.core.config import settings

try:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, InternalServerError, ServiceUnavailable, TooManyRequests
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Abstract method for standard batch generation."""
        pass
        
    @abstractmethod
    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        """Abstract method for streaming token generation."""
        pass

class DummyLLMProvider(BaseLLMProvider):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        logger.info("[Tracing] Mocking LLM generation for isolated testing.")
        time.sleep(0.5) # Simulate generation latency
        
        # Phase 1: Support dummy JSON generation for schema tests
        if "matching this schema" in system_prompt:
            import uuid
            # Extract basic marks fallback heuristically
            marks = 1.0
            if "marks=" in user_prompt:
                try: marks = float(user_prompt.split("marks=")[1].split()[0])
                except: pass
                
            return json.dumps({
                "text": f"Grounded generated question based on evidence.",
                "marks": marks,
                "difficulty": "medium",
                "sub_questions": [],
                "answer_key": "Valid answer based on context.",
                "rubric": "Award marks appropriately."
            })
            
        return "Based on the provided evidence, the system is fully grounded and operational (test.pdf, Page 1)."
        
    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        yield "Based on the provided evidence, "
        yield "the system is fully grounded "
        yield "and operational (test.pdf, Page 1)."

class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self):
        if not genai:
            logger.warning("google.generativeai not installed. Gemini provider will fail.")
            
        self.keys = settings.gemini_keys_list
        if not self.keys:
            raise ValueError("No Gemini keys found in configuration.")
            
        self.current_key_idx = 0
        self.cooldowns: Dict[str, float] = {key: 0.0 for key in self.keys}
        
        self._configure_current_key()
        
    def _configure_current_key(self):
        key = self.keys[self.current_key_idx]
        if genai:
            genai.configure(api_key=key)
        safe_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        logger.info(f"Configured Gemini with key {self.current_key_idx} ({safe_key})")
        
    def _rotate_key(self):
        original_idx = self.current_key_idx
        for _ in range(len(self.keys)):
            self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
            key = self.keys[self.current_key_idx]
            if time.time() > self.cooldowns[key]:
                self._configure_current_key()
                return
        
        # If all keys are on cooldown, just advance to the next and wait if necessary
        self.current_key_idx = (original_idx + 1) % len(self.keys)
        self._configure_current_key()
        
    def _mark_key_failed(self, cooldown_seconds: float = 60.0):
        key = self.keys[self.current_key_idx]
        self.cooldowns[key] = time.time() + cooldown_seconds
        safe_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        logger.warning(f"Key {self.current_key_idx} ({safe_key}) marked failed. Cooldown for {cooldown_seconds}s.")
        self._rotate_key()

    async def _execute_with_rotation(self, operation, *args, **kwargs):
        max_attempts = len(self.keys) * 2
        for attempt in range(max_attempts):
            key = self.keys[self.current_key_idx]
            # Check cooldown
            if time.time() < self.cooldowns[key]:
                self._rotate_key()
                continue
                
            try:
                # Wrap sync call in executor if operation is synchronous.
                # genai's generate_content is synchronous or async depending on the method.
                # Assuming `operation` is an async function or we `await` it.
                return await operation(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = isinstance(e, (ResourceExhausted, TooManyRequests)) or "429" in error_msg or "quota" in error_msg
                is_server_error = isinstance(e, (InternalServerError, ServiceUnavailable)) or "500" in error_msg or "503" in error_msg
                
                if is_rate_limit:
                    logger.warning(f"Rate limit / Quota exhaustion on key {self.current_key_idx}.")
                    self._mark_key_failed(cooldown_seconds=300.0) # 5 min cooldown for quota
                elif is_server_error:
                    logger.warning(f"Temporary server error on key {self.current_key_idx}.")
                    self._mark_key_failed(cooldown_seconds=30.0) # 30 sec cooldown for 500s
                else:
                    logger.error(f"Unrecoverable error on key {self.current_key_idx}: {e}")
                    raise e
                    
        raise Exception("All Gemini API keys exhausted or on cooldown.")

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        async def _run():
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.GEMINI_TEMPERATURE,
                    top_p=settings.GEMINI_TOP_P,
                    max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                )
            )
            # Use run_in_executor if the library isn't fully async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, model.generate_content, user_prompt)
            return response.text
            
        return await self._execute_with_rotation(_run)

    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        # Stream rotation is complex because we can't easily retry mid-stream.
        # We will attempt to get the stream object using rotation, then yield.
        async def _get_stream():
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.GEMINI_TEMPERATURE,
                    top_p=settings.GEMINI_TOP_P,
                    max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                )
            )
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: model.generate_content(user_prompt, stream=True))
            
        stream_response = await self._execute_with_rotation(_get_stream)
        
        # Iterate stream
        for chunk in stream_response:
            yield chunk.text

class LLMService:
    def __init__(self, provider: BaseLLMProvider = None):
        """
        Provider abstraction enables hot-swapping to GPT-4, Claude, or local vLLM 
        without changing the orchestration pipeline.
        """
        if provider is None:
            if settings.GEMINI_API_KEYS and genai:
                self.provider = GeminiLLMProvider()
            else:
                self.provider = DummyLLMProvider()
        else:
            self.provider = provider
        
    def _build_system_prompt(self, grounded_context: str) -> str:
        """
        Strict system prompt enforcing hallucination controls and citation formats.
        """
        return f"""You are a strict, highly accurate document analysis AI.
Your ONLY source of knowledge is the following extracted evidence.
You must NOT answer using external knowledge.
If the evidence does not contain the answer, you MUST state "I cannot answer this based on the provided documents."

Format all claims with inline citations using the document filename and page number.
Example: "The revenue increased by 20% (Q1_Report.pdf, Page 4)."

EVIDENCE BLOCKS:
{grounded_context}
"""

    async def generate_answer(self, query: str, grounded_context: str) -> Dict[str, Any]:
        start_time = time.time()
        
        if not grounded_context.strip():
            logger.warning("[Tracing] Grounded context is empty. Returning fallback response.")
            return {
                "answer": "I do not have sufficient evidence in your documents to answer this question.",
                "generation_time_sec": round(time.time() - start_time, 4)
            }
            
        system_prompt = self._build_system_prompt(grounded_context)
        user_prompt = f"Question: {query}"
        
        answer = await self.provider.generate(system_prompt, user_prompt)
        
        return {
            "answer": answer,
            "generation_time_sec": round(time.time() - start_time, 4)
        }

    async def generate_json(self, query: str, grounded_context: str, response_schema: Type[T], max_retries: int = 3) -> T:
        """
        PHASE 1: Real LLM JSON Generation with Repair Loop.
        Forces the LLM to output valid JSON matching the provided Pydantic schema.
        Auto-repairs if strict validation (like marks totaling) fails.
        """
        start_time = time.time()
        
        if not grounded_context.strip():
            raise ValueError("Grounded context is required for JSON generation.")
            
        system_prompt = self._build_system_prompt(grounded_context) + f"\n\nYou must respond ONLY with valid JSON exactly matching this schema:\n{json.dumps(response_schema.model_json_schema())}"
        
        user_prompt = f"Question: {query}"
        
        for attempt in range(max_retries):
            try:
                # In production, use provider features (e.g. OpenAI response_format={"type": "json_object"})
                raw_response = await self.provider.generate(system_prompt, user_prompt)
                
                # Cleanup potential markdown ticks if the LLM leaked them
                clean_json = raw_response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:-3].strip()
                elif clean_json.startswith("```"):
                    clean_json = clean_json[3:-3].strip()
                
                parsed_dict = json.loads(clean_json)
                validated_model = response_schema(**parsed_dict)
                logger.info(f"[Tracing] JSON generated and validated successfully on attempt {attempt+1}")
                return validated_model
                
            except json.JSONDecodeError as e:
                logger.warning(f"[Tracing] JSON decoding failed on attempt {attempt+1}: {e}")
                user_prompt += f"\n\nYour previous response was NOT valid JSON. Error: {str(e)}. Please output ONLY raw JSON without markdown ticks."
            except ValidationError as e:
                logger.warning(f"[Tracing] Pydantic strict validation failed on attempt {attempt+1}: {e.errors()}")
                # Instruct the LLM on exactly what it failed to validate
                user_prompt += f"\n\nYour previous JSON failed schema validation. Fix these errors: {e.errors()}. CRITICAL: Ensure your 'marks' fields perfectly align logically!"
                
        raise ValueError(f"Failed to generate valid JSON matching {response_schema.__name__} after {max_retries} attempts.")

llm_service = LLMService()
