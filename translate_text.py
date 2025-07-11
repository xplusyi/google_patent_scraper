# First, you need to install the requests library
# You can do this by running: pip install requests

import requests
import urllib.parse

def translate_text(
    text: str, 
    target_language: str, 
    source_language: str, 
    engine: str = 'google'
) -> str:
    """
    Translates text using an unofficial API endpoint from the specified engine.

    DISCLAIMER: This method uses unofficial, reverse-engineered APIs. It may break
    or be rate-limited without warning. For production applications, using official
    APIs (Google Cloud Translate, Azure AI Translator) is strongly recommended.

    Args:
        text (str): The text to be translated.
        target_language (str): The language code for the target language (e.g., 'en', 'es').
        source_language (str): The language code for the source language (e.g., 'auto', 'zh-CN', 'fr').
        engine (str, optional): The translation engine to use. 
                                 Supports 'google' and 'microsoft'. Defaults to 'google'.

    Returns:
        str: The translated text, or an error message if translation fails.
        
    Raises:
        requests.exceptions.RequestException: If there is a network-related error.
        ValueError: If an unsupported engine is selected.
        Exception: If the API response format is unexpected.
    """
    
    print(f"--- Translating with {engine.capitalize()} ---")
    print(f"Original Text: '{text}'")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        if engine == 'google':
            # URL encode the text for the GET request
            encoded_text = urllib.parse.quote(text)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_language}&tl={target_language}&dt=t&q={encoded_text}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result_json = response.json()
            translated_segments = [segment[0] for segment in result_json[0] if segment[0]]
            translated_text = "".join(translated_segments)

        elif engine == 'microsoft':
            # Microsoft's endpoint uses a POST request
            url = f"https://www.bing.com/ttranslatev3?isVertical=1&&IG=C013430A3596491FB22C3554A9855479&IID=translator.5028.1"
            # For auto-detection, Bing uses 'auto-detect'
            if source_language == 'auto':
                 source_language = 'auto-detect'

            params = {'from': source_language, 'to': target_language}
            data = {'text': text}
            
            response = requests.post(url, params=params, data=data, headers=headers)
            response.raise_for_status()
            
            result_json = response.json()
            translated_text = result_json[0]['translations'][0]['text']

        else:
            raise ValueError(f"Unsupported translation engine: '{engine}'. Please use 'google' or 'microsoft'.")

        print(f"Translated Text: '{translated_text}'")
        return translated_text

    except requests.exceptions.RequestException as e:
        print(f"A network error occurred: {e}")
        raise
    except (IndexError, TypeError, KeyError):
        error_message = f"Failed to parse the translation from the {engine} API response. The format may have changed."
        print(error_message)
        raise Exception(error_message) from None


# --- Example Usage ---
if __name__ == "__main__":
    
    # Example 1: Translate from Chinese to English using Google
    source_text_cn = "你好世界"
    try:
        translate_text(source_text_cn, "en", "zh-CN", engine='google')
    except Exception:
        print("Translation failed for Example 1.")

    print("\n" + "="*40 + "\n")

    # Example 2: Translate from Chinese to English using Microsoft
    try:
        translate_text(source_text_cn, "en", "zh-Hans", engine='microsoft')
        # Note: Microsoft often uses 'zh-Hans' for Simplified Chinese
    except Exception:
        print("Translation failed for Example 2.")

    print("\n" + "="*40 + "\n")

    # Example 3: Translate from English to Spanish using Microsoft
    source_text_en = "This is a test of the Microsoft translation engine."
    try:
        translate_text(source_text_en, "es", "en", engine='microsoft')
    except Exception:
        print("Translation failed for Example 3.")
        
    print("\n" + "="*40 + "\n")

    # Example 4: Auto-detect source (French) and translate to German using Google
    source_text_fr = "Bonjour le monde. J'espère que vous passez une bonne journée."
    try:
        translate_text(source_text_fr, "de", "auto", engine='google')
    except Exception:
        print("Translation failed for Example 4.")
