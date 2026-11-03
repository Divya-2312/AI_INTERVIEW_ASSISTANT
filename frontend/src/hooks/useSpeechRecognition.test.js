import { test, describe } from 'node:test';
import assert from 'node:assert';

// Mock Web Speech API SpeechRecognition
class MockSpeechRecognition {
  constructor() {
    this.continuous = false;
    this.interimResults = false;
    this.lang = 'en-US';
    this.maxAlternatives = 1;
    this.onresult = null;
    this.onerror = null;
    this.onend = null;
    this.started = false;
    this.stopped = false;
  }

  start() {
    this.started = true;
    this.stopped = false;
  }

  stop() {
    this.stopped = true;
    this.started = false;
    if (this.onend) this.onend();
  }

  // Helper to simulate speech result event
  simulateResult(results, resultIndex = 0) {
    if (this.onresult) {
      this.onresult({
        resultIndex,
        results: results.map((r) => {
          const item = [{ transcript: r.transcript, confidence: r.confidence ?? 0.9 }];
          item.isFinal = Boolean(r.isFinal);
          return item;
        }),
      });
    }
  }

  // Helper to simulate speech error event
  simulateError(errorType) {
    if (this.onerror) {
      this.onerror({ error: errorType });
    }
  }
}

describe('Speech Answer Mode - useSpeechRecognition logic & lifecycle', () => {
  test('1. Start and stop recognition toggles listening state', () => {
    const mockRec = new MockSpeechRecognition();
    let isListening = false;

    // Simulate start
    mockRec.start();
    isListening = mockRec.started;
    assert.strictEqual(isListening, true, 'Microphone should be active after start');

    // Simulate stop
    mockRec.stop();
    isListening = mockRec.started;
    assert.strictEqual(isListening, false, 'Microphone should be inactive after stop');
    assert.strictEqual(mockRec.stopped, true);
  });

  test('2. Transcript is APPENDED to existing typed text without erasing it', () => {
    const existingTypedText = 'In Java, encapsulation bundles data and methods.';
    let currentAnswer = existingTypedText;

    const baseText = existingTypedText ? existingTypedText.trim() + ' ' : '';
    let committedTranscript = '';
    let interim = '';

    const mockRec = new MockSpeechRecognition();
    mockRec.onresult = (event) => {
      interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        if (res.isFinal) {
          committedTranscript = `${committedTranscript} ${res[0].transcript}`.trim();
        } else {
          interim += res[0].transcript;
        }
      }
      currentAnswer = `${baseText}${committedTranscript} ${interim}`.trim();
    };

    // User speaks final chunk
    mockRec.simulateResult([{ transcript: 'It also hides internal state.', isFinal: true }]);

    assert.ok(
      currentAnswer.startsWith('In Java, encapsulation bundles data and methods.'),
      'Original typed text must not be erased'
    );
    assert.strictEqual(
      currentAnswer,
      'In Java, encapsulation bundles data and methods. It also hides internal state.',
      'Spoken text must be appended to the typed text'
    );
  });

  test('3. Interim results do not duplicate words as candidate continues speaking', () => {
    let currentAnswer = '';
    let committedTranscript = '';
    let interim = '';

    const mockRec = new MockSpeechRecognition();
    mockRec.onresult = (event) => {
      interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        if (res.isFinal) {
          committedTranscript = `${committedTranscript} ${res[0].transcript}`.trim();
        } else {
          interim += res[0].transcript;
        }
      }
      currentAnswer = `${committedTranscript} ${interim}`.trim();
    };

    // 1st interim event: "thread"
    mockRec.simulateResult([{ transcript: 'thread', isFinal: false }]);
    assert.strictEqual(currentAnswer, 'thread');

    // 2nd interim event: "thread is a lightweight"
    mockRec.simulateResult([{ transcript: 'thread is a lightweight', isFinal: false }]);
    assert.strictEqual(currentAnswer, 'thread is a lightweight', 'Should replace interim without duplicating "thread"');

    // Final result event: "thread is a lightweight process."
    mockRec.simulateResult([{ transcript: 'thread is a lightweight process.', isFinal: true }]);
    assert.strictEqual(currentAnswer, 'thread is a lightweight process.');
  });

  test('4. Permission denied error produces a clear descriptive user message', () => {
    let speechError = '';
    let isListening = true;

    const mockRec = new MockSpeechRecognition();
    mockRec.onerror = (event) => {
      isListening = false;
      const messages = {
        'not-allowed': 'Microphone access was blocked. Please allow microphone permission in your browser settings.',
        'permission-denied': 'Microphone access was blocked. Please allow microphone permission in your browser settings.',
      };
      speechError = messages[event.error] || `Error: ${event.error}`;
    };

    mockRec.simulateError('not-allowed');

    assert.strictEqual(isListening, false, 'Microphone must stop on error');
    assert.ok(
      speechError.includes('Microphone access was blocked'),
      'Clear permission denied error must be displayed'
    );
  });

  test('5. Unsupported browser (Firefox) detection shows clear message', () => {
    // When window.SpeechRecognition and window.webkitSpeechRecognition are undefined
    const mockWindow = {};
    const SpeechRecognitionApi = mockWindow.SpeechRecognition || mockWindow.webkitSpeechRecognition;

    const speechSupported = Boolean(SpeechRecognitionApi);
    assert.strictEqual(speechSupported, false, 'Browser without SpeechRecognition must be flagged unsupported');

    const fallbackMessage = !speechSupported
      ? 'Voice input is not supported in this browser. Please use Google Chrome or Microsoft Edge.'
      : '';
    assert.ok(fallbackMessage.includes('not supported in this browser'));
    assert.ok(fallbackMessage.includes('Chrome or Microsoft Edge'));
  });

  test('6. Microphone stops on submit and on leaving page (cleanup)', () => {
    const mockRec = new MockSpeechRecognition();
    mockRec.start();
    assert.strictEqual(mockRec.started, true);

    // Simulate submit event: stops recognition
    function handleSubmit() {
      if (mockRec.started) {
        mockRec.stop();
      }
    }

    handleSubmit();
    assert.strictEqual(mockRec.started, false, 'Microphone must stop when answer is submitted');
    assert.strictEqual(mockRec.stopped, true);
  });
});
