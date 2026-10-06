"""
AI Client - Unified interface for multiple AI providers

Default engine is a small local model (Qwen2.5-1.5B-Instruct via llama.cpp).
It runs on CPU, costs nothing, and does not need an API key.

Optional cloud fallbacks, used only when the local model is disabled:
- Groq
- Google Gemini
"""

import os
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .trajectory import percent_label

# Groq configuration (OpenAI-compatible)
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Best free model on Groq

# Local engine. Qwen2.5 1.5B Instruct is small enough for a laptop CPU
# and still follows the moat-analysis format.
LOCAL_MODEL_REPO = "bartowski/Qwen2.5-1.5B-Instruct-GGUF"
LOCAL_MODEL_FILE = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
LOCAL_MODEL_NAME = "Qwen2.5-1.5B-Instruct"
MODEL_DIR = Path(__file__).parent.parent / "models"
LOCAL_MAX_TOKENS = 700
LOCAL_CHAT_MAX_TOKENS = 320

# System prompt for moat analysis
MOAT_ANALYSIS_PROMPT = """You are an expert financial analyst specializing in competitive moat analysis. 
Your role is to analyze companies and provide clear, actionable insights about their competitive advantages.
Keep the full response under 280 words. Prefer short bullets over long paragraphs.

When analyzing a company, structure your response as follows:

## Moat Assessment
Rate the moat as: **Wide**, **Narrow**, or **None**
Explain the primary sources of competitive advantage.

## Competitive Advantages
List and explain the key advantages (e.g., brand, network effects, switching costs, cost advantages, intangible assets).

## Threats & Risks
Identify the main competitive threats and business risks.

## Financial Health
Comment on the company's financial metrics if data is provided.

## Prediction Market Sentiment
If prediction market data is provided, analyze what the market expects and any notable odds.
Only mention markets that are listed in the data. Do not invent markets, sports, or events.

## Investment Considerations
Provide balanced considerations for investors (not recommendations).

Be specific, cite numbers when available, and acknowledge uncertainty. Keep responses focused and readable.
Do NOT provide specific buy/sell recommendations. Focus on analysis, not advice."""


@dataclass
class ChatMessage:
    """Represents a chat message."""
    role: str  # "user" or "assistant" or "system"
    content: str


