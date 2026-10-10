function mergeBuffers(channelBuffers: Float32Array[], sampleRate: number): AudioBuffer {
  let totalLength = 0;
  for (let i = 0; i < channelBuffers.length; i++) {
    totalLength += channelBuffers[i].length;
  }
  const result = new Float32Array(totalLength);
  let offset = 0;
  for (let i = 0; i < channelBuffers.length; i++) {
    result.set(channelBuffers[i], offset);
    offset += channelBuffers[i].length;
  }
  return {
    numberOfChannels: 1,
    length: totalLength,
    sampleRate: sampleRate,
    getChannelData: () => result
  } as unknown as AudioBuffer;
}

function bufferToWav(buffer: AudioBuffer): Blob {
  const numOfChan = buffer.numberOfChannels;
  const length = buffer.length * numOfChan * 2 + 44;
  const bufferArr = new ArrayBuffer(length);
  const view = new DataView(bufferArr);
  const channels: Float32Array[] = [];
  const sampleRate = buffer.sampleRate;
  let pos = 0;

  function setUint16(data: number) {
    view.setUint16(pos, data, true);
    pos += 2;
  }

  function setUint32(data: number) {
    view.setUint32(pos, data, true);
    pos += 4;
  }

  // Write WAV header
  setUint32(0x46464952); // "RIFF"
  setUint32(length - 8); // file length - 8
  setUint32(0x45564157); // "WAVE"
  setUint32(0x20746d66); // "fmt " chunk
  setUint32(16);         // format chunk length
  setUint16(1);          // sample format (raw PCM)
  setUint16(numOfChan);  // channel count
  setUint32(sampleRate); // sample rate
  setUint32(sampleRate * 2 * numOfChan); // byte rate
  setUint16(numOfChan * 2); // block align
  setUint16(16);         // bits per sample
  setUint32(0x61746164); // "data" chunk
  setUint32(buffer.length * numOfChan * 2); // chunk length

  for (let i = 0; i < numOfChan; i++) {
    channels.push(buffer.getChannelData(i));
  }

  let offset = 0;
  while (pos < length) {
    for (let i = 0; i < numOfChan; i++) {
      let sample = Math.max(-1, Math.min(1, channels[i][offset]));
      sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(pos, sample, true);
      pos += 2;
    }
    offset++;
  }

  return new Blob([bufferArr], { type: 'audio/wav' });
}

export class VoiceInput {
  private stream: MediaStream | null = null;
  private audioCtx: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private audioChunks: Float32Array[] = [];
  private recording = false;
  private silenceStart: number | null = null;
  private recordStart: number | null = null;
  private shouldListen = false;
  public isAwake = false;
  public onWake: (() => void) | null = null;
  public onMicLevel: ((pct: number) => void) | null = null;

  // Adaptive noise calibration
  private calibrationStart: number = 0;
  private calibrationSamples: number[] = [];
  private adaptiveThreshold: number = 0.008;

  constructor(
    private onTranscript: (text: string) => void,
    private onError?: (err: string) => void,
    private onAudio?: (base64Wav: string) => void,
    private onStateChange?: (state: 'idle' | 'listening' | 'transcribing' | 'thinking') => void
  ) {
    this.initAudioRecorder();
  }

  private async initAudioRecorder() {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone access is not supported in this browser environment.");
      }
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });

      const audioTrack = this.stream.getAudioTracks()[0];
      console.log(`[Voice VAD] Microphone granted: '${audioTrack ? audioTrack.label : 'Default Mic'}'`);

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.audioCtx = new AudioContextClass();
      const source = this.audioCtx.createMediaStreamSource(this.stream);
      this.processor = this.audioCtx.createScriptProcessor(4096, 1, 1);

      this.calibrationStart = Date.now();
      this.calibrationSamples = [];

      const silenceDuration = 1100;   // ms of silence before committing audio
      const maxRecordDuration = 10000; // max 10s recording cap

      this.processor.onaudioprocess = (e) => {
        if (!this.shouldListen) return;
        const inputData = e.inputBuffer.getChannelData(0);

        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);

        // Update live mic level meter
        const pct = Math.min(100, Math.round(rms * 1200));
        if (this.onMicLevel) this.onMicLevel(pct);

        // Calibrate ambient noise floor during first 1.0 second
        if (Date.now() - this.calibrationStart < 1000) {
          this.calibrationSamples.push(rms);
          if (this.calibrationSamples.length > 5) {
            const avgNoise = this.calibrationSamples.reduce((a, b) => a + b, 0) / this.calibrationSamples.length;
            this.adaptiveThreshold = Math.max(0.006, avgNoise * 2.5);
          }
          return;
        }

        const effectiveThreshold = this.adaptiveThreshold;

        // VAD Logic
        if (rms > effectiveThreshold) {
          if (!this.recording) {
            this.recording = true;
            this.recordStart = Date.now();
            this.audioChunks = [];
            this.silenceStart = null;
            console.log(`[Voice VAD] Speech START detected (RMS: ${rms.toFixed(4)}, Threshold: ${effectiveThreshold.toFixed(4)})`);
            if (this.onStateChange) this.onStateChange('listening');
            if (this.onWake && !this.isAwake) {
              this.isAwake = true;
              this.onWake();
            }
          }
          this.silenceStart = null;
        } else {
          if (this.recording) {
            if (!this.silenceStart) {
              this.silenceStart = Date.now();
            } else if (Date.now() - this.silenceStart > silenceDuration) {
              console.log(`[Voice VAD] Speech END detected after silence (${silenceDuration}ms).`);
              this.recording = false;
              this.silenceStart = null;
              if (this.onStateChange) this.onStateChange('transcribing');
              this.processAndSendAudio();
            }
          }
        }

        // Max 10s recording cap guard
        if (this.recording && this.recordStart && (Date.now() - this.recordStart > maxRecordDuration)) {
          console.warn(`[Voice VAD] Maximum recording cap reached (${maxRecordDuration}ms). Forcing audio commit.`);
          this.recording = false;
          this.silenceStart = null;
          if (this.onStateChange) this.onStateChange('transcribing');
          this.processAndSendAudio();
        }

        if (this.recording) {
          this.audioChunks.push(new Float32Array(inputData));
        }
      };

      source.connect(this.processor);
      this.processor.connect(this.audioCtx.destination);
    } catch (err: any) {
      console.error("[Voice VAD] Microphone init failed:", err);
      let errMsg = err.message || String(err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errMsg = "MICROPHONE ACCESS DENIED. Click the camera/microphone icon in your address bar to grant access.";
      }
      if (this.onError) this.onError(errMsg);
    }
  }

  private async processAndSendAudio() {
    if (this.audioChunks.length === 0 || !this.audioCtx) return;

    const sampleRate = this.audioCtx.sampleRate;
    const merged = mergeBuffers(this.audioChunks, sampleRate);
    const wavBlob = bufferToWav(merged);

    console.log(`[Voice VAD] Encoded audio chunk: ${wavBlob.size} bytes (${sampleRate}Hz)`);

    const reader = new FileReader();
    reader.readAsDataURL(wavBlob);
    reader.onloadend = () => {
      const base64data = (reader.result as string).split(',')[1];
      if (this.onAudio) {
        this.onAudio(base64data);
      }
    };

    this.audioChunks = [];
  }

  resetWakeState() {
    this.isAwake = false;
  }

  start() {
    this.shouldListen = true;
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  pause() {
    this.shouldListen = false;
    this.recording = false;
    this.audioChunks = [];
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
