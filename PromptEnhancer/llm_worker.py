from PyQt6.QtCore import QThread, pyqtSignal

from providers import call_llm, LLMError


class PromptWorker(QThread):
    """Calls the selected provider's API in the background to rewrite a rough
    idea into a structured prompt."""
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, provider_id: str, model: str, api_key: str,
                 system_prompt: str, user_message: str):
        super().__init__()
        self._provider_id = provider_id
        self._model = model
        self._api_key = api_key
        self._system_prompt = system_prompt
        self._user_message = user_message

    def run(self):
        try:
            text = call_llm(
                self._provider_id, self._model, self._api_key,
                self._system_prompt, self._user_message,
            )
        except LLMError as e:
            self.error.emit(str(e))
            return
        self.result_ready.emit(text)
