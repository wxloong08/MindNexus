#!/usr/bin/env python3
"""
Pre-download embedding model for offline deployment.
This script is run during Docker build to cache the model.
"""

import os
import sys

# Default model - using lightweight bge-small-zh-v1.5 for low-memory servers
# Change to BAAI/bge-m3 if you have 4GB+ RAM available
MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")


def download_with_sentence_transformers():
    """Download model using sentence-transformers (most compatible)"""
    print(f"Downloading {MODEL_NAME} using sentence-transformers...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model = SentenceTransformer(MODEL_NAME)
        test_embedding = model.encode(["测试句子用于验证模型"])
        print(f"Model loaded successfully! Embedding dimension: {len(test_embedding)}")
        
        return True
        
    except Exception as e:
        print(f"Failed to download model: {e}", file=sys.stderr)
        return False


def download_with_flag_embedding():
    """Download BGE model using FlagEmbedding (better for BGE models)"""
    if "bge" not in MODEL_NAME.lower():
        return False
        
    print(f"Downloading {MODEL_NAME} using FlagEmbedding...")
    
    try:
        from FlagEmbedding import FlagModel
        
        model = FlagModel(MODEL_NAME, use_fp16=False)
        test_embedding = model.encode(["测试句子用于验证模型"])
        print(f"Model loaded successfully! Embedding dimension: {len(test_embedding[0])}")
        
        return True
        
    except ImportError:
        print("FlagEmbedding not available, will try sentence-transformers")
        return False
    except Exception as e:
        print(f"Failed to download with FlagEmbedding: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    print("=" * 50)
    print(f"Pre-downloading embedding model: {MODEL_NAME}")
    print("=" * 50)
    
    # Set HuggingFace mirror if available
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    os.environ["HF_ENDPOINT"] = hf_endpoint
    print(f"Using HuggingFace endpoint: {hf_endpoint}")
    
    # Try FlagEmbedding first for BGE models, then sentence-transformers
    if download_with_flag_embedding() or download_with_sentence_transformers():
        print(f"\n✅ Model pre-download completed successfully!")
        print(f"   Model: {MODEL_NAME}")
        sys.exit(0)
    else:
        print(f"\n❌ Model pre-download failed!")
        sys.exit(1)