class AIClient:
    """
    Unified AI client supporting multiple providers.
    
    Priority order:
    1. Local Qwen2.5-1.5B (default, no API key)
    2. GROQ_API_KEY, only if MOATY_DISABLE_LOCAL=1
    3. GEMINI_API_KEY, only if MOATY_DISABLE_LOCAL=1
    """
    
    def __init__(self):
        """Initialize the AI client with the local engine or an optional API key."""
        self.groq_key = os.environ.get("GROQ_API_KEY")
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        
        self.provider = None
        self.client = None
        self.llm = None
        self.model_name: Optional[str] = None
        self.gemini_model = None
        self.chat_histories: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()
        self._setup_error: Optional[str] = None
        
        self._configure()
    
    def _configure(self):
        """Configure the client. Local model wins unless explicitly disabled."""
        self.provider = None
        self.client = None
        self.llm = None
        self.gemini_model = None
        self.model_name = None
        self._setup_error = None

        use_local = os.environ.get("MOATY_DISABLE_LOCAL") != "1"
        if use_local:
            try:
                if self._configure_local():
                    self.provider = "local"
                    self.model_name = LOCAL_MODEL_NAME
                    return
            except Exception as e:
                self._setup_error = str(e)
                print(f"Failed to configure local AI: {e}")
        
        # Cloud fallbacks when the local engine is turned off or failed to load.
        if self.groq_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.groq_key,
                    base_url=GROQ_BASE_URL
                )
                self.provider = "groq"
                self.model_name = GROQ_MODEL
                return
            except Exception as e:
                print(f"Failed to configure Groq: {e}")
        
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
                self.gemini_model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    system_instruction=MOAT_ANALYSIS_PROMPT
                )
                self.provider = "gemini"
                self.model_name = "gemini-2.0-flash"
                return
            except Exception as e:
                print(f"Failed to configure Gemini: {e}")

    def ensure_local_model(self) -> Path:
        """Return the GGUF path, downloading it from Hugging Face if needed."""
        override = os.environ.get("MOATY_MODEL_PATH")
        path = Path(override) if override else MODEL_DIR / LOCAL_MODEL_FILE
        if path.exists() and path.stat().st_size > 900_000_000:
            return path

        path.parent.mkdir(parents=True, exist_ok=True)
        from huggingface_hub import hf_hub_download

        print(f"Downloading local AI engine {LOCAL_MODEL_NAME}...")
        downloaded = hf_hub_download(
            repo_id=LOCAL_MODEL_REPO,
            filename=LOCAL_MODEL_FILE,
            local_dir=str(path.parent),
        )
        return Path(downloaded)

    def _configure_local(self) -> bool:
        """Load the local GGUF model with llama.cpp."""
        model_path = self.ensure_local_model()
        from llama_cpp import Llama

        threads = max(1, min(4, os.cpu_count() or 2))
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=threads,
            n_batch=128,
            verbose=False,
        )
        return True

    def _complete(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        """Run one chat completion on the active provider."""
        if self.provider == "local":
            # Keep the prompt inside the 2048 token window without duplicating short chats.
            trimmed = messages if len(messages) <= 8 else messages[:2] + messages[-6:]
            with self._lock:
                response = self.llm.create_chat_completion(
                    messages=trimmed,
                    temperature=0.6,
                    max_tokens=max_tokens,
                )
            return response["choices"][0]["message"]["content"] or ""

        if self.provider == "groq":
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        raise RuntimeError(f"Unsupported provider for chat completion: {self.provider}")
    
    def set_groq_key(self, api_key: str):
        """Set Groq API key."""
        self.groq_key = api_key
        os.environ["GROQ_API_KEY"] = api_key
        self._configure()
    
    def set_gemini_key(self, api_key: str):
        """Set Gemini API key."""
        self.gemini_key = api_key
        os.environ["GEMINI_API_KEY"] = api_key
        self._configure()
    
    def set_api_key(self, api_key: str, provider: str = "groq"):
        """Set API key for specified provider."""
        if provider == "groq":
            self.set_groq_key(api_key)
        elif provider == "gemini":
            self.set_gemini_key(api_key)
    
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self.provider is not None
    
    def get_provider(self) -> Optional[str]:
        """Get the current AI provider name."""
        return self.provider

    def get_model_name(self) -> Optional[str]:
        """Get the model id currently serving analysis."""
        return self.model_name

    def get_setup_error(self) -> Optional[str]:
        """Return the last local-engine setup error, if configuration failed."""
        return self._setup_error
    
    def _build_prompt(
        self,
        company_name: str,
        ticker: Optional[str] = None,
        fundamentals: Optional[Dict] = None,
        kalshi_markets: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """Build the analysis prompt."""
        prompt_parts = [f"Analyze the competitive moat of **{company_name}**"]
        
        if ticker:
            prompt_parts[0] += f" (Ticker: {ticker})"
        
        prompt_parts.append("\n\n")
        
        if fundamentals:
            prompt_parts.append("### Company Financial Data\n")
            
            if fundamentals.get("roic_history"):
                prompt_parts.append("**ROIC History:**\n")
                for year, roic in fundamentals["roic_history"][-5:]:
                    roic_pct = roic * 100 if isinstance(roic, float) else roic
                    prompt_parts.append(f"- {year}: {roic_pct:.1f}%\n")
            
            if fundamentals.get("decay_params"):
                params = fundamentals["decay_params"]
                prompt_parts.append(f"\n**Moat Decay Analysis:**\n")
                if params.get('lambda') is not None:
                    prompt_parts.append(f"- Decay Rate (λ): {params['lambda']:.4f}\n")
                if params.get('roic_0') is not None:
                    prompt_parts.append(f"- Initial ROIC: {params['roic_0']*100:.1f}%\n")
                if params.get('roic_terminal') is not None:
                    prompt_parts.append(f"- Terminal ROIC: {params['roic_terminal']*100:.1f}%\n")
                if params.get('r_squared') is not None:
                    prompt_parts.append(f"- Fit Quality (R²): {params['r_squared']:.3f}\n")

            trajectory = fundamentals.get("trajectory") or {}
            year_5 = trajectory.get("year_5") or {}
            year_10 = trajectory.get("year_10") or {}
            if year_5.get("roic") is not None and year_10.get("roic") is not None:
                prompt_parts.append("\n**Projected return on capital (use these figures):**\n")
                prompt_parts.append(
                    f"- In 5 years ({year_5.get('year')}): {percent_label(year_5['roic'])}\n"
                )
                prompt_parts.append(
                    f"- In 10 years ({year_10.get('year')}): {percent_label(year_10['roic'])}\n"
                )
                if trajectory.get("terminal_roic") is not None:
                    prompt_parts.append(
                        f"- Long-run ROIC: {percent_label(trajectory['terminal_roic'])}\n"
                    )
            
            if fundamentals.get("sector"):
                prompt_parts.append(f"\n**Sector:** {fundamentals['sector']}\n")
            
            prompt_parts.append("\n")
        
        if kalshi_markets:
            prompt_parts.append("### Prediction Market Data\n")
            prompt_parts.append(kalshi_markets)
            prompt_parts.append("\n\n")
        
        if additional_context:
            prompt_parts.append("### Additional Context\n")
            prompt_parts.append(additional_context)
            prompt_parts.append("\n\n")
        
        prompt_parts.append("Please provide a concise moat analysis.")
        
        return "".join(prompt_parts)
    
    def analyze_company_sync(
        self,
        company_name: str,
        ticker: Optional[str] = None,
        fundamentals: Optional[Dict] = None,
        kalshi_markets: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Perform moat analysis on a company.
        
        Args:
            company_name: Name of the company
            ticker: Stock ticker symbol
            fundamentals: Dictionary of financial data
            kalshi_markets: Formatted string of prediction market data
            additional_context: Any additional context to include
            
        Returns:
            AI-generated analysis
        """
        if not self.is_configured():
            return "Error: Local AI engine is not ready. Restart the API so it can download the model, or set GROQ_API_KEY."
        
        prompt = self._build_prompt(
            company_name, ticker, fundamentals, kalshi_markets, additional_context
        )
        
        try:
            if self.provider in ("local", "groq"):
                return self._complete(
                    [
                        {"role": "system", "content": MOAT_ANALYSIS_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    LOCAL_MAX_TOKENS if self.provider == "local" else 2000,
                )
            
            elif self.provider == "gemini":
                response = self.gemini_model.generate_content(prompt)
                return response.text

            return "Error: AI provider is not available."
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "invalid" in error_msg.lower():
                return "Error: Invalid API key. Please check your API key."
            elif "429" in error_msg or "rate" in error_msg.lower():
                return "Error: Rate limit exceeded. Please try again in a moment."
            else:
                return f"Error generating analysis: {error_msg}"
    
    def chat(
        self,
        session_id: str,
        message: str,
        company_context: Optional[str] = None
    ) -> str:
        """
        Continue a chat conversation about a company.
        
        Args:
            session_id: Unique identifier for the chat session
            message: User's message
            company_context: Context about the company being discussed
            
        Returns:
            AI response
        """
        if not self.is_configured():
            return "Error: Local AI engine is not ready."
        
        # Initialize chat history if needed
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = [
                {"role": "system", "content": MOAT_ANALYSIS_PROMPT}
            ]
            if company_context:
                self.chat_histories[session_id].append({
                    "role": "system",
                    "content": f"Context about the company being discussed:\n{company_context}"
                })
        
        # Add user message
        self.chat_histories[session_id].append({
            "role": "user",
            "content": message
        })
        
        try:
            if self.provider in ("local", "groq"):
                assistant_message = self._complete(
                    self.chat_histories[session_id],
                    LOCAL_CHAT_MAX_TOKENS if self.provider == "local" else 1500,
                )
                
            elif self.provider == "gemini":
                # For Gemini, we need to format the history differently
                import google.generativeai as genai
                
                # Convert history to Gemini format
                gemini_history = []
                for msg in self.chat_histories[session_id][1:]:  # Skip system message
                    role = "user" if msg["role"] == "user" else "model"
                    if msg["role"] == "system":
                        role = "user"  # Gemini doesn't have system role in history
                    gemini_history.append({
                        "role": role,
                        "parts": [msg["content"]]
                    })
                
                chat = self.gemini_model.start_chat(history=gemini_history[:-1])
                response = chat.send_message(message)
                assistant_message = response.text
            
            # Store assistant response
            self.chat_histories[session_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                return "Error: Rate limit exceeded. Please try again in a moment."
            else:
                return f"Error: {error_msg}"
    
    def clear_chat(self, session_id: str):
        """Clear a chat session."""
        if session_id in self.chat_histories:
            del self.chat_histories[session_id]


# Singleton instance
_client: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """Get or create the AI client singleton."""
    global _client
    if _client is None:
        _client = AIClient()
    return _client


# Backwards compatibility aliases
def get_gemini_client():
    """Backwards compatibility - returns the unified AI client."""
    return get_ai_client()


GeminiClient = AIClient  # Type alias for backwards compatibility


if __name__ == "__main__":
    # Test the client
    client = get_ai_client()
    
    if client.is_configured():
        print(f"AI client configured with provider: {client.get_provider()}")
        print("\nTesting analysis...")
        result = client.analyze_company_sync(
            company_name="Apple Inc",
            ticker="AAPL",
            fundamentals={
                "sector": "Technology",
                "roic_history": [(2020, 0.25), (2021, 0.28), (2022, 0.30)],
            }
        )
        print(result[:500] + "..." if len(result) > 500 else result)
    else:
        print("Local AI engine is not ready.")
        if client.get_setup_error():
            print(client.get_setup_error())
