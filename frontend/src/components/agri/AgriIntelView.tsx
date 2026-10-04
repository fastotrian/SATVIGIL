/**
 * SATVIGIL — AGRI INTEL View
 * 3-panel agricultural intelligence dashboard:
 *   Left: Crop Health (NDVI)
 *   Top-Right: Field Boundary Mapping
 *   Bottom-Right: Crop Damage Assessment
 */
import React from 'react';
import { CropHealthPanel } from './CropHealthPanel';
import { FieldBoundaryPanel } from './FieldBoundaryPanel';
import { DamageAssessmentPanel } from './DamageAssessmentPanel';

export function AgriIntelView() {
  return (
    <div className="flex flex-1 h-full overflow-hidden p-3 gap-3" style={{ background: 'var(--navy-950)' }}>
      {/* Left Column: Crop Health */}
      <div className="w-80 shrink-0 flex flex-col gap-3 overflow-hidden">
        <CropHealthPanel />
      </div>

      {/* Right Column: Field Boundary + Damage */}
      <div className="flex-1 flex flex-col gap-3 overflow-hidden">
        <div className="flex-1 min-h-0">
          <FieldBoundaryPanel />
        </div>
        <div className="h-64 shrink-0">
          <DamageAssessmentPanel />
        </div>
      </div>
    </div>
  );
}
