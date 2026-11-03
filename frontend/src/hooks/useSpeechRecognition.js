import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Custom hook for browser speech recognition (Speech Answer Mode).
 * 
 * Features:
 * - Language selection (e.g. en-IN, en-US, en-GB, en-AU)
 * - Start / Stop toggle
 * - Appends spoken words to existing typed text without erasing it
 * - Avoids word duplication for interim / continuous results
 * - Stops microphone on submit, on leaving page / unmount, and on error
 * - Clear error messages for blocked microphone / permission denied
 * - Graceful fallback message for unsupported browsers (e.g. Firefox)
 */
export function useSpeechRecognition({
  speechLang = 'en-IN',
  onTranscriptChange,
  isLocked = false,
  onSpeechSegmentsUpdate,
} = {}) {
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [speechError, setSpeechError] = useState('');

  const recognitionRef = useRef(null);
  const baseTextRef = useRef('');
  const committedTranscriptRef = useRef('');
  const languageRejectedRef = useRef(false);

  useEffect(() => {
    const SpeechRecognitionApi =
      typeof window !== 'undefined' &&
      (window.SpeechRecognition || window.webkitSpeechRecognition);

    if (!SpeechRecognitionApi) {
      setSpeechSupported(false);
      return;
    }

    setSpeechSupported(true);
    let recognition;
    try {
      recognition = new SpeechRecognitionApi();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = speechLang;
      recognition.maxAlternatives = 1;
    } catch (e) {
      setSpeechSupported(false);
      return;
    }

    recognition.onresult = (event) => {
      if (isLocked) return;
      let interim = '';
      let sawUnrecognizable = false;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const alt = result[0];
        const text = alt.transcript || '';
        const confidence = typeof alt.confidence === 'number' ? alt.confidence : 1;

        if (result.isFinal) {
          const NON_LATIN = /[^\u0000-\u007F\s.,!?'"()-]/;
          if (
            NON_LATIN.test(text) ||
            (confidence > 0 && confidence < 0.4)
          ) {
            sawUnrecognizable = true;
            continue;
          }
          const cleaned = text.replace(/[.!?]+$/, '').trim();
          if (onSpeechSegmentsUpdate && cleaned) {
            onSpeechSegmentsUpdate(cleaned, Date.now());
          }
          committedTranscriptRef.current = `${committedTranscriptRef.current} ${cleaned}`.trim();
        } else {
          interim += text;
        }
      }

      if (sawUnrecognizable) {
        languageRejectedRef.current = true;
        setSpeechError("Couldn't understand the language. Please speak in English.");
      } else if ((interim || committedTranscriptRef.current) && !languageRejectedRef.current) {
        setSpeechError('');
      }

      const speechCombined = `${committedTranscriptRef.current} ${interim}`.trim();
      const combined = `${baseTextRef.current}${speechCombined}`.trim();
      if (onTranscriptChange && (combined || sawUnrecognizable)) {
        onTranscriptChange(combined);
      }
    };

    recognition.onerror = (event) => {
      setIsListening(false);
      const messages = {
        'no-speech': "I didn't hear anything. Please try again.",
        'audio-capture': 'No microphone was found. Please check your device.',
        'not-allowed': 'Microphone access was blocked. Please allow microphone permission in your browser settings.',
        'permission-denied': 'Microphone access was blocked. Please allow microphone permission in your browser settings.',
        'language-not-supported': 'English speech recognition is not available on this device.',
        network: 'A network error interrupted speech recognition. Please try again.',
      };
      setSpeechError(messages[event.error] || `Speech recognition error: ${event.error}. Please try again.`);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.stop();
      } catch (e) {}
    };
  }, [speechLang, isLocked, onTranscriptChange, onSpeechSegmentsUpdate]);

  const startListening = useCallback((currentText = '') => {
    if (!speechSupported) {
      setSpeechError('Voice input is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
      return;
    }
    if (!recognitionRef.current || isLocked) return;
    baseTextRef.current = currentText ? currentText.trim() + ' ' : '';
    committedTranscriptRef.current = '';
    languageRejectedRef.current = false;
    setSpeechError('');
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e) {
      console.error('Recognition start error', e);
    }
  }, [isLocked, speechSupported]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
  }, []);

  const toggleListening = useCallback((currentText = '') => {
    if (isListening) {
      stopListening();
    } else {
      startListening(currentText);
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    speechSupported,
    speechError,
    startListening,
    stopListening,
    toggleListening,
  };
}
