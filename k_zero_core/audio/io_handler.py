from typing import Optional

class IOHandler:
    def __init__(self, input_type: str, output_type: str, stt=None, tts=None):
        """
        input_type: 'text' or 'audio'
        output_type: 'text' or 'audio'
        """
        self.input_type = input_type
        self.output_type = output_type
        self.stt = stt
        self.tts = tts

    def get_user_input(self) -> str:
        """Obtiene la entrada del usuario dependiendo de si es texto o audio."""
        if self.input_type == 'audio' and self.stt:
            return self.stt.listen_and_transcribe()
        else:
            return input("Tú: ")

    def output_response(self, text: str) -> None:
        """Ejecuta el TTS si el modo de salida es audio."""
        if self.output_type == 'audio' and self.tts and text.strip():
            print("Hablando...")
            self.tts.speak(text, voice=self.tts.default_voice)
