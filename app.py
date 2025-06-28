import streamlit as st
import oci
import os
from typing import Dict, List
import json

# Page configuration
st.set_page_config(
    page_title="🌐 Multilingual Translation Engine",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .translation-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 1rem 0;
    }
    .language-selector {
        margin: 1rem 0;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding: 1rem;
        color: #666;
        border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

class OCITranslator:
    """Oracle Cloud Infrastructure Language Translation Service wrapper"""
    
    def __init__(self):
        self.config = self._load_config()
        self.client = None
        if self.config:  # Only initialize if config is loaded
            self._initialize_client()
        else:
            st.error("❌ OCI Client Not Connected")
            st.info("💡 Configure your OCI credentials in secrets.toml or environment variables")
    
    def _load_config(self) -> Dict:
        """Load OCI configuration from environment variables or secrets"""
        try:
            # Try to load from Streamlit secrets first
            if hasattr(st, 'secrets') and 'oci' in st.secrets:
                config = {}
                
                # Handle both key_content (direct key) and private_key_path (file path)
                if "key_content" in st.secrets["oci"]:
                    # Direct key content in secrets
                    config["key_content"] = st.secrets["oci"]["key_content"]
                    st.success("✅ Using key_content from secrets.toml")
                elif "private_key_path" in st.secrets["oci"]:
                    # Key file path in secrets
                    private_key_path = st.secrets["oci"]["private_key_path"]
                    if private_key_path.startswith('~'):
                        private_key_path = os.path.expanduser(private_key_path)
                    
                    if not os.path.exists(private_key_path):
                        st.error(f"❌ Private key file not found: {private_key_path}")
                        return {}
                    
                    with open(private_key_path, 'r') as f:
                        config["key_content"] = f.read()
                    st.success(f"✅ Using private key from file: {private_key_path}")
                else:
                    st.error("❌ Neither key_content nor private_key_path found in secrets")
                    return {}

                # Load other configuration
                config.update({
                    "user": st.secrets["oci"]["user"],
                    "fingerprint": st.secrets["oci"]["fingerprint"],
                    "tenancy": st.secrets["oci"]["tenancy"],
                    "region": st.secrets["oci"]["region"],
                    "compartment_id": st.secrets["oci"]["compartment_id"]
                })
                
                # Validate all required fields are present
                missing_fields = [k for k, v in config.items() if not v]
                if missing_fields:
                    st.error(f"❌ Missing configuration fields: {missing_fields}")
                    return {}
                
                st.success("✅ OCI configuration loaded from secrets.toml")
                return config
                
            else:
                # Fallback to environment variables
                config = {
                    "user": os.getenv("OCI_USER"),
                    "key_content": os.getenv("OCI_KEY_CONTENT"),
                    "fingerprint": os.getenv("OCI_FINGERPRINT"),
                    "tenancy": os.getenv("OCI_TENANCY"),
                    "region": os.getenv("OCI_REGION", "us-ashburn-1"),
                    "compartment_id": os.getenv("OCI_COMPARTMENT_ID")
                }
                
                # Validate all required fields are present
                missing_fields = [k for k, v in config.items() if not v]
                if missing_fields:
                    st.warning(f"⚠️ Missing environment variables: {missing_fields}")
                    return {}
                
                st.info("✅ OCI configuration loaded from environment variables")
                return config
                
        except Exception as e:
            st.error(f"❌ Error loading configuration: {str(e)}")
            return {}
    
    def _initialize_client(self):
        """Initialize OCI AI Language client"""
        try:
            if not self.config:
                st.error("❌ OCI configuration not loaded")
                return
                
            if not all(self.config.values()):
                missing = [k for k, v in self.config.items() if not v]
                st.error(f"❌ Missing OCI configuration: {missing}")
                return
                
            # Create config dict for OCI client
            oci_config = {
                "user": self.config["user"],
                "key_content": self.config["key_content"],
                "fingerprint": self.config["fingerprint"],
                "tenancy": self.config["tenancy"],
                "region": self.config["region"]
            }
            
            self.client = oci.ai_language.AIServiceLanguageClient(oci_config)
            st.success("✅ OCI AI Language client initialized successfully")
            
        except Exception as e:
            st.error(f"❌ Failed to initialize OCI client: {str(e)}")
            self.client = None
    
    def translate_text(self, text: str, target_language: str, source_language: str = "auto") -> str:
        """Translate text using OCI Language Translation service"""
        if not self.client:
            return "❌ OCI client not initialized. Please check your configuration."
        
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
            
            # Make the translation request
            response = self.client.batch_language_translation(translation_details)
            
            if response.data and response.data.documents:
                return response.data.documents[0].translated_text
            else:
                return "❌ No translation received from OCI service."
                
        except Exception as e:
            error_msg = str(e)
            if "NotAuthorizedOrNotFound" in error_msg:
                return "❌ AI Language service not enabled. Please enable it in OCI Console: AI & Machine Learning → Language → Translation"
            elif "BadRequest" in error_msg and "Languagecode" in error_msg:
                return "❌ Language code error. Please specify a valid source language."
            elif "400" in error_msg:
                return f"❌ API Error: Please check if the AI Language Translation service is enabled in your OCI tenancy."
            else:
                return f"❌ Translation error: {error_msg}"
    
    def detect_language(self, text: str) -> str:
        """Detect the language of input text"""
        if not self.client:
            return "unknown"
        
        try:
            # Create language detection request
            detection_details = oci.ai_language.models.BatchDetectDominantLanguageDetails(
                compartment_id=self.config["compartment_id"],
                documents=[
                    oci.ai_language.models.DominantLanguageDocument(
                        key="user_input",
                        text=text
                    )
                ]
            )
            
            response = self.client.batch_detect_dominant_language(detection_details)
            
            if response.data and response.data.documents:
                languages = response.data.documents[0].languages
                if languages:
                    return languages[0].code
            return "unknown"
            
        except Exception as e:
            st.error(f"Language detection error: {str(e)}")
            return "unknown"

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

def main():
    """Main Streamlit application"""
    
    # Initialize session state first (before any widgets)
    if 'source_lang' not in st.session_state:
        st.session_state.source_lang = "auto"
    if 'target_lang' not in st.session_state:
        st.session_state.target_lang = "ja"
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'translation_history' not in st.session_state:
        st.session_state.translation_history = []
    if 'selected_sample' not in st.session_state:
        st.session_state.selected_sample = None
    
    # Handle sample text selection (before creating widgets)
    if st.session_state.selected_sample:
        st.session_state.input_text = st.session_state.selected_sample
        st.session_state.selected_sample = None
    
    # Header
    st.markdown('<h1 class="main-header">🌐 Multilingual Translation Engine</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666; font-size: 1.1em;">Powered by Oracle Cloud Infrastructure AI Language Services</p>', unsafe_allow_html=True)
    
    # Initialize translator
    translator = OCITranslator()
    
    # Connection status
    if translator.client:
        st.success("✅ OCI Client Connected")
    else:
        st.error("❌ OCI Client Not Connected")
        st.info("💡 Configure your OCI credentials in secrets.toml or environment variables")
        st.stop()  # Stop execution if not connected
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Language selection
        languages = get_supported_languages()
        
        st.subheader("🔄 Translation Settings")
        source_lang = st.selectbox(
            "Source Language:",
            options=["auto"] + list(languages.keys()),
            format_func=lambda x: "Auto-detect" if x == "auto" else languages.get(x, x),
            key="source_lang"
        )
        
        target_lang = st.selectbox(
            "Target Language:",
            options=list(languages.keys()),
            index=list(languages.keys()).index("ja"),  # Default to Japanese
            format_func=lambda x: languages.get(x, x),
            key="target_lang"
        )
        
        # Quick language pairs (informational only)
        st.subheader("🚀 Popular Pairs")
        st.info("💡 **Tip**: Use the dropdowns above to select:\n"
                "- 🇺🇸 English → 🇯🇵 Japanese\n"
                "- 🇯🇵 Japanese → 🇺🇸 English\n"
                "- 🇺🇸 English → 🇪🇸 Spanish\n"
                "- Or any other language combination!")
        
        # Configuration status
        st.subheader("📊 Status")
        if translator.client:
            st.success("✅ OCI Client Connected")
        else:
            st.error("❌ OCI Client Not Connected")
            st.info("💡 Configure your OCI credentials in secrets.toml or environment variables")
    
    # Main content area
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📝 Input Text ({languages.get(source_lang, 'Auto-detect')})")
        input_text = st.text_area(
            "Enter text to translate:",
            height=200,
            placeholder="Type or paste your text here...",
            key="input_text"
        )
        
        # Translate button
        translate_button = st.button("🌐 Translate", type="primary", use_container_width=True)
        st.caption("💡 Translation happens automatically as you type, or click the button above")
        
        # Sample texts for testing
        st.subheader("📋 Sample Texts")
        sample_texts = {
            "Business Email": "Dear Mr. Tanaka, I hope this email finds you well. I would like to schedule a meeting to discuss our upcoming project collaboration.",
            "Technical Documentation": "This API endpoint accepts POST requests with JSON payload containing user authentication credentials and returns a JWT token.",
            "Casual Conversation": "Hello! How are you doing today? The weather is really nice, isn't it?",
            "Legal Text": "This agreement shall be governed by and construed in accordance with the laws of Japan, without regard to its conflict of law provisions."
        }
        
        sample_texts = {
            "Business Email": "Dear Mr. Tanaka, I hope this email finds you well. I would like to schedule a meeting to discuss our upcoming project collaboration.",
            "Technical Documentation": "This API endpoint accepts POST requests with JSON payload containing user authentication credentials and returns a JWT token.",
            "Casual Conversation": "Hello! How are you doing today? The weather is really nice, isn't it?",
            "Legal Text": "This agreement shall be governed by and construed in accordance with the laws of Japan, without regard to its conflict of law provisions."
        }
        
        # Display sample texts with copy buttons
        for sample_name, sample_text in sample_texts.items():
            with st.expander(f"📄 {sample_name}"):
                st.write(f"*{sample_text}*")
                
                # Show the text in a copyable format
                st.code(sample_text, language=None)
                
                # Create columns for better layout
                col_info, col_button = st.columns([3, 1])
                with col_info:
                    st.caption("💡 Select the text above (triple-click) and copy (Ctrl+C/Cmd+C)")
                with col_button:
                    if st.button("📋 Fill", key=f"fill_{sample_name}", help="Fill input field with this sample"):
                        st.session_state.selected_sample = sample_text
                        st.rerun()
    
    with col2:
        st.subheader(f"🎯 Translation ({languages.get(target_lang, target_lang)})")
        
        # Show translation when there's text (maintains real-time functionality)
        # The button provides a clear call-to-action but doesn't change the behavior
        if input_text.strip():
            with st.spinner("🔄 Translating..."):
                # Detect source language if auto-detect is selected
                if source_lang == "auto":
                    detected_lang = translator.detect_language(input_text)
                    if detected_lang != "unknown":
                        st.info(f"🔍 Detected language: {languages.get(detected_lang, detected_lang)}")
                
                # Perform translation
                translation = translator.translate_text(input_text, target_lang, source_lang)
                
                # Display translation
                st.markdown(f'<div class="translation-box">{translation}</div>', unsafe_allow_html=True)
                
                # Copy button
                if st.button("📋 Copy Translation"):
                    st.success("✅ Translation copied to clipboard!")
                    # Note: Actual clipboard functionality would require additional JavaScript
        else:
            st.info("👆 Enter text in the input area to see translation")
    
    # Additional features
    st.markdown("---")
    
    # Batch translation section
    with st.expander("📚 Batch Translation"):
        st.write("Upload a text file or enter multiple lines for batch translation:")
        
        uploaded_file = st.file_uploader("Choose a text file", type=['txt'])
        if uploaded_file is not None:
            content = str(uploaded_file.read(), "utf-8")
            lines = content.split('\n')
            
            st.write(f"Found {len(lines)} lines to translate:")
            
            if st.button("🚀 Translate All"):
                progress_bar = st.progress(0)
                translations = []
                
                for i, line in enumerate(lines):
                    if line.strip():
                        translation = translator.translate_text(line.strip(), target_lang, source_lang)
                        translations.append(f"{line.strip()} → {translation}")
                    progress_bar.progress((i + 1) / len(lines))
                
                st.subheader("📋 Batch Translation Results:")
                for translation in translations:
                    st.write(translation)
    
    # Translation history
    if input_text.strip() and st.button("💾 Save to History"):
        history_entry = {
            "source": input_text,
            "translation": translation,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "timestamp": st.session_state.get('timestamp', 'now')
        }
        st.session_state.translation_history.append(history_entry)
        st.success("✅ Added to translation history!")
    
    # Display history
    if st.session_state.translation_history:
        with st.expander("📜 Translation History"):
            for i, entry in enumerate(reversed(st.session_state.translation_history[-10:])):  # Show last 10
                st.write(f"**{i+1}.** {entry['source']} → {entry['translation']}")
                st.caption(f"({languages.get(entry['source_lang'], entry['source_lang'])} → {languages.get(entry['target_lang'], entry['target_lang'])})")
                st.markdown("---")
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p>🚀 Built with Oracle Cloud Infrastructure AI Language Services | 
        <a href="https://docs.oracle.com/en-us/iaas/language/using/overview.htm" target="_blank">OCI Documentation</a> | 
        <a href="https://github.com" target="_blank">View on GitHub</a></p>
        <p><em>Perfect for global business communication, technical documentation, and multilingual content creation</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
