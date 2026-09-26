/**
 * SATVIGIL — Operational Marquee / Bloomberg-Style Ops Log Ticker
 * Fixed 28px bottom status strip with live scrolling telemetry stream.
 */
import React from 'react';
import { useAlertStore } from '../../store/alertStore';

export function OpsLogFooter() {
  return (
    <footer
      className="h-2 w-full shrink-0 select-none z-20"
      style={{
        background: 'var(--navy-950)',
        borderTop: '1px solid var(--navy-800)',
      }}
    />
  );
}
