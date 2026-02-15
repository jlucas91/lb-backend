# LocationsBook — Data Model & API Design

## Context

LocationsBook helps location managers in the film industry manage scouted locations. Core needs:
- **Private portfolios**: Each user maintains their own collection of locations
- **Rich location data**: Photos, structured attributes (location type, address, etc.)
- **Productions**: Users collaborate on film/TV productions, adding locations to them
- **Sharing**: Users can share individual locations with each other

---

## Data Model

### User

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, default `gen_random_uuid()` |
| email | VARCHAR(255) | Unique, not null |
| display_name | VARCHAR(100) | Not null |
| password_hash | VARCHAR(255) | Not null |
| created_at | TIMESTAMPTZ | Default now |
| updated_at | TIMESTAMPTZ | Default now, auto-update |

Auth strategy is out of scope for this document — `password_hash` is a placeholder. Can swap for OAuth/SSO later.

---

### Location

The core entity. Owned by a single user (their portfolio).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| owner_id | UUID | FK → User, not null |
| name | VARCHAR(200) | Not null |
| address | TEXT | Full address string |
| city | VARCHAR(100) | |
| state | VARCHAR(100) | State/province/region |
| country | VARCHAR(100) | |
| latitude | DOUBLE | Nullable |
| longitude | DOUBLE | Nullable |
| location_type | VARCHAR(50) | Enum — see below |
| description | TEXT | Free-form notes |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**`location_type` values** (stored as string, validated in app layer via Python enum):
- `residential` — houses, apartments
- `commercial` — offices, retail
- `industrial` — warehouses, factories
- `outdoor` — parks, streets, fields, nature
- `institutional` — schools, hospitals, government
- `hospitality` — hotels, restaurants, bars
- `transportation` — airports, train stations
- `historical` — heritage sites, landmarks
- `studio` — soundstages, studios
- `other`

---

### File

Attachments on a location — photos, videos, PDFs, documents, etc. Stored as references to object storage (S3/etc.).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| location_id | UUID | FK → Location, not null, cascade delete |
| file_type | VARCHAR(20) | `photo`, `video`, `document`, `other` |
| storage_key | VARCHAR(500) | Path/key in object storage |
| filename | VARCHAR(255) | Original filename |
| content_type | VARCHAR(100) | MIME type (image/jpeg, video/mp4, application/pdf, etc.) |
| size_bytes | INTEGER | File size |
| caption | TEXT | Optional |
| sort_order | INTEGER | Default 0, for ordering |
| created_at | TIMESTAMPTZ | |

---

### Production

A film/TV production that users collaborate on.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | VARCHAR(200) | Not null |
| description | TEXT | |
| status | VARCHAR(20) | `active`, `wrapped`, `archived` |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

### ProductionMember (join table: User ↔ Production)

| Column | Type | Notes |
|--------|------|-------|
| production_id | UUID | PK (composite), FK → Production |
| user_id | UUID | PK (composite), FK → User |
| role | VARCHAR(20) | `owner`, `manager`, `member` |
| joined_at | TIMESTAMPTZ | |

- `owner` — created the production, full control
- `manager` — can add/remove locations, invite members
- `member` — can view and add locations

---

### ProductionLocation (join table: Location ↔ Production)

| Column | Type | Notes |
|--------|------|-------|
| production_id | UUID | PK (composite), FK → Production |
| location_id | UUID | PK (composite), FK → Location |
| added_by_id | UUID | FK → User, not null |
| status | VARCHAR(20) | `scouted`, `approved`, `rejected`, `booked` |
| notes | TEXT | Production-specific notes about this location |
| added_at | TIMESTAMPTZ | |

---

### LocationShare

Sharing a location from one user to another.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| location_id | UUID | FK → Location, not null |
| shared_by_id | UUID | FK → User (the owner sharing it) |
| shared_with_id | UUID | FK → User (the recipient) |
| permission | VARCHAR(10) | `view`, `edit` |
| created_at | TIMESTAMPTZ | |

Unique constraint on `(location_id, shared_with_id)` — can't share the same location twice with the same user.

---

## ER Diagram (text)

```
User ──< Location ──< File
 │            │
 │            ├──< LocationShare >── User
 │            │
 │            └──< ProductionLocation >── Production
 │                                           │
 └──────< ProductionMember >─────────────────┘
```

---

## API Endpoints

All endpoints prefixed with `/api`. Auth (current user) assumed on all endpoints except registration/login.

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get access token |
| GET | `/auth/me` | Get current user profile |
| PATCH | `/auth/me` | Update current user profile |

---

### Locations (user's portfolio)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/locations` | List my locations (filterable by type, city, search) |
| POST | `/locations` | Create a location |
| GET | `/locations/{id}` | Get location detail (with photos) |
| PATCH | `/locations/{id}` | Update location |
| DELETE | `/locations/{id}` | Delete location (cascades to files) |

