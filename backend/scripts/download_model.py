#!/usr/bin/env python3
"""
Pre-download embedding model for offline deployment.
This script is run during Docker build to cache the model.
"""

import os
import sys

def download_bge_m3():
    """Download BGE-M3 model using FlagEmbedding"""
    print("Downloading BGE-M3 embedding model...")
    
    # Set HuggingFace mirror if available
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    os.environ["HF_ENDPOINT"] = hf_endpoint
    print(f"Using HuggingFace endpoint: {hf_endpoint}")
    
    try:
        from FlagEmbedding import FlagModel
        
        # Download and cache the model
        model = FlagModel(
            "BAAI/bge-m3",
            use_fp16=False,
        )
        
        # Test encoding to verify model works
        test_embedding = model.encode(["Test sentence for embedding model validation."])
        print(f"Model loaded successfully! Embedding dimension: {len(test_embedding[0])}")
        
        return True
        
    except Exception as e:
        print(f"Failed to download model: {e}", file=sys.stderr)
        return False


def download_sentence_transformer():
    """Fallback: Download using sentence-transformers"""
    print("Downloading using sentence-transformers...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer("BAAI/bge-m3")
        test_embedding = model.encode(["Test sentence"])
        print(f"Model loaded successfully! Embedding dimension: {len(test_embedding)}")
        
        return True
        
    except Exception as e:
        print(f"Failed to download model: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Pre-downloading embedding model for offline use")
    print("=" * 50)
    
    if download_bge_m3():
        print("\n✅ Model pre-download completed successfully!")
        sys.exit(0)
    elif download_sentence_transformer():
        print("\n✅ Model pre-download completed successfully (using sentence-transformers)!")
        sys.exit(0)
    else:
        print("\n❌ Model pre-download failed!")
        sys.exit(1)
