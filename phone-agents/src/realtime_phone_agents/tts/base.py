from abc import ABC, abstractmethod
from typing import Generator

import numpy as np
from numpy.typing import NDArray


class TTSModel(ABC):
    """
    Abstract base class for Text-to-Speech models.

    All STT model implementations must inherit from this class
    and implement the `tts` and the `stream_tts` methods.
    """

    @abstractmethod
    def tts(self, text: str, **kwargs) -> tuple[int, NDArray[np.int16]]:
        """
        Convert text to speech audio.

        Args:
            text: Text to convert to speech
            **kwargs: Additional model-specific parameters

        Returns:
            bytes: Audio data as bytes

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass

    @abstractmethod
    def stream_tts(
        self, text: str, **kwargs
    ) -> Generator[tuple[int, NDArray[np.int16]], None, None]:
        """
        Stream audio from the model.

        Args:
            text: Text to convert to speech
            **kwargs: Additional model-specific parameters

        Returns:
            Generator[tuple[int, NDArray[np.int16]], None, None]: Generator of (sample_rate, chunk) pairs
        """
        pass
