import requests
from PyQt6.QtCore import QThread, pyqtSignal

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL = "claude-sonnet-5"
MAX_TOKENS = 2000


class PromptWriterWorker(QThread):
    """Calls the Anthropic Messages API in the background to rewrite a rough
    idea into a structured video-generation prompt."""
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key: str, system_prompt: str, user_message: str):
        super().__init__()
        self._api_key = api_key
        self._system_prompt = system_prompt
        self._user_message = user_message

    def run(self):
        try:
            resp = requests.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "system": self._system_prompt,
                    "messages": [{"role": "user", "content": self._user_message}],
                },
                timeout=60,
            )
        except requests.RequestException as e:
            self.error.emit(f"Request failed: {e}")
            return

        if resp.status_code != 200:
            detail = ""
            try:
                detail = resp.json().get("error", {}).get("message", "")
            except ValueError:
                detail = resp.text[:300]
            self.error.emit(f"API error {resp.status_code}: {detail}")
            return

        try:
            data = resp.json()
            text = "".join(
                block.get("text", "") for block in data.get("content", [])
                if block.get("type") == "text"
            ).strip()
        except ValueError as e:
            self.error.emit(f"Could not parse response: {e}")
            return

        if not text:
            self.error.emit("Empty response from API.")
            return

        self.result_ready.emit(text)
