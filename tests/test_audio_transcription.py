import pytest
from unittest.mock import MagicMock
from core.speech_transcription import transcribe_audio, TranscriptionInvalidAudio


def test_transcribe_audio_empty_bytes():
    with pytest.raises(TranscriptionInvalidAudio):
        transcribe_audio(b"")


def test_transcribe_audio_format_guessing():
    # Mock MP3 signature bytes (ID3 tag or similar)
    mp3_bytes = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 100
    
    mock_client = MagicMock()
    # Mock the return value of client.audio.transcriptions.create
    mock_client.audio.transcriptions.create.return_value = "transcribed text"
    
    transcribe_audio(mp3_bytes, client=mock_client)
    
    # Verify that the mocked client was called with file_obj named 'audio.mp3'
    args, kwargs = mock_client.audio.transcriptions.create.call_args
    file_obj = kwargs["file"]
    
    assert file_obj.name == "audio.mp3"
