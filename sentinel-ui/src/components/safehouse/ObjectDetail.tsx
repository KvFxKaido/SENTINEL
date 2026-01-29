/**
 * ObjectDetail — Detail panel for inspecting safehouse objects
 * 
 * Shows detailed information about gear, vehicles, threads, and enhancements.
 * This is where the player quietly accounts for what they still have.
 */

import type {
  PlacedObject,
  GearItem,
  Vehicle,
  DormantThread,
  Enhancement,
  SafehouseState,
} from './types';
import './safehouse.css';

interface ObjectDetailProps {
  object: PlacedObject | null;
  state: SafehouseState;
  onClose: () => void;
}

export function ObjectDetail({ object, state, onClose }: ObjectDetailProps) {
  if (!object) return null;

  return (
    <div className="object-detail-panel">
      <div className="detail-header">
        <span className="detail-type">{getTypeLabel(object.type)}</span>
        <button className="detail-close" onClick={onClose}>×</button>
      </div>
      <div className="detail-content">
        {renderContent(object, state)}
      </div>
    </div>
  );
}

function getTypeLabel(type: PlacedObject['type']): string {
  switch (type) {
    case 'gear': return '⚙ GEAR';
    case 'vehicle': return '🚗 VEHICLE';
    case 'thread': return '📌 DORMANT THREAD';
    case 'enhancement': return '⚡ ENHANCEMENT';
    case 'player': return '👤 CHARACTER';
    default: return '';
  }
}

function renderContent(object: PlacedObject, state: SafehouseState) {
  switch (object.type) {
    case 'gear':
      return <GearDetail gear={object.data as GearItem} />;
    case 'vehicle':
      return <VehicleDetail vehicle={object.data as Vehicle} />;
    case 'thread':
      return <ThreadDetail thread={object.data as DormantThread} />;
    case 'enhancement':
      return <EnhancementDetail enhancement={object.data as Enhancement} />;
    case 'player':
      return <CharacterDetail state={state} />;
    default:
      return null;
  }
}

// ============================================================================
// Detail Components
// ============================================================================

function GearDetail({ gear }: { gear: GearItem }) {
  return (
    <div className="detail-section">
      <h3 className="detail-name">{gear.name}</h3>
      <div className="detail-meta">
        <span className="meta-label">Category:</span>
        <span className="meta-value">{gear.category}</span>
      </div>
      {gear.description && (
        <p className="detail-description">{gear.description}</p>
      )}
      <div className="detail-status">
        {gear.used ? (
          <span className="status-badge status-warning">USED</span>
        ) : (
          <span className="status-badge status-success">READY</span>
        )}
        {gear.singleUse && (
          <span className="status-badge status-info">SINGLE USE</span>
        )}
      </div>
    </div>
  );
}

function VehicleDetail({ vehicle }: { vehicle: Vehicle }) {
  const fuelPercent = vehicle.fuel;
  const conditionPercent = vehicle.condition;

  return (
    <div className="detail-section">
      <h3 className="detail-name">{vehicle.name}</h3>
      <div className="detail-meta">
        <span className="meta-label">Type:</span>
        <span className="meta-value">{vehicle.type}</span>
      </div>
      {vehicle.description && (
        <p className="detail-description">{vehicle.description}</p>
      )}
      
      <div className="detail-bars">
        <div className="bar-row">
          <span className="bar-label">Fuel</span>
          <div className="bar-track">
            <div 
              className={`bar-fill ${fuelPercent <= 20 ? 'bar-danger' : fuelPercent <= 40 ? 'bar-warning' : 'bar-success'}`}
              style={{ width: `${fuelPercent}%` }}
            />
          </div>
          <span className="bar-value">{fuelPercent}%</span>
        </div>
        <div className="bar-row">
          <span className="bar-label">Condition</span>
          <div className="bar-track">
            <div 
              className={`bar-fill ${conditionPercent <= 20 ? 'bar-danger' : conditionPercent <= 40 ? 'bar-warning' : 'bar-success'}`}
              style={{ width: `${conditionPercent}%` }}
            />
          </div>
          <span className="bar-value">{conditionPercent}%</span>
        </div>
      </div>

      <div className="detail-status">
        <span className={`status-badge ${getVehicleStatusClass(vehicle.status)}`}>
          {vehicle.status.toUpperCase()}
        </span>
      </div>

      <div className="detail-capabilities">
        <h4>Capabilities</h4>
        <div className="capability-tags">
          {vehicle.terrain.map(t => (
            <span key={t} className="capability-tag">{t}</span>
          ))}
          {vehicle.cargo && <span className="capability-tag">cargo</span>}
          {vehicle.stealth && <span className="capability-tag">stealth</span>}
          <span className="capability-tag">capacity: {vehicle.capacity}</span>
        </div>
      </div>
    </div>
  );
}

