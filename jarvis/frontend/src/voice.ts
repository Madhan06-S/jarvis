export class VoiceInput {
  private recognition: any;
  private shouldListen = false;
  private isListeningStr = false;
  
  constructor(private onTranscript: (text: string) => void) {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = "en-US";
      
      let transcriptBuffer = "";
      let debounceTimer: any = null;

      this.recognition.onresult = (event: any) => {
        let finalTrans = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTrans += " " + event.results[i][0].transcript;
          }
        }
        
        if (finalTrans.trim()) {
          transcriptBuffer += finalTrans;
          if (debounceTimer) clearTimeout(debounceTimer);
          debounceTimer = setTimeout(() => {
            if (transcriptBuffer.trim()) {
              this.onTranscript(transcriptBuffer.trim());
              transcriptBuffer = "";
            }
          }, 800);
        }
      };
      
      this.recognition.onstart = () => { this.isListeningStr = true; };
      this.recognition.onend = () => {
        this.isListeningStr = false;
        if (this.shouldListen) {
          try { this.recognition.start(); } catch (e) {}
        }
      };
      this.recognition.onerror = (e: any) => {
        if (e.error === 'not-allowed') {
            console.error("Microphone blocked. Please grant permission.");
        } else if (e.error !== 'no-speech') {
            console.warn("Speech API Error:", e.error);
        }
      };
    }
  }

  start() {
    this.shouldListen = true;
    if (!this.isListeningStr && this.recognition) {
      try { this.recognition.start(); } catch (e) {}
    }
  }

  pause() {
    this.shouldListen = false;
    if (this.isListeningStr && this.recognition) {
      this.recognition.abort(); // IMPORTANT: use abort to discard buffered audio to prevent echo
    }
  }
}

export class AudioPlayer {
  private ctx: AudioContext;
  private analyser: AnalyserNode;
  private queue: AudioBuffer[] = [];
  private isPlaying = false;
  private source: AudioBufferSourceNode | null = null;
  private finishedCallback: (() => void) | null = null;

  constructor() {
    this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.8;
    this.analyser.connect(this.ctx.destination);
  }

  getAnalyser() {
    return this.analyser;
  }

  onFinished(cb: () => void) {
    this.finishedCallback = cb;
  }

  async enqueue(base64: string) {
    const binary = atob(base64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    const buffer = bytes.buffer;
    const audioBuf = await this.ctx.decodeAudioData(buffer);
    this.queue.push(audioBuf);
    if (!this.isPlaying) {
      this.playNext();
    }
  }

  private playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      if (this.finishedCallback) this.finishedCallback();
      return;
    }
    this.isPlaying = true;
    const buf = this.queue.shift()!;
    this.source = this.ctx.createBufferSource();
    this.source.buffer = buf;
    this.source.connect(this.analyser);
    this.source.onended = () => {
      this.playNext();
    };
    this.source.start(0);
  }

  isIdle(): boolean {
    return !this.isPlaying && this.queue.length === 0;
  }

  stop() {
    this.queue = [];
    if (this.source) {
      this.source.onended = null;
      try { this.source.stop(); } catch (e) {}
      this.source = null;
    }
    this.isPlaying = false;
  }

  ensureUnlocked() {
    if (this.ctx.state === "suspended") {
      const unlock = () => {
        this.ctx.resume();
        document.removeEventListener("click", unlock);
        document.removeEventListener("keydown", unlock);
      };
      document.addEventListener("click", unlock);
      document.addEventListener("keydown", unlock);
    }
  }
}
