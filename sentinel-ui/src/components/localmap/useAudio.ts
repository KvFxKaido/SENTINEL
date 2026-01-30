import { useEffect, useRef } from 'react';
import { audioManager, type AtmosphereType, type FloorType } from './audio';

export function useAudio() {
  const initialized = useRef(false);

  // Auto-init on first interaction
  useEffect(() => {
    const handleInteraction = () => {
      if (!initialized.current) {
        audioManager.init();
        audioManager.resume();
        initialized.current = true;
      }
    };

    window.addEventListener('click', handleInteraction);
    window.addEventListener('keydown', handleInteraction);
    
    return () => {
      window.removeEventListener('click', handleInteraction);
      window.removeEventListener('keydown', handleInteraction);
    };
  }, []);

  return {
    setAtmosphere: (type: AtmosphereType) => audioManager.setAtmosphere(type),
    playFootstep: (floor: FloorType = 'default') => audioManager.playFootstep(floor),
    playInteraction: (type: 'hover' | 'select' | 'alert' | 'cancel') => audioManager.playInteraction(type),
    setVolume: (vol: number) => audioManager.setVolume(vol),
    toggleMute: () => audioManager.toggleMute(),
  };
}