**Query params for GET `/locations`**:
- `location_type` — filter by type
- `q` — search name/address/description
- `page`, `per_page` — pagination (default 20)

---

### Files (photos, videos, documents)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/locations/{id}/files/presign` | Request presigned upload URL(s) |
| POST | `/locations/{id}/files/confirm` | Confirm upload completed, store metadata |
| GET | `/locations/{id}/files` | List files for a location (filterable by `file_type`) |
| PATCH | `/locations/{id}/files/{file_id}` | Update caption/sort order |
| DELETE | `/locations/{id}/files/{file_id}` | Delete a file (+ delete from storage) |

**Upload flow**: Client calls `presign` with filename/content-type, gets back a presigned S3 PUT URL + a `storage_key`. Client uploads directly to S3. Client calls `confirm` with the `storage_key` to finalize the file record. `file_type` is inferred from `content_type` (image/* → photo, video/* → video, application/pdf → document, etc.).

---

### Productions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/productions` | List productions I'm a member of |
| POST | `/productions` | Create a production (caller becomes owner) |
| GET | `/productions/{id}` | Get production detail |
| PATCH | `/productions/{id}` | Update production (owner/manager) |
| DELETE | `/productions/{id}` | Delete production (owner only) |

---

### Production Members

| Method | Path | Description |
|--------|------|-------------|
| GET | `/productions/{id}/members` | List members |
| POST | `/productions/{id}/members` | Add a member (owner/manager) |
| PATCH | `/productions/{id}/members/{user_id}` | Change member role (owner only) |
| DELETE | `/productions/{id}/members/{user_id}` | Remove member (owner/manager) |

---

### Production Locations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/productions/{id}/locations` | List locations in a production |
| POST | `/productions/{id}/locations` | Add a location to a production |
| PATCH | `/productions/{id}/locations/{location_id}` | Update status/notes |
| DELETE | `/productions/{id}/locations/{location_id}` | Remove location from production |

---

### Location Sharing

| Method | Path | Description |
|--------|------|-------------|
| POST | `/locations/{id}/shares` | Share location with a user |
| GET | `/locations/{id}/shares` | List who this location is shared with |
| DELETE | `/locations/{id}/shares/{share_id}` | Revoke a share |
| GET | `/shared-with-me` | List locations others have shared with me |

---

## Access Control Summary

| Resource | Who can read | Who can write |
|----------|-------------|---------------|
| Location | Owner + shared-with users + production members (if added to their production) | Owner + `edit` share recipients |
| File | Same as parent location | Same as parent location write |
| Production | Members | Owner + managers |
| Production members | Members | Owner (roles), owner+managers (add/remove) |
| Production locations | Members | Members (add), owner+managers (status changes, remove) |
| Location shares | Location owner | Location owner |

---

## Decisions

- **Location attributes**: Start with basics (name, address, coordinates, type, description). Add film-industry-specific fields later via migrations.
- **Photo upload**: Presigned URL flow — client requests a presigned URL from the API, uploads directly to S3, then confirms. API stores metadata only.
- **Auth**: Out of scope for this document. `password_hash` on User is a placeholder.
- **Search**: Start with simple LIKE/ILIKE. Add `tsvector` full-text search later if needed.

---

## Implementation Plan

### Phase 1: Models & Migration

1. Create SQLAlchemy models in `app/models/`:
   - `user.py` — User model
   - `location.py` — Location model
   - `file.py` — File model
   - `production.py` — Production model
   - `production_member.py` — ProductionMember model
   - `production_location.py` — ProductionLocation model
   - `location_share.py` — LocationShare model
   - `__init__.py` — re-export all models (needed for Alembic discovery)

2. Create Python enums in `app/models/enums.py`:
   - `LocationType`, `FileType`, `ProductionStatus`, `ProductionRole`, `ProductionLocationStatus`, `SharePermission`

3. Generate Alembic migration for all tables

### Phase 2: Schemas

Create Pydantic schemas in `app/schemas/`:
- One file per resource: `user.py`, `location.py`, `file.py`, `production.py`, `location_share.py`
- Each file has: `Create`, `Update`, `Response` schemas
- Pagination schema in `app/schemas/common.py`

### Phase 3: API Routes

Create route modules in `app/api/v1/`:
- `auth.py` — registration, login, me
- `locations.py` — CRUD + search/filter
- `files.py` — presign, confirm, list, update, delete
- `productions.py` — CRUD
- `production_members.py` — member management
- `production_locations.py` — location-production association
- `location_shares.py` — sharing + shared-with-me
- Wire all into `app/api/v1/router.py`

### Phase 4: Tests

- Model unit tests
- API integration tests per route module
