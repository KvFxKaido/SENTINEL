/**
 * LocalMapPage — Client-side wrapper for Astro's client:only directive.
 *
 * Reads URL params and renders LocalMapView with the correct props.
 * This exists because Astro needs a single React component to hydrate
 * via client:only="react", which properly installs the React Refresh
 * preamble before any .tsx modules are evaluated.
 */

import { Component, useCallback, type ErrorInfo, type ReactNode } from 'react';
import { LocalMapView } from './LocalMapView';

class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null; info: string }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: null, info: '' };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ info: errorInfo?.componentStack || '' });
    console.error('[LocalMap ErrorBoundary]', error, errorInfo);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          color: '#f85149',
          background: '#0a0a0f',
          padding: '2rem',
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap' as const,
          overflow: 'auto',
          maxHeight: '100vh',
        }}>
          <h2 style={{ color: '#58a6ff' }}>LocalMap Render Error</h2>
          <p>{String(this.state.error)}</p>
          <pre style={{ fontSize: '0.75rem', color: '#8b949e', marginTop: '1rem' }}>
            {this.state.info}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function LocalMapPage() {
  const params = new URLSearchParams(window.location.search);
  const mapId = params.get('map') || 'safehouse_main';
  const spawnId = params.get('spawn') || undefined;

  const handleMapChange = useCallback((newMapId: string) => {
    const newParams = new URLSearchParams(window.location.search);
    newParams.set('map', newMapId);
    window.history.replaceState({}, '', `?${newParams.toString()}`);
  }, []);

  const handleInteraction = useCallback((type: string, target: unknown) => {
    console.log('Interaction:', type, target);
  }, []);

  const handleExit = useCallback(() => {
    window.location.href = '/';
  }, []);

  return (
    <ErrorBoundary>
      <LocalMapView
        initialMapId={mapId}
        initialSpawnId={spawnId}
        onMapChange={handleMapChange}
        onInteraction={handleInteraction}
        onExit={handleExit}
      />
    </ErrorBoundary>
  );
}
