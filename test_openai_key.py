import os
import openai
import sys

def test_openai_api_key():
    """Test if the OpenAI API key is working properly"""
    print("Testing OpenAI API key...")
    
    # Get the API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        return False
    
    # Initialize the OpenAI client
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Make a simple request
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[{"role": "user", "content": "Hello, are you working? Reply with a very short message."}]
        )
        
        # Extract and print the response
        message = response.choices[0].message.content
        print(f"Response received: {message}")
        print("SUCCESS: OpenAI API key is working correctly.")
        return True
        
    except openai.APIError as e:
        print(f"ERROR: API Error: {str(e)}")
    except openai.APIConnectionError as e:
        print(f"ERROR: Connection Error: {str(e)}")
    except openai.RateLimitError as e:
        print(f"ERROR: Rate Limit Error: {str(e)}")
    except openai.AuthenticationError as e:
        print(f"ERROR: Authentication Error: Invalid API key.")
    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
    
    return False

if __name__ == "__main__":
    success = test_openai_api_key()
    sys.exit(0 if success else 1)