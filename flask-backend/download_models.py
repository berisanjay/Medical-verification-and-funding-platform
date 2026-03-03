"""
Download spaCy models required for medical entity extraction
Run this script after installing requirements.txt
"""
import subprocess
import sys

def download_models():
    """Download required spaCy models"""
    models = [
        'en_core_web_sm',   # Standard English model
        'en_core_sci_sm'    # SciSpacy medical model
    ]
    
    print("Downloading spaCy models...")
    print("=" * 60)
    
    for model in models:
        print(f"\nDownloading {model}...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'spacy', 'download', model
            ])
            print(f"✅ Successfully downloaded {model}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to download {model}: {e}")
            
            if model == 'en_core_sci_sm':
                print("\nNote: If SciSpacy model fails, install with:")
                print("pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz")
    
    print("\n" + "=" * 60)
    print("Model download complete!")
    print("\nVerifying installation...")
    
    # Verify models
    import spacy
    for model in models:
        try:
            nlp = spacy.load(model)
            print(f"✅ {model} loaded successfully")
        except Exception as e:
            print(f"❌ {model} failed to load: {e}")


if __name__ == '__main__':
    download_models()
