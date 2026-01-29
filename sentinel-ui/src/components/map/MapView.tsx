import { useState, useEffect, useCallback } from 'react';
import { WorldMap } from './WorldMap';
import { RegionDetail } from './RegionDetail';
import type { Region, RegionData, RegionConnectivity, ContentMarker } from './types';
import {
  getMapState,
  getRegionDetail,
  travel,
  onMapEvent,
  type MapState,
  type RegionDetailResponse,
} from '../../lib/bridge';
import './map.css';

/**
 * MapView — Container component for the SENTINEL strategic world map.
 *
 * Handles:
 * - Fetching map state from the bridge API
 * - Region selection and detail panel
 * - Travel confirmation flow (commitment gate)
 * - SSE event subscription for live updates
 *
 * @see architecture/Sentinel 2D.md, Section 18 (Integration Architecture)
 */

interface MapViewProps {
  /** Current session number for display */
  session?: number;
  /** Callback when travel is initiated (for narrative log integration) */
  onTravelInitiated?: (from: string, to: string) => void;
}

// Static region data loaded from regions.json via the API
// This will be populated on first load
let cachedRegionData: Record<string, RegionData> | null = null;

export function MapView({ session, onTravelInitiated }: MapViewProps) {
  // Map state from bridge API
  const [mapState, setMapState] = useState<MapState | null>(null);
  const [regionData, setRegionData] = useState<Record<string, RegionData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected region for detail panel
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [regionDetail, setRegionDetail] = useState<RegionDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Travel confirmation state
  const [travelPending, setTravelPending] = useState(false);
  const [travelTarget, setTravelTarget] = useState<{ regionId: string; via?: string } | null>(null);

  // Fetch initial map state
  useEffect(() => {
    async function fetchMapState() {
      try {
        setLoading(true);
        const state = await getMapState();
        setMapState(state);

        // If we don't have region data yet, fetch it from the first region detail
        // In a full implementation, this would come from a dedicated endpoint
        if (!cachedRegionData) {
          await loadRegionData(state);
        } else {
          setRegionData(cachedRegionData);
        }

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load map');
      } finally {
        setLoading(false);
      }
    }

    fetchMapState();
  }, []);

  // Load static region data by fetching details for each region
  async function loadRegionData(state: MapState) {
    const regions: Record<string, RegionData> = {};
    const regionIds = Object.keys(state.regions);

    // Fetch region details in parallel (limited concurrency)
    const results = await Promise.allSettled(
      regionIds.map(async (id) => {
        try {
          const detail = await getRegionDetail(id);
          if (detail.ok) {
            return { id, data: detail.region };
          }
        } catch {
          // Ignore individual failures
        }
        return null;
      })
    );

    for (const result of results) {
      if (result.status === 'fulfilled' && result.value) {
        const { id, data } = result.value;
        regions[id] = {
          id: id as Region,
          name: data.name,
          description: data.description,
          primary_faction: data.primary_faction as any,
          contested_by: data.contested_by as any[],
          terrain: data.terrain,
          character: data.character,
          position: data.position,
          routes: [], // Routes are fetched per-region when needed
          nexus_presence: 'medium', // Default
          hazards: [],
          points_of_interest: [],
        };
      }
    }

    cachedRegionData = regions;
    setRegionData(regions);
  }

  // Subscribe to map events
  useEffect(() => {
    const unsubscribe = onMapEvent((event) => {
      console.log('Map event:', event);

      // Refresh map state on relevant events
      if (
        event.event_type === 'map.region_changed' ||
        event.event_type === 'map.connectivity_updated' ||
        event.event_type === 'map.marker_changed'
      ) {
        getMapState().then(setMapState).catch(console.error);
      }
    });

    return unsubscribe;
  }, []);

  // Handle region click
  const handleRegionClick = useCallback(async (regionId: Region) => {
    setSelectedRegion(regionId);
    setDetailLoading(true);

    try {
      const detail = await getRegionDetail(regionId);
      setRegionDetail(detail);
    } catch (err) {
      console.error('Failed to fetch region detail:', err);
      setRegionDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Handle travel request
  const handleTravel = useCallback(async (regionId: string, via?: string) => {
    setTravelPending(true);
    setTravelTarget({ regionId, via });

    try {
      const result = await travel(regionId, via);

      if (result.ok) {
        // Travel successful - close detail panel and refresh
        setSelectedRegion(null);
        setRegionDetail(null);
        onTravelInitiated?.(mapState?.current_region || '', regionId);

        // Refresh map state
        const newState = await getMapState();
        setMapState(newState);
      } else {
        // Travel failed - show error
        console.error('Travel failed:', result.error);
        alert(`Travel failed: ${result.error}`);
      }
    } catch (err) {
      console.error('Travel error:', err);
      alert(`Travel error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setTravelPending(false);
      setTravelTarget(null);
    }
  }, [mapState, onTravelInitiated]);

  // Close detail panel
  const handleCloseDetail = useCallback(() => {
    setSelectedRegion(null);
    setRegionDetail(null);
  }, []);

  // Build region states and markers from map state
  const regionStates: Record<string, RegionConnectivity> = {};
  const markers: Record<string, ContentMarker[]> = {};

  if (mapState) {
    for (const [id, state] of Object.entries(mapState.regions)) {
      regionStates[id] = state.connectivity;
      markers[id] = state.markers;
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="map-view-loading" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: '8px' }}>LOADING MAP DATA...</div>
          <div style={{ fontSize: '12px', color: 'var(--accent-steel)' }}>
            Establishing connection to SENTINEL network
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="map-view-error" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--status-danger)',
        fontFamily: 'var(--font-mono)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: '8px' }}>MAP UNAVAILABLE</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="map-view" style={{ position: 'relative', width: '100%', height: '100%' }}>
      <WorldMap
        regions={regionData}
        currentRegion={mapState?.current_region as Region || 'rust_corridor'}
        regionStates={regionStates}
        markers={markers}
        onRegionClick={handleRegionClick}
        showLegend={true}
        session={session}
      />

      {/* Region Detail Panel */}
      {selectedRegion && regionDetail && (
        <RegionDetail
          region={regionDetail.region}
          routes={regionDetail.routes_from_current}
          content={regionDetail.content}
          onTravel={handleTravel}
          onClose={handleCloseDetail}
        />
      )}

      {/* Loading overlay for detail */}
      {detailLoading && (
        <div style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-primary)',
          borderRadius: '8px',
          padding: '16px 24px',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
        }}>
          LOADING REGION DATA...
        </div>
      )}

      {/* Travel pending overlay */}
      {travelPending && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
        }}>
          <div style={{
            background: 'var(--bg-panel)',
            border: '1px solid var(--accent-steel)',
            borderRadius: '8px',
            padding: '24px 32px',
            textAlign: 'center',
            fontFamily: 'var(--font-mono)',
          }}>
            <div style={{ color: 'var(--accent-cyan)', marginBottom: '8px', fontSize: '14px' }}>
              INITIATING TRAVEL
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Destination: {travelTarget?.regionId.replace(/_/g, ' ').toUpperCase()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MapView;
