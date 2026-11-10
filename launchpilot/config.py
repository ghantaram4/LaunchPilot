import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("LAUNCHPILOT_DATA_DIR", str(ROOT / "data"))).resolve()
MODEL = "openai/gpt-oss-120b"
ENDPOINT = "https://api.tokenfactory.nebius.com/v1/"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CREDENTIAL_FILE = Path(os.environ.get("LAUNCHPILOT_CREDENTIAL_FILE", r"D:\ReviewPilot_VSCode_Backend\.env"))

# Disable optional third-party tracing/telemetry; source text goes only to Nebius after consent.
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def credential() -> str:
    """Read ONLY NEBIUS_API_KEY, in place. Never load or copy the other project's configuration."""
    value = os.environ.get("NEBIUS_API_KEY", "").strip()
    if not value and CREDENTIAL_FILE.is_file():
        with CREDENTIAL_FILE.open(encoding="utf-8-sig") as source:
            for line in source:
                name, sep, candidate = line.partition("=")
                if sep and name.strip() == "NEBIUS_API_KEY":
                    value = candidate.strip().strip('"').strip("'")
                    break
    if not value:
        raise RuntimeError("Nebius credential missing. Set NEBIUS_API_KEY or LAUNCHPILOT_CREDENTIAL_FILE.")
    return value
