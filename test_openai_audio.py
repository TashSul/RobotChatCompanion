import os
import openai
import sys
import tempfile

def test_openai_audio_capabilities():
    """Test if the OpenAI API key works for audio capabilities (Whisper and TTS)"""
    print("Testing OpenAI API for audio capabilities...")
    
    # Get the API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.")
        return False
    
    # Initialize the OpenAI client
    try:
        client = openai.OpenAI(api_key=api_key)
        success = True
        
        # Test Text-to-Speech (TTS)
        print("\nTesting OpenAI Text-to-Speech...")
        try:
            tts_temp_file = os.path.join(tempfile.gettempdir(), "openai_tts_test.mp3")
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Hello, this is a test of OpenAI's text to speech capability."
            )
            
            response.stream_to_file(tts_temp_file)
            print(f"SUCCESS: Text-to-Speech works! Audio saved to {tts_temp_file}")
            
        except Exception as e:
            print(f"ERROR: Text-to-Speech failed: {str(e)}")
            success = False
        
        # We can't easily test Whisper without a real audio file, but we can check if the API endpoints are accessible
        print("\nChecking OpenAI Whisper API access...")
        try:
            # Just check models endpoint to see if we can access the API
            models = client.models.list()
            whisper_available = any("whisper" in model.id for model in models)
            
            if whisper_available:
                print("SUCCESS: Whisper API should be accessible (models endpoint works).")
            else:
                print("NOTE: Whisper model not explicitly found, but API is accessible.")
                
        except Exception as e:
            print(f"ERROR: Could not access models API: {str(e)}")
            success = False
            
        return success
        
    except Exception as e:
        print(f"ERROR: Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_openai_audio_capabilities()
    sys.exit(0 if success else 1)