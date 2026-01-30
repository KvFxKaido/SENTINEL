/**
 * Procedural Audio System for SENTINEL 2D
 * 
 * Generates all sound effects and ambience using Web Audio API.
 * No external audio files are used.
 * 
 * Design Philosophy:
 * - Restrained, atmospheric, and functional.
 * - Sounds should blend into the background.
 * - Procedural generation ensures variety and infinite length.
 */

export type AtmosphereType = 'safe' | 'neutral' | 'tense' | 'hostile';
export type FloorType = 'default' | 'metal' | 'water' | 'debris';

class AudioManager {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private ambientGain: GainNode | null = null;
  private sfxGain: GainNode | null = null;
  
  // Ambient oscillators
  private ambientOscillators: OscillatorNode[] = [];
  private ambientNodes: AudioNode[] = []; // Store filters/gains for cleanup
  private currentAtmosphere: AtmosphereType = 'neutral';
  
  private isMuted: boolean = false;
  private volume: number = 0.5;
  private initialized: boolean = false;

  constructor() {
    // Lazy initialization to respect browser autoplay policies
  }

  public init() {
    if (this.initialized) return;
    
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      this.ctx = new AudioContextClass();
      
      this.masterGain = this.ctx.createGain();
      this.masterGain.gain.value = this.volume;
      this.masterGain.connect(this.ctx.destination);
      
      this.ambientGain = this.ctx.createGain();
      this.ambientGain.gain.value = 0.4; // Base ambient level
      this.ambientGain.connect(this.masterGain);
      
      this.sfxGain = this.ctx.createGain();
      this.sfxGain.gain.value = 0.6; // Base SFX level
      this.sfxGain.connect(this.masterGain);
      
      this.initialized = true;
      this.setAtmosphere('neutral');
    } catch (e) {
      console.warn('Audio initialization failed:', e);
    }
  }

  public async resume() {
    if (this.ctx && this.ctx.state === 'suspended') {
      await this.ctx.resume();
    }
  }

  public setVolume(val: number) {
    this.volume = Math.max(0, Math.min(1, val));
    if (this.masterGain) {
      this.masterGain.gain.setValueAtTime(this.isMuted ? 0 : this.volume, this.ctx!.currentTime);
    }
  }

  public toggleMute() {
    this.isMuted = !this.isMuted;
    this.setVolume(this.volume);
  }

  public setAtmosphere(type: AtmosphereType) {
    if (!this.initialized || this.currentAtmosphere === type) return;
    
    // Crossfade: Ramp down current, wait, ramp up new
    // For simplicity in this v1, we just stop and start new
    this.stopAmbience();
    this.currentAtmosphere = type;
    this.startAmbience(type);
  }

  private stopAmbience() {
    this.ambientOscillators.forEach(osc => {
      try { osc.stop(); } catch (e) {}
    });
    this.ambientNodes.forEach(node => {
      try { node.disconnect(); } catch (e) {}
    });
    this.ambientOscillators = [];
    this.ambientNodes = [];
  }

  private startAmbience(type: AtmosphereType) {
    if (!this.ctx || !this.ambientGain) return;
    const now = this.ctx.currentTime;

    // Create noise buffer for wind/texture
    const bufferSize = this.ctx.sampleRate * 2; // 2 seconds
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const createDrone = (freq: number, type: OscillatorType, gain: number, lfoFreq: number = 0.1) => {
      if (!this.ctx || !this.ambientGain) return;
      
      const osc = this.ctx.createOscillator();
      const oscGain = this.ctx.createGain();
      const lfo = this.ctx.createOscillator();
      const lfoGain = this.ctx.createGain();
      
      osc.type = type;
      osc.frequency.value = freq;
      
      lfo.frequency.value = lfoFreq;
      lfoGain.gain.value = gain * 0.3; // AM depth
      
      // Signal chain: LFO -> LFO Gain -> Osc Gain -> Ambient Gain
      lfo.connect(lfoGain);
      lfoGain.connect(oscGain.gain);
      osc.connect(oscGain);
      oscGain.connect(this.ambientGain);
      
      oscGain.gain.value = gain;
      
      osc.start(now);
      lfo.start(now);
      
      this.ambientOscillators.push(osc, lfo);
      this.ambientNodes.push(oscGain, lfoGain);
    };

    const createNoise = (filterFreq: number, gain: number) => {
      if (!this.ctx || !this.ambientGain) return;
      
      const noise = this.ctx.createBufferSource();
      noise.buffer = buffer;
      noise.loop = true;
      
      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.value = filterFreq;
      
      const noiseGain = this.ctx.createGain();
      noiseGain.gain.value = gain;
      
      noise.connect(filter);
      filter.connect(noiseGain);
      noiseGain.connect(this.ambientGain);
      
      noise.start(now);
      
      this.ambientNodes.push(noise, filter, noiseGain);
    };

    // Atmosphere recipes
    switch (type) {
      case 'safe':
        createDrone(110, 'sine', 0.05, 0.05); // Low A
        createDrone(164.8, 'sine', 0.03, 0.07); // E
        createNoise(400, 0.02); // Warm hiss
        break;
      
      case 'neutral':
        createDrone(60, 'triangle', 0.03, 0.1); // Low drone
        createNoise(800, 0.04); // Air conditioning / wind
        break;
        
      case 'tense':
        createDrone(55, 'sawtooth', 0.02, 2.0); // Throbbing low A
        createDrone(58, 'sine', 0.03, 0.5); // Dissonant Bb beat
        createNoise(200, 0.05); // Low rumble
        break;
        
      case 'hostile':
        createDrone(40, 'sawtooth', 0.05, 4.0); // Aggressive low rumble
        createDrone(4000, 'sine', 0.01, 0.2); // High anxiety whine
        createNoise(1500, 0.08); // Harsher noise
        break;
    }
  }

  // ==========================================================================
  // SFX
  // ==========================================================================

  public playFootstep(floor: FloorType = 'default') {
    if (!this.ctx || !this.sfxGain) return;
    const now = this.ctx.currentTime;
    
    // Noise burst
    const bufferSize = this.ctx.sampleRate * 0.1;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    
    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;
    
    const filter = this.ctx.createBiquadFilter();
    const gain = this.ctx.createGain();
    
    // Floor characteristics
    switch (floor) {
      case 'metal':
        filter.type = 'highpass';
        filter.frequency.value = 1000;
        filter.Q.value = 10; // Metallic resonance
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
        break;
        
      case 'water':
        filter.type = 'lowpass';
        filter.frequency.value = 400;
        filter.Q.value = 1;
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.15);
        break;

      case 'debris':
        filter.type = 'bandpass';
        filter.frequency.value = 800;
        filter.Q.value = 0.5; // Crunchy
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);
        break;
        
      default: // Concrete/Floor
        filter.type = 'lowpass';
        filter.frequency.value = 600;
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);
    }
    
    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.sfxGain);
    
    noise.start(now);
  }

  public playInteraction(type: 'hover' | 'select' | 'alert' | 'cancel') {
    if (!this.ctx || !this.sfxGain) return;
    const now = this.ctx.currentTime;
    
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    
    osc.connect(gain);
    gain.connect(this.sfxGain);
    
    switch (type) {
      case 'hover':
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.05);
        gain.gain.setValueAtTime(0.02, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.05);
        osc.start(now);
        osc.stop(now + 0.05);
        break;
        
      case 'select':
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(440, now + 0.1);
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
        osc.start(now);
        osc.stop(now + 0.1);
        break;
        
      case 'alert':
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.linearRampToValueAtTime(110, now + 0.3);
        gain.gain.setValueAtTime(0.1, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
        osc.start(now);
        osc.stop(now + 0.3);
        break;

      case 'cancel':
        osc.type = 'square';
        osc.frequency.setValueAtTime(150, now);
        gain.gain.setValueAtTime(0.05, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
        osc.start(now);
        osc.stop(now + 0.1);
        break;
    }
  }

  public cleanup() {
    this.stopAmbience();
    if (this.ctx) {
      this.ctx.close();
      this.ctx = null;
    }
    this.initialized = false;
  }
}

export const audioManager = new AudioManager();
