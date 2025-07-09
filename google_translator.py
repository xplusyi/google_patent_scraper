# First, you need to install the requests library
# You can do this by running: pip install requests

import requests
import json
import urllib.parse

def translate_text(text: str, target_language: str, source_language: str) -> str:
    """
    Translates text using an unofficial Google Translate API endpoint.

    This method is based on the one used by many open-source projects.
    DISCLAIMER: This is not an officially supported Google API. It may break
    or be rate-limited without warning. For production applications, using the
    official Google Cloud Translate API is strongly recommended.

    Args:
        text (str): The text to be translated.
        target_language (str): The language code for the target language (e.g., 'en', 'es').
        source_language (str): The language code for the source language (e.g., 'zh-CN', 'fr').

    Returns:
        str: The translated text, or an error message if translation fails.
        
    Raises:
        requests.exceptions.RequestException: If there is a network-related error.
        Exception: If the response format is unexpected.
    """
    # URL encode the text to be translated
    encoded_text = urllib.parse.quote(text)
    
    # Construct the URL for the unofficial API endpoint
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_language}&tl={target_language}&dt=t&q={encoded_text}"
    
    # Set a User-Agent header to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Make the GET request
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        # The response is a JSON array, parse it
        result_json = response.json()
        
        # The translated text is contained within a nested list structure.
        # We iterate through the segments and join them.
        translated_segments = [segment[0] for segment in result_json[0] if segment[0]]
        translated_text = "".join(translated_segments)
        
        print(f"Original Text: '{text}'")
        print(f"Translated Text: '{translated_text}'")
        
        return translated_text

    except requests.exceptions.RequestException as e:
        print(f"A network error occurred: {e}")
        raise
    except (IndexError, TypeError):
        error_message = "Failed to parse the translation from the API response. The response format may have changed."
        print(error_message)
        raise Exception(error_message) from None


# --- Example Usage ---
if __name__ == "__main__":
    
    # Example 1: Translate from Chinese (Simplified) to English
    print("--- Example 1: Chinese (Simplified) to English ---")
    source_text_cn = "你好世界" # "Hello, world" in Chinese
    target_lang_en = "en"
    source_lang_cn = "zh-CN"
    try:
        translate_text(source_text_cn, target_lang_en, source_lang_cn)
    except Exception:
        print("Translation failed for Example 1.")

    print("\n" + "="*30 + "\n")

    # Example 2: Translate from English to Spanish
    print("--- Example 2: English to Spanish ---")
    source_text_en = "This is a test of the unofficial Google Translate API."
    target_lang_es = "es"
    source_lang_en = "en"
    try:
        translate_text(source_text_en, target_lang_es, source_lang_en)
    except Exception:
        print("Translation failed for Example 2.")

    print("\n" + "="*30 + "\n")

    # Example 3: Translate a longer text from French to German
    print("--- Example 3: French to German ---")
    source_text_fr = "Bonjour le monde. Comment ça va aujourd'hui? J'espère que vous passez une bonne journée."
    target_lang_de = "de"
    source_lang_fr = "fr"
    try:
        translate_text(source_text_fr, target_lang_de, source_lang_fr)
    except Exception:
        print("Translation failed for Example 3.")
