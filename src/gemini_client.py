"""
Gemini AI Client

Handles AI-powered company analysis using Google's Gemini API.
Uses the free tier with gemini-2.0-flash model.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import google.generativeai as genai

# System prompt for moat analysis
MOAT_ANALYSIS_PROMPT = """You are an expert financial analyst specializing in competitive moat analysis. 
Your role is to analyze companies and provide clear, actionable insights about their competitive advantages.

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

## Investment Considerations
Provide balanced considerations for investors (not recommendations).

Be specific, cite numbers when available, and acknowledge uncertainty. Keep responses focused and readable.
Do NOT provide specific buy/sell recommendations. Focus on analysis, not advice."""


@dataclass
class ChatMessage:
    """Represents a chat message."""
    role: str  # "user" or "assistant"
    content: str


class GeminiClient:
    """Client for Gemini AI interactions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key. If not provided, looks for GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = None
        self.chat_sessions: Dict[str, Any] = {}
        
        if self.api_key:
            self._configure()
    
    def _configure(self):
        """Configure the Gemini API with the API key."""
        genai.configure(api_key=self.api_key)
        
        # Use flash model for speed and free tier limits
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=MOAT_ANALYSIS_PROMPT
        )
    
    def set_api_key(self, api_key: str):
        """Set or update the API key."""
        self.api_key = api_key
        self._configure()
    
    def is_configured(self) -> bool:
        """Check if the client is properly configured."""
        return self.model is not None
    
    async def analyze_company(
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
            return "Error: Gemini API key not configured. Please provide your API key."
        
        # Build the prompt
        prompt_parts = [f"Analyze the competitive moat of **{company_name}**"]
        
        if ticker:
            prompt_parts[0] += f" (Ticker: {ticker})"
        
        prompt_parts.append("\n\n")
        
        # Add fundamentals if available
        if fundamentals:
            prompt_parts.append("### Company Financial Data\n")
            
            if fundamentals.get("roic_history"):
                prompt_parts.append("**ROIC History:**\n")
                for year, roic in fundamentals["roic_history"]:
                    prompt_parts.append(f"- {year}: {roic*100:.1f}%\n")
            
            if fundamentals.get("decay_params"):
                params = fundamentals["decay_params"]
                prompt_parts.append(f"\n**Moat Decay Analysis:**\n")
                prompt_parts.append(f"- Decay Rate (λ): {params.get('lambda', 'N/A')}\n")
                prompt_parts.append(f"- Initial ROIC: {params.get('roic_0', 'N/A')}\n")
                prompt_parts.append(f"- Terminal ROIC: {params.get('roic_terminal', 'N/A')}\n")
                prompt_parts.append(f"- Fit Quality (R²): {params.get('r_squared', 'N/A')}\n")
            
            if fundamentals.get("sector"):
                prompt_parts.append(f"\n**Sector:** {fundamentals['sector']}\n")
            
            prompt_parts.append("\n")
        
        # Add prediction market data
        if kalshi_markets:
            prompt_parts.append("### Prediction Market Data\n")
            prompt_parts.append(kalshi_markets)
            prompt_parts.append("\n\n")
        
        # Add additional context
        if additional_context:
            prompt_parts.append("### Additional Context\n")
            prompt_parts.append(additional_context)
            prompt_parts.append("\n\n")
        
        prompt_parts.append("Please provide a comprehensive moat analysis.")
        
        prompt = "".join(prompt_parts)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "API_KEY" in error_msg.upper() or "401" in error_msg:
                return "Error: Invalid API key. Please check your Gemini API key."
            elif "429" in error_msg or "quota" in error_msg.lower():
                return "Error: Rate limit exceeded. Please try again in a moment."
            else:
                return f"Error generating analysis: {error_msg}"
    
    def analyze_company_sync(
        self,
        company_name: str,
        ticker: Optional[str] = None,
        fundamentals: Optional[Dict] = None,
        kalshi_markets: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """Synchronous version of analyze_company."""
        if not self.is_configured():
            return "Error: Gemini API key not configured. Please provide your API key."
        
        # Build the prompt
        prompt_parts = [f"Analyze the competitive moat of **{company_name}**"]
        
        if ticker:
            prompt_parts[0] += f" (Ticker: {ticker})"
        
        prompt_parts.append("\n\n")
        
        # Add fundamentals if available
        if fundamentals:
            prompt_parts.append("### Company Financial Data\n")
            
            if fundamentals.get("roic_history"):
                prompt_parts.append("**ROIC History:**\n")
                for year, roic in fundamentals["roic_history"]:
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
            
            if fundamentals.get("sector"):
                prompt_parts.append(f"\n**Sector:** {fundamentals['sector']}\n")
            
            prompt_parts.append("\n")
        
        # Add prediction market data
        if kalshi_markets:
            prompt_parts.append("### Prediction Market Data\n")
            prompt_parts.append(kalshi_markets)
            prompt_parts.append("\n\n")
        
        # Add additional context
        if additional_context:
            prompt_parts.append("### Additional Context\n")
            prompt_parts.append(additional_context)
            prompt_parts.append("\n\n")
        
        prompt_parts.append("Please provide a comprehensive moat analysis.")
        
        prompt = "".join(prompt_parts)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "API_KEY" in error_msg.upper() or "401" in error_msg:
                return "Error: Invalid API key. Please check your Gemini API key."
            elif "429" in error_msg or "quota" in error_msg.lower():
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
            return "Error: Gemini API key not configured. Please provide your API key."
        
        try:
            # Create or get chat session
            if session_id not in self.chat_sessions:
                # Start new chat with context
                initial_context = ""
                if company_context:
                    initial_context = f"We are discussing the following company:\n{company_context}\n\n"
                
                self.chat_sessions[session_id] = self.model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": [initial_context + "I'd like to learn more about this company."]
                        },
                        {
                            "role": "model", 
                            "parts": ["I'm ready to help you analyze this company. What would you like to know?"]
                        }
                    ] if initial_context else []
                )
            
            chat = self.chat_sessions[session_id]
            response = chat.send_message(message)
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                return "Error: Rate limit exceeded. Please try again in a moment."
            else:
                return f"Error: {error_msg}"
    
    def clear_chat(self, session_id: str):
        """Clear a chat session."""
        if session_id in self.chat_sessions:
            del self.chat_sessions[session_id]


# Singleton instance
_client: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    """Get or create the Gemini client singleton."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client


if __name__ == "__main__":
    # Test with API key from environment
    import sys
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY environment variable to test")
        sys.exit(0)
    
    client = get_gemini_client()
    client.set_api_key(api_key)
    
    print("Testing Gemini client...")
    result = client.analyze_company_sync(
        company_name="Apple Inc",
        ticker="AAPL",
        fundamentals={
            "sector": "Technology",
            "roic_history": [(2020, 0.25), (2021, 0.28), (2022, 0.30)],
        }
    )
    print(result[:500] + "..." if len(result) > 500 else result)
