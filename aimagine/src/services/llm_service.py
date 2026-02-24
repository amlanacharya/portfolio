from typing import List, Dict, Optional
import os
from groq import Groq
from dotenv import load_dotenv

class LLMService:
    def __init__(self):
        """Initialize LLM service with Groq"""
        # Load environment variables
        load_dotenv()
        
        # Get API key
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables. Please add it to your .env file")
            
        self.client = Groq(api_key=api_key)
        self.model = os.getenv('GROQ_MODEL_NAME', 'llama-3.2-90b-text-preview')
        self.max_tokens = int(os.getenv('MAX_TOKENS', '500'))
        self.temperature = float(os.getenv('TEMPERATURE', '0.7'))

    def generate_response(self, 
                         query: str, 
                         context: List[Dict],
                         system_prompt: Optional[str] = None) -> str:
        """Generate a response using the LLM with context from retrieved documents"""
        
        # Format context into a string
        context_str = "\n\n".join([f"Context {i+1}:\n{c['text']}" 
                                  for i, c in enumerate(context)])
        
        # Default system prompt if none provided
        if system_prompt is None:
            system_prompt = """You are an airline customer service assistant. 
            Use the provided context to answer questions accurately and professionally. 
            If you're unsure or the context doesn't contain the relevant information, 
            say so clearly. Always maintain a helpful and courteous tone."""

        # Construct the complete prompt
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Based on the following context, please answer this question: {query}

            {context_str}

            Please provide a clear and concise answer based on the context provided."""}
        ]

        try:
            # Generate completion
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            return completion.choices[0].message.content

        except Exception as e:
            raise Exception(f"Error generating LLM response: {str(e)}")

    def generate_followup_questions(self, 
                                  query: str, 
                                  response: str,
                                  max_questions: int = 3) -> List[str]:
        """Generate relevant follow-up questions based on the conversation"""
        
        prompt = f"""Based on this conversation:
        User: {query}
        Assistant: {response}

        Generate {max_questions} relevant follow-up questions that the user might want to ask next.
        Return only the questions, one per line."""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful airline assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            # Split response into individual questions
            questions = [q.strip() for q in 
                        completion.choices[0].message.content.split('\n') 
                        if q.strip()]
            
            return questions[:max_questions]

        except Exception as e:
            return []  # Return empty list if generation fails 