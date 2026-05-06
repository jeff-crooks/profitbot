import os
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv(Path.home() / ".env.secrets")
load_dotenv(Path(__file__).parent.parent / ".env")

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not found in ~/.env.secrets or .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def generate(
    system: str,
    prompt: str,
    max_tokens: int = 4096,
    use_cache: bool = True,
) -> str:
    client = get_client()
    system_block: dict = {"type": "text", "text": system}
    if use_cache:
        system_block["cache_control"] = {"type": "ephemeral"}
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=[system_block],
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
