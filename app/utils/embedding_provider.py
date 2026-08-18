import gc
import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("EmbeddingProvider")

MODEL_NAME = "e5-small-en-ru"

_model = None
_failed: bool = False
_available: Optional[bool] = None
_lock = threading.Lock()

def _check_available() -> bool:
    global _available
    if _available is None:
        try:
            import sentence_transformers
            _available = True
        except ImportError:
            _available = False
            logger.warning(
                "[EmbeddingProvider] sentence-transformers not found. "
                "All semantic features (Soul Memory RAG, TopicRAG, "
                "NPC memory) will switch to a simplified fallback. "
                "Installation: pip install sentence-transformers"
            )
    return _available

def get_embedder(device: str = "cpu"):
    global _model, _failed

    if _model is not None or _failed or not _check_available():
        return _model

    with _lock:
        if _model is None and not _failed:
            try:
                from sentence_transformers import SentenceTransformer

                project_root = Path(__file__).resolve().parent.parent.parent
                local_path = project_root / "app" / "utils" / MODEL_NAME
                model_target = str(local_path) if local_path.exists() else MODEL_NAME

                logger.info(
                    f"[EmbeddingProvider] Loading embedding model on "
                    f"{device.upper()} from '{model_target}'..."
                )
                _model = SentenceTransformer(model_target, device=device)
                logger.info(
                    f"[EmbeddingProvider] Embedding model successfully loaded on {device.upper()}"
                )

            except Exception as e:
                logger.error(
                    f"[EmbeddingProvider] Failed to load embedding model: {e}",
                    exc_info=True,
                )
                _model = None
                _failed = True

    return _model

def is_loaded() -> bool:
    return _model is not None

def reset_failure_state() -> None:
    global _failed
    with _lock:
        _failed = False

def unload() -> None:
    global _model, _failed
    with _lock:
        if _model is not None:
            del _model
            _model = None
            _failed = False
            gc.collect()

            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            logger.info("[EmbeddingProvider] Embedding model unloaded from memory")