function getVehicleStatusClass(status: Vehicle['status']): string {
  switch (status) {
    case 'Operational': return 'status-success';
    case 'Low Fuel':
    case 'Needs Repair': return 'status-warning';
    case 'Out of Fuel':
    case 'Broken Down': return 'status-danger';
    default: return '';
  }
}

function ThreadDetail({ thread }: { thread: DormantThread }) {
  return (
    <div className="detail-section">
      <h3 className="detail-name">{thread.origin}</h3>
      
      <div className="thread-info">
        <div className="thread-row">
          <span className="thread-label">Trigger:</span>
          <span className="thread-value">{thread.trigger}</span>
        </div>
        <div className="thread-row">
          <span className="thread-label">Consequence:</span>
          <span className="thread-value thread-consequence">{thread.consequence}</span>
        </div>
      </div>

      <div className="detail-status">
        <span className={`status-badge ${getSeverityClass(thread.severity)}`}>
          {thread.severity.toUpperCase()}
        </span>
        <span className="status-badge status-muted">
          Session {thread.createdSession}
        </span>
      </div>

      <p className="thread-warning">
        This thread is dormant. It will activate when its trigger condition is met.
      </p>
    </div>
  );
}

function getSeverityClass(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical': return 'status-danger';
    case 'major': return 'status-warning';
    case 'moderate': return 'status-info';
    case 'minor': return 'status-muted';
    default: return 'status-info';
  }
}

function EnhancementDetail({ enhancement }: { enhancement: Enhancement }) {
  return (
    <div className="detail-section">
      <h3 className="detail-name">{enhancement.name}</h3>
      
      <div className="detail-meta">
        <span className="meta-label">Source:</span>
        <span className="meta-value">{enhancement.source}</span>
      </div>

      <div className="enhancement-benefit">
        <h4>Benefit</h4>
        <p>{enhancement.benefit}</p>
      </div>

      <div className="detail-status">
        <span className="status-badge status-special">INSTALLED</span>
      </div>
    </div>
  );
}

function CharacterDetail({ state }: { state: SafehouseState }) {
  const char = state.character;
  if (!char) return null;

  return (
    <div className="detail-section">
      <h3 className="detail-name">{char.name}</h3>
      
      <div className="detail-meta">
        <span className="meta-label">Background:</span>
        <span className="meta-value">{char.background}</span>
      </div>

      <div className="detail-bars">
        <div className="bar-row">
          <span className="bar-label">Social Energy</span>
          <div className="bar-track">
            <div 
              className={`bar-fill ${char.socialEnergy.current <= 20 ? 'bar-danger' : char.socialEnergy.current <= 50 ? 'bar-warning' : 'bar-cyan'}`}
              style={{ width: `${(char.socialEnergy.current / char.socialEnergy.max) * 100}%` }}
            />
          </div>
          <span className="bar-value">{char.socialEnergy.current}/{char.socialEnergy.max}</span>
        </div>
      </div>

      <div className="character-stats">
        <div className="stat-row">
          <span className="stat-label">Credits</span>
          <span className="stat-value credits">¤{char.credits}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Location</span>
          <span className="stat-value">{state.location}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Region</span>
          <span className="stat-value">{state.region}</span>
        </div>
      </div>

      <div className="character-inventory-summary">
        <h4>Inventory Summary</h4>
        <div className="inventory-counts">
          <span className="count-item">
            <span className="count-icon">⚙</span>
            <span className="count-value">{state.gear.length}</span>
            <span className="count-label">Gear</span>
          </span>
          <span className="count-item">
            <span className="count-icon">🚗</span>
            <span className="count-value">{state.vehicles.length}</span>
            <span className="count-label">Vehicles</span>
          </span>
          <span className="count-item">
            <span className="count-icon">⚡</span>
            <span className="count-value">{state.enhancements.length}</span>
            <span className="count-label">Enhancements</span>
          </span>
          <span className="count-item">
            <span className="count-icon">📌</span>
            <span className="count-value">{state.threads.length}</span>
            <span className="count-label">Threads</span>
          </span>
        </div>
      </div>
    </div>
  );
}
