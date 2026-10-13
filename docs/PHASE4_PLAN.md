# Phase 4 – Situation Room + Digital Ambassador Full Features

**Priority order (from user)**: Situation Room → Digital Ambassadors → Listen → Ads → CREATE → geo depth

## Goals
1. Production-usable Situation Room on large displays and desktop
2. Complete Digital Ambassador lifecycle (register → verify → ward allocate → task → report → leaderboard → badges)
3. Human-approval workflow for all recommended actions
4. Leaflet map with real PostGIS layers (even if geometries are still placeholders)

## Phase 4 Deliverables

### Situation Room
- [ ] Configurable layout / auto-rotate for large screens
- [ ] Live WebSocket feed for alerts (Redis pub/sub)
- [ ] Recommendation Review & Assign modal (creates tasks)
- [ ] Campaign calendar strip
- [ ] System health panel
- [ ] Election countdown (configurable date)

### Digital Ambassadors
- [x] List + create + verify + leaderboard (API done in Phase 3)
- [ ] Mobile-friendly Ambassador portal page
- [ ] Task assignment & daily reporting
- [ ] Badge system & performance score calculation
- [ ] Ward allocation UI
- [ ] Content pack distribution (approval-gated)

### Shared
- [ ] Leaflet map component consuming /geo/hierarchy + boundaries
- [ ] Role-guarded navigation
- [ ] Basic notification centre (in-app)

## Start immediately
1. Leaflet map component
2. Ambassador portal page
3. Task model + API + assignment flow
4. Recommendation → Task conversion
