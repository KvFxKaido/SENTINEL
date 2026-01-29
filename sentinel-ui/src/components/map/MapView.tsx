import { useState, useEffect, useCallback } from 'react';
import { WorldMap } from './WorldMap';
import { RegionDetail } from './RegionDetail';
import type { Region, RegionData, RegionConnectivity, ContentMarker } from './types';
import {
  getMapState,
  getRegionDetail,
  proposeTravel,
  commitTravel,
  cancelTravel,
  onMapEvent,
  type MapState,
  type RegionDetailResponse,
  type TravelProposal,
  type TurnResult,
} from '../../lib/bridge';
import './map.css';

/**
 * MapView — Container component for the SENTINEL strategic world map.
 *
 * Orchestrates the turn-based travel pipeline (Sentinel 2D §6):
 *   1. Player clicks a region → fetch detail + propose travel (parallel)
 *   2. RegionDetail renders the engine's ProposalResult
 *   3. Player selects route → confirmation overlay
 *   4. COMMIT → commitTravel() → engine resolves → TurnResult
 *   5. Map refreshes, panel closes, parent receives TurnResult
 *
 * Cancel at any point calls cancelTravel() — zero side effects.
 *
 * @see architecture/Sentinel 2D.md, Section 18 (Integration Architecture)
 */

interface MapViewProps {
  /** Current session number for display */
  session?: number;
  /** Callback when travel resolves with the full TurnResult */
  onTravelComplete?: (turnResult: TurnResult) => void;
}

// Static region data loaded from regions.json via the API — cached across renders
let cachedRegionData: Record<string, RegionData> | null = null;

export function MapView({ session, onTravelComplete }: MapViewProps) {
  // Map state from bridge API
  const [mapState, setMapState] = useState<MapState | null>(null);
  const [regionData, setRegionData] = useState<Record<string, RegionData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected region for detail panel
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [regionDetail, setRegionDetail] = useState<RegionDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Turn-based travel state (replaces old travelPending/travelTarget)
  const [activeProposal, setActiveProposal] = useState<TravelProposal | null>(null);
  const [proposalLoading, setProposalLoading] = useState(false);
  const [resolving, setResolving] = useState(false);

  // Fetch initial map state
  useEffect(() => {
    async function fetchMapState() {
      try {
        setLoading(true);
        const state = await getMapState();
        setMapState(state);

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
          routes: [],
          nexus_presence: 'medium',
          hazards: [],
          points_of_interest: [],
        };
      }
    }

    cachedRegionData = regions;
    setRegionData(regions);
  }

  // Subscribe to map events for live updates
  useEffect(() => {
    const unsubscribe = onMapEvent((event) => {
      console.log('Map event:', event);

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

  // ── Region click: fetch detail + propose travel in parallel ─────────────────
  const handleRegionClick = useCallback(async (regionId: Region) => {
    // Cancel any existing proposal before starting a new one
    if (activeProposal) {
      await cancelTravel().catch(console.error);
    }

    setSelectedRegion(regionId);
    setActiveProposal(null);
    setDetailLoading(true);

    const isTravelTarget = mapState != null && regionId !== mapState.current_region;
    if (isTravelTarget) setProposalLoading(true);

    try {
      // Fetch region detail and propose travel in parallel
      const [detail, proposalResult] = await Promise.all([
        getRegionDetail(regionId),
        isTravelTarget ? proposeTravel(regionId) : null,
      ]);

      setRegionDetail(detail);

      if (proposalResult != null && proposalResult.ok) {
        setActiveProposal(proposalResult.proposal);
      }
    } catch (err) {
      console.error('Failed to load region:', err);
      setRegionDetail(null);
    } finally {
      setDetailLoading(false);
      setProposalLoading(false);
    }
  }, [mapState, activeProposal]);

  // ── Commit travel: crosses the commitment gate ──────────────────────────────
  const handleCommitTravel = useCallback(async (via?: string) => {
    setResolving(true);

    try {
      const result = await commitTravel(via);

      if (result.ok) {
        const turnResult = result.turn_result;

        // Close panel, clear proposal
        setSelectedRegion(null);
        setRegionDetail(null);
        setActiveProposal(null);

        // Notify parent with the full TurnResult
        onTravelComplete?.(turnResult);

        // Refresh map state to reflect new position
        const newState = await getMapState();
        setMapState(newState);
      } else {
        console.error('Travel commit failed:', result.error);
      }
    } catch (err) {
      console.error('Travel commit error:', err);
    } finally {
      setResolving(false);
    }
  }, [onTravelComplete]);

  // ── Cancel travel: zero side effects ────────────────────────────────────────
  const handleCancelTravel = useCallback(() => {
    if (activeProposal) {
      cancelTravel().catch(console.error);
      setActiveProposal(null);
    }
  }, [activeProposal]);

  // ── Close detail panel ──────────────────────────────────────────────────────
  const handleCloseDetail = useCallback(() => {
    setSelectedRegion(null);
    setRegionDetail(null);
    setActiveProposal(null);
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

  const isCurrentRegion = selectedRegion === mapState?.current_region;

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

      {/* Region Detail Panel — driven by engine proposal */}
      {selectedRegion && regionDetail && (
        <RegionDetail
          region={regionDetail.region}
          content={regionDetail.content}
          proposal={activeProposal}
          proposalLoading={proposalLoading}
          isCurrentRegion={isCurrentRegion}
          onCommitTravel={handleCommitTravel}
          onCancelTravel={handleCancelTravel}
          onClose={handleCloseDetail}
          resolving={resolving}
        />
      )}

      {/* Loading overlay for detail fetch */}
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

      {/* Resolving overlay — engine is processing the committed action */}
      {resolving && (
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
              RESOLVING TRAVEL
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
              Engine processing turn...
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MapView;
