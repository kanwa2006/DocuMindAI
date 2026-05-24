import logging
import time
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator, Type, TypeVar, List
from pydantic import BaseModel, ValidationError
from app.core.config import settings
from app.services.llm_key_rotation import get_key_rotator

try:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, InternalServerError, ServiceUnavailable, TooManyRequests
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


# P3 — safe accessor for Gemini `response.text` / `chunk.text`.
#
# google-generativeai raises:
#   "Invalid operation: response.text quick accessor requires the response
#   to contain a valid Part, but none were returned. ... finish_reason is 1"
# when the candidate has no parts (e.g., empty completion, safety block,
# truncated output). Reading `.text` blindly crashes the whole stream.
#
# This helper inspects candidates / parts / finish_reason and returns a
# safe string (possibly empty, possibly a user-friendly fallback message).
# Provider internals are NOT modified — this is a thin wrapper used at the
# two access sites (`generate` and `generate_stream`).
def _safe_extract_text(response_or_chunk, *, on_empty: str = "") -> str:
    """Return text from a Gemini response/chunk without crashing on no-part responses."""
    try:
        # Fast path: the property is safe to read.
        text = getattr(response_or_chunk, "text", None)
        if text:
            return text
    except Exception as exc:
        # response.text raises ValueError when finish_reason indicates no
        # valid Part. Fall through to the part-by-part inspection.
        logger.warning(f"[Gemini] response.text accessor failed: {exc}")

    # Manual extraction from candidates / parts.
    try:
        candidates = getattr(response_or_chunk, "candidates", None) or []
        if not candidates:
            return on_empty
        candidate = candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        # finish_reason mapping (varies slightly across google-generativeai versions):
        #   0 = FINISH_REASON_UNSPECIFIED, 1 = STOP, 2 = MAX_TOKENS,
        #   3 = SAFETY, 4 = RECITATION, 5 = OTHER
        fr_value = getattr(finish_reason, "value", finish_reason)
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if parts:
            collected: List[str] = []
            for p in parts:
                p_text = getattr(p, "text", None)
                if p_text:
                    collected.append(p_text)
            if collected:
                return "".join(collected)
        # No parts. Give a user-friendly explanation for known reasons.
        if fr_value == 2:  # MAX_TOKENS
            return on_empty or (
                "[The response was cut off before it could complete. "
                "Try asking a shorter question or fewer documents.]"
            )
        if fr_value == 3:  # SAFETY
            return on_empty or (
                "[The response was blocked by a safety filter. "
                "Try rephrasing the question.]"
            )
        if fr_value == 4:  # RECITATION
            return on_empty or (
                "[The response was blocked because it would have recited "
                "the source material verbatim.]"
            )
        return on_empty
    except Exception as exc:
        logger.warning(f"[Gemini] Could not extract text from candidates: {exc}")
        return on_empty

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
            
        self._rotator = get_key_rotator()
        self.keys = self._rotator._keys
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
        self._rotator.report_rate_limit(key, retry_after_seconds=int(cooldown_seconds))
        self._rotate_key()

    def _mark_key_invalid(self):
        key = self.keys[self.current_key_idx]
        self.cooldowns[key] = float("inf")
        safe_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        logger.error(f"Key {self.current_key_idx} ({safe_key}) is invalid (403). Permanently skipping.")
        self._rotator.report_invalid_key(key)
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
                
                is_invalid_key = "403" in error_msg or "api_key_invalid" in error_msg or "INVALID_API_KEY" in str(e)

                if is_rate_limit:
                    logger.warning(f"Rate limit / Quota exhaustion on key {self.current_key_idx}.")
                    self._mark_key_failed(cooldown_seconds=300.0) # 5 min cooldown for quota
                elif is_invalid_key:
                    self._mark_key_invalid()
                elif is_server_error:
                    logger.warning(f"Temporary server error on key {self.current_key_idx}.")
                    self._mark_key_failed(cooldown_seconds=30.0) # 30 sec cooldown for 500s
                else:
                    logger.error(f"Unrecoverable error on key {self.current_key_idx}: {e}")
                    raise e
                    
        raise Exception("All Gemini API keys exhausted or on cooldown.")

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        def _make_run(model_name: str):
            async def _run():
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.GEMINI_TEMPERATURE,
                        top_p=settings.GEMINI_TOP_P,
                        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                    )
                )
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, model.generate_content, user_prompt)
                # P3 — safe accessor: never crashes on empty parts /
                # finish_reason=1/2/3 etc. Returns "" or a fallback msg
                # which the caller handles like any other answer.
                return _safe_extract_text(response)
            return _run

        try:
            return await self._execute_with_rotation(_make_run(settings.GEMINI_MODEL))
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "deprecated" in error_msg:
                logger.warning(
                    f"Model {settings.GEMINI_MODEL} unavailable (404/deprecated), "
                    f"retrying once with fallback {settings.GEMINI_FALLBACK_MODEL}"
                )
                return await self._execute_with_rotation(_make_run(settings.GEMINI_FALLBACK_MODEL))
            raise

    async def generate_stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        def _make_get_stream(model_name: str):
            async def _get_stream():
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=settings.GEMINI_TEMPERATURE,
                        top_p=settings.GEMINI_TOP_P,
                        max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
                    )
                )
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: model.generate_content(user_prompt, stream=True))
            return _get_stream

        try:
            stream_response = await self._execute_with_rotation(_make_get_stream(settings.GEMINI_MODEL))
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "deprecated" in error_msg:
                logger.warning(
                    f"Model {settings.GEMINI_MODEL} unavailable (404/deprecated), "
                    f"retrying once with fallback {settings.GEMINI_FALLBACK_MODEL}"
                )
                stream_response = await self._execute_with_rotation(_make_get_stream(settings.GEMINI_FALLBACK_MODEL))
            else:
                raise

        for chunk in stream_response:
            # P3 — safe accessor: a stream chunk can have finish_reason set
            # on the last frame with no parts; reading chunk.text would
            # raise ValueError and kill the entire SSE stream mid-response.
            token = _safe_extract_text(chunk)
            if token:
                yield token

class LLMService:
    def __init__(self, provider: BaseLLMProvider = None):
        """
        Provider abstraction enables hot-swapping to GPT-4, Claude, or local vLLM 
        without changing the orchestration pipeline.
        """
        if provider is None:
            if genai:
                try:
                    self.provider = GeminiLLMProvider()
                except RuntimeError:
                    logger.warning("No Gemini API keys configured; falling back to DummyLLMProvider.")
                    self.provider = DummyLLMProvider()
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
