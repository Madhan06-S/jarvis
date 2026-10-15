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

function resampleBufferTo16k(audioData: Float32Array, originalSampleRate: number): Float32Array {
  if (originalSampleRate === 16000) return audioData;
  const ratio = originalSampleRate / 16000;
  const newLength = Math.round(audioData.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const origIndex = i * ratio;
    const i1 = Math.floor(origIndex);
    const i2 = Math.min(i1 + 1, audioData.length - 1);
    const weight = origIndex - i1;
    result[i] = audioData[i1] * (1 - weight) + audioData[i2] * weight;
  }
  return result;
}

function bufferTo16kWav(buffer: AudioBuffer): { blob: Blob, peakAmp: number, durationSec: number, originalRate: number } {
  const originalRate = buffer.sampleRate;
  const rawChannel = buffer.getChannelData(0);
  const data16k = resampleBufferTo16k(rawChannel, originalRate);

  let peakAmp = 0;
  for (let i = 0; i < data16k.length; i++) {
    const val = Math.abs(data16k[i]);
    if (val > peakAmp) peakAmp = val;
  }
  const durationSec = data16k.length / 16000;

  // Gentle gain boost for soft mic input so Whisper receives clear signal
  const boostGain = (peakAmp > 0.002 && peakAmp < 0.45) ? Math.min(3.5, 0.75 / peakAmp) : 1.0;

  const targetSampleRate = 16000;
  const numOfChan = 1;
  const length = data16k.length * 2 + 44;
  const bufferArr = new ArrayBuffer(length);
  const view = new DataView(bufferArr);
  let pos = 0;

  function writeString(s: string) {
    for (let i = 0; i < s.length; i++) {
      view.setUint8(pos++, s.charCodeAt(i));
    }
  }

  function setUint16(data: number) {
    view.setUint16(pos, data, true);
    pos += 2;
  }

  function setUint32(data: number) {
    view.setUint32(pos, data, true);
    pos += 4;
  }

  // Write standard canonical WAV header (16 kHz, Mono, 16-bit PCM)
  writeString('RIFF');
  setUint32(length - 8);
  writeString('WAVE');
  writeString('fmt ');
  setUint32(16);                               // subchunk1size (16 for PCM)
  setUint16(1);                                // audioFormat (1 = PCM)
  setUint16(numOfChan);                        // numChannels (1)
  setUint32(targetSampleRate);                 // sampleRate (16000)
  setUint32(targetSampleRate * 2 * numOfChan); // byteRate (32000)
  setUint16(numOfChan * 2);                    // blockAlign (2)
  setUint16(16);                               // bitsPerSample (16)
  writeString('data');
  setUint32(data16k.length * 2);

  for (let i = 0; i < data16k.length; i++) {
    let sample = Math.max(-1, Math.min(1, data16k[i] * boostGain));
    sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    view.setInt16(pos, sample, true);
    pos += 2;
  }

  const blob = new Blob([bufferArr], { type: 'audio/wav' });
  return { blob, peakAmp, durationSec, originalRate };
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
  public onDeviceChange: ((deviceName: string) => void) | null = null;

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
      console.log("[Voice VAD] Requesting microphone stream (echoCancellation, noiseSuppression, autoGainControl)...");
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });

      const audioTrack = this.stream.getAudioTracks()[0];
      const deviceLabel = audioTrack ? audioTrack.label : 'Default Microphone';
      console.log(`[Voice VAD] Microphone granted: '${deviceLabel}'`);
      if (this.onDeviceChange) this.onDeviceChange(deviceLabel);

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

        // Update live mic level meter with amplified scale for responsive UI feedback
        const pct = Math.min(100, Math.round(Math.pow(Math.min(1.0, rms * 18.0), 0.65) * 100));
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

        const commitRecordedAudio = () => {
          this.recording = false;
          this.silenceStart = null;
          const chunks = [...this.audioChunks];
          this.audioChunks = [];
          if (chunks.length === 0) {
            if (this.onStateChange) this.onStateChange('idle');
            return;
          }
          if (this.onStateChange) this.onStateChange('transcribing');
          this.processAndSendAudio(chunks);
        };

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
              commitRecordedAudio();
            }
          }
        }

        // Max 10s recording cap guard
        if (this.recording && this.recordStart && (Date.now() - this.recordStart > maxRecordDuration)) {
          console.warn(`[Voice VAD] Maximum recording cap reached (${maxRecordDuration}ms). Forcing audio commit.`);
          commitRecordedAudio();
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

  private async processAndSendAudio(chunks: Float32Array[]) {
    if (!chunks || chunks.length === 0 || !this.audioCtx) {
      if (this.onStateChange) this.onStateChange('idle');
      return;
    }

    const sampleRate = this.audioCtx.sampleRate;
    const merged = mergeBuffers(chunks, sampleRate);
    const { blob, peakAmp, durationSec, originalRate } = bufferTo16kWav(merged);

    console.log(`🎙️ [Live Mic Recording] AudioContext.sampleRate: ${originalRate}Hz | WAV header sampleRate: 16000Hz | Duration: ${durationSec.toFixed(2)}s | Peak Amplitude: ${peakAmp.toFixed(4)} | Encoded Size: ${blob.size} bytes`);
    if (peakAmp < 0.005) {
      console.warn("⚠️ [Live Mic Recording] Peak amplitude is near zero (< 0.005). Check mic volume or hardware mute.");
    }

    const reader = new FileReader();
    reader.readAsDataURL(blob);
    reader.onloadend = () => {
      const resultStr = reader.result as string;
      const base64data = resultStr ? resultStr.split(',')[1] : '';
      if (base64data && this.onAudio) {
        this.onAudio(base64data);
      } else {
        if (this.onStateChange) this.onStateChange('idle');
      }
    };
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
