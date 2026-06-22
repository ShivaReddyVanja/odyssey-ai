"use client";

import React, { useState, useEffect } from "react";
import { Place, TransitOption } from "../hooks/useEventStream";

interface CandidateListProps {
  candidates: Record<string, (Place | TransitOption)[]>;
  lastDiscovery: { category: string; timestamp: number } | null;
}

type TabType = "transit" | "accommodation" | "food" | "activities";

/* ─── Inline SVG Icons matching Notion minimal aesthetic ─── */

function TransitIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3.5c-.5-.5-2.5 0-4 1.5L13.5 8.5 5.3 6.7c-.9-.2-1.9.1-2.4.9l-.5.7 8.3 4.1-3.3 3.3-3.7-1.1c-.6-.2-1.2 0-1.5.5l-.3.4 4 2.8 2.8 4 .4-.3c.5-.3.7-1 .5-1.5l-1.1-3.7 3.3-3.3 4.1 8.3.7-.5c.8-.5 1.1-1.5.9-2.4z" />
    </svg>
  );
}

function StaysIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 22v-3a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v3" />
      <path d="M4 17V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12" />
      <path d="M8 8h8" />
      <path d="M8 12h8" />
    </svg>
  );
}

function DiningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2" />
      <path d="M7 2v2" />
      <path d="M9 15v6H5v-6" />
      <path d="M21 15V2v5a5 5 0 0 1-5 5h-1v9H15" />
    </svg>
  );
}

function SightsIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76" />
    </svg>
  );
}

function MapPinIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

const TABS: { id: TabType; label: string; Icon: React.ComponentType<{ className?: string }> }[] = [
  { id: "transit",       label: "Transit", Icon: TransitIcon },
  { id: "accommodation", label: "Stays",   Icon: StaysIcon },
  { id: "food",          label: "Dining",  Icon: DiningIcon },
  { id: "activities",    label: "Sights",  Icon: SightsIcon },
];

export default function CandidateList({ candidates, lastDiscovery }: CandidateListProps) {
  const [activeTab, setActiveTab] = useState<TabType>("transit");

  /* Auto-switch to freshly discovered category */
  useEffect(() => {
    if (lastDiscovery) {
      setActiveTab(lastDiscovery.category as TabType);
    }
  }, [lastDiscovery]);

  const items = candidates[activeTab] ?? [];

  return (
    <div className="candidate-panel">

      {/* ── Tab Bar ── */}
      <div className="candidate-tabs">
        {TABS.map((tab) => {
          const count = candidates[tab.id]?.length ?? 0;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`candidate-tab-btn ${isActive ? "candidate-tab-btn--active" : ""}`}
            >
              <tab.Icon className="candidate-tab-icon" />
              <span className="candidate-tab-label">{tab.label}</span>
              {count > 0 && (
                <span className="candidate-tab-count">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── List ── */}
      <div className="candidate-list">
        {items.length === 0 ? (
          <div className="candidate-empty">
            <p className="candidate-empty-text">No candidates yet</p>
            <p className="candidate-empty-hint">Discoveries stream in real-time during planning.</p>
          </div>
        ) : (
          items.map((item, idx) => {
            if (item.type === "transit") {
              return <TransitRow key={`${item.id ?? "transit"}-${idx}`} item={item} />;
            }
            return <PlaceRow key={`${item.id ?? "place"}-${idx}`} item={item} />;
          })
        )}
      </div>

    </div>
  );
}

/* ── Place Row ─────────────────────────────────────────────────────────── */

function PlaceRow({ item }: { item: Place }) {
  const [imgErr, setImgErr] = React.useState(false);

  const costLabel = item.cost_estimate
    ? `${"$".repeat(Math.min(Math.round(item.cost_estimate), 4))}`
    : null;

  return (
    <div className="place-item">
      {item.photo_url && !imgErr ? (
        <img
          className="place-thumb"
          src={item.photo_url}
          alt={item.name}
          onError={() => setImgErr(true)}
        />
      ) : (
        <div className="place-thumb-placeholder">
          {item.category === "food" ? (
            <DiningIcon className="place-thumb-icon" />
          ) : item.category === "stay" ? (
            <StaysIcon className="place-thumb-icon" />
          ) : item.category === "sightseeing" ? (
            <SightsIcon className="place-thumb-icon" />
          ) : (
            <MapPinIcon className="place-thumb-icon" />
          )}
        </div>
      )}
      <div className="place-info">
        <div className="place-name-row">
          <span className="place-name">{item.name}</span>
          {costLabel && <span className="place-cost">{costLabel}</span>}
        </div>
        <div className="place-address">{item.location.address}</div>
        <div className="place-meta-row">
          {item.rating != null ? (
            <span className="place-rating">
              <span className="place-rating-star">★</span>
              {item.rating.toFixed(1)}
            </span>
          ) : (
            <span className="place-rating" style={{ color: "var(--color-text-ghost)" }}>—</span>
          )}
          <span className="place-category-tag">{item.category}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Transit Row ───────────────────────────────────────────────────────── */

function TransitRow({ item }: { item: TransitOption }) {
  const priceLabel = item.estimated_price
    ? `₹${item.estimated_price.toLocaleString("en-IN")}`
    : "—";

  return (
    <div className="transit-item">
      <div className="transit-top-row">
        <span className="transit-mode-badge">{item.mode}</span>
        <span className="transit-price">{priceLabel}</span>
      </div>
      <div className="transit-route">
        {item.origin}
        <span className="transit-arrow">→</span>
        {item.destination}
      </div>
      <div className="transit-meta-row">
        {item.carrier && <span>{item.carrier}</span>}
        {item.carrier && item.departure_time && (
          <span className="transit-meta-sep">·</span>
        )}
        {item.departure_time && <span>Dep {item.departure_time}</span>}
        {item.duration_minutes > 0 && (
          <>
            <span className="transit-meta-sep">·</span>
            <span>{item.duration_minutes}m</span>
          </>
        )}
      </div>
    </div>
  );
}
