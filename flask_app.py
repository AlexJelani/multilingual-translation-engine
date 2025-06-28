from flask import Flask, render_template, request, jsonify
import oci
import os
from typing import Dict
import json

app = Flask(__name__)

class OCITranslator:
    """Oracle Cloud Infrastructure Language Translation Service wrapper"""
    
    def __init__(self):
        self.config = self._load_config()
        self.client = None
        self._initialize_client()
    
    def _load_config(self) -> Dict:
        """Load OCI configuration from environment variables"""
        return {
            "user": os.getenv("OCI_USER"),
            "key_content": os.getenv("OCI_KEY_CONTENT"),
            "fingerprint": os.getenv("OCI_FINGERPRINT"),
            "tenancy": os.getenv("OCI_TENANCY"),
            "region": os.getenv("OCI_REGION", "us-ashburn-1"),
            "compartment_id": os.getenv("OCI_COMPARTMENT_ID")
        }
    
    def _initialize_client(self):
        """Initialize OCI AI Language client"""
        try:
            if all(self.config.values()):
                oci_config = {
                    "user": self.config["user"],
                    "key_content": self.config["key_content"],
                    "fingerprint": self.config["fingerprint"],
                    "tenancy": self.config["tenancy"],
                    "region": self.config["region"]
                }
                self.client = oci.ai_language.AIServiceLanguageClient(oci_config)
            else:
                print("Warning: OCI configuration not complete")
        except Exception as e:
            print(f"Failed to initialize OCI client: {str(e)}")
    
    def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Translate text using OCI Language Translation service"""
        if not self.client:
            return "OCI client not initialized. Please check your configuration."
        
        try:
            # Auto-detect source language if needed
            if source_language == "auto":
                detected_lang = self.detect_language(text)
                if detected_lang != "unknown":
                    source_language = detected_lang
                else:
                    source_language = "en"  # Default to English
            
            # Create TextDocument with proper structure
            text_doc = oci.ai_language.models.TextDocument(
                key="user_input",
                text=text,
                language_code=source_language
            )
            
            # Create translation request
            translation_details = oci.ai_language.models.BatchLanguageTranslationDetails(
                compartment_id=self.config["compartment_id"],
                target_language_code=target_language,
                documents=[text_doc]
            )
            
            response = self.client.batch_language_translation(translation_details)
            
            if response.data and response.data.documents:
                return response.data.documents[0].translated_text
            else:
                return "No translation received from OCI service."
                
        except Exception as e:
            return f"Translation error: {str(e)}"
    
    def detect_language(self, text: str) -> str:
        """Detect the language of input text"""
        if not self.client:
            return "unknown"
        
        try:
            detection_details = oci.ai_language.models.BatchDetectLanguageDetails(
                compartment_id=self.config["compartment_id"],
                documents=[{
                    "key": "user_input",
                    "text": text
                }]
            )
            
            response = self.client.batch_detect_language(detection_details)
            
            if response.data and response.data.documents:
                languages = response.data.documents[0].languages
                if languages:
                    return languages[0].code
            return "unknown"
            
        except Exception as e:
            print(f"Language detection error: {str(e)}")
            return "unknown"

# Initialize translator
translator = OCITranslator()

def get_supported_languages() -> Dict[str, str]:
    """Return supported language codes and names"""
    return {
        "en": "English",
        "ja": "Japanese (日本語)",
        "es": "Spanish (Español)",
        "fr": "French (Français)",
        "de": "German (Deutsch)",
        "it": "Italian (Italiano)",
        "pt": "Portuguese (Português)",
        "ru": "Russian (Русский)",
        "ko": "Korean (한국어)",
        "zh": "Chinese (中文)",
        "ar": "Arabic (العربية)",
        "hi": "Hindi (हिन्दी)",
        "th": "Thai (ไทย)",
        "vi": "Vietnamese (Tiếng Việt)",
        "nl": "Dutch (Nederlands)",
        "sv": "Swedish (Svenska)",
        "no": "Norwegian (Norsk)",
        "da": "Danish (Dansk)",
        "fi": "Finnish (Suomi)",
        "pl": "Polish (Polski)"
    }

@app.route('/')
def index():
    """Main page"""
    languages = get_supported_languages()
    return render_template('index.html', languages=languages)

@app.route('/translate', methods=['POST'])
def translate():
    """Translation API endpoint"""
    data = request.get_json()
    
    text = data.get('text', '')
    target_lang = data.get('target_language', 'ja')
    source_lang = data.get('source_language', 'auto')
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    # Detect language if auto-detect is selected
    detected_lang = None
    if source_lang == "auto":
        detected_lang = translator.detect_language(text)
    
    # Perform translation
    translation = translator.translate_text(text, target_lang, source_lang)
    
    return jsonify({
        'original_text': text,
        'translated_text': translation,
        'source_language': source_lang,
        'target_language': target_lang,
        'detected_language': detected_lang
    })

@app.route('/detect_language', methods=['POST'])
def detect_language():
    """Language detection API endpoint"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text.strip():
        return jsonify({'error': 'No text provided'}), 400
    
    detected_lang = translator.detect_language(text)
    languages = get_supported_languages()
    
    return jsonify({
        'detected_language': detected_lang,
        'language_name': languages.get(detected_lang, 'Unknown')
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'oci_client_initialized': translator.client is not None
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
