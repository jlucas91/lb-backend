# LocationsBook API Reference

Frontend developer reference for the LocationsBook REST API.

**Base URL**: `/api/v1`
**Content-Type**: `application/json` (all requests and responses unless noted)
**Auth**: Bearer token in `Authorization` header on all endpoints except `POST /auth/register` and `POST /auth/login`.

---

## Types & Enums

```typescript
// All IDs are UUID strings: "550e8400-e29b-41d4-a716-446655440000"
// All timestamps are ISO 8601 strings: "2026-02-15T12:00:00Z"

type LocationType =
  | "residential"   // houses, apartments
  | "commercial"    // offices, retail
  | "industrial"    // warehouses, factories
  | "outdoor"       // parks, streets, fields, nature
  | "institutional" // schools, hospitals, government
  | "hospitality"   // hotels, restaurants, bars
  | "transportation"// airports, train stations
  | "historical"    // heritage sites, landmarks
  | "studio"        // soundstages, studios
  | "other";

type FileType = "photo" | "video" | "document" | "other";

type ProductionStatus = "active" | "wrapped" | "archived";

type ProductionRole = "owner" | "manager" | "member";

type ProductionLocationStatus = "scouted" | "approved" | "rejected" | "booked";

type SharePermission = "view" | "edit";
```

---

## Pagination

Paginated list endpoints accept these query params and return a wrapper:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `per_page` | integer | 20 | Items per page (max 100) |

```typescript
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}
```

---

## Error Responses

All errors return:

```typescript
interface ErrorResponse {
  detail: string; // Human-readable message
}
```

Common HTTP status codes:
- `400` — Validation error or bad request
- `401` — Not authenticated
- `403` — Forbidden (insufficient permissions)
- `404` — Resource not found
- `409` — Conflict (e.g. duplicate email, already shared)
- `422` — Unprocessable entity (Pydantic validation)

FastAPI validation errors (422) return:

```typescript
interface ValidationErrorResponse {
  detail: Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}
```

---

## Auth

### `POST /auth/register`

Create a new account.

**Request:**
```typescript
{
  email: string;        // max 255 chars
  display_name: string; // max 100 chars
  password: string;     // min 8 chars
}
```

**Response (201):**
```typescript
{
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}
```

---

### `POST /auth/login`

Get an access token.

**Request:**
```typescript
{
  email: string;
  password: string;
}
```

**Response (200):**
```typescript
{
  access_token: string;
  token_type: "bearer";
}
```

Use the token in subsequent requests: `Authorization: Bearer <access_token>`

---

### `GET /auth/me`

Get the current user's profile.

**Response (200):**
```typescript
interface User {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
  updated_at: string;
}
```

---

### `PATCH /auth/me`

Update the current user's profile. All fields optional.

**Request:**
```typescript
{
  display_name?: string;
}
```

**Response (200):** `User`

---

## Locations

### `GET /locations`

List locations in the current user's portfolio.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `location_type` | LocationType | Filter by type |
| `q` | string | Search name, address, description (case-insensitive) |
| `page` | integer | Page number |
| `per_page` | integer | Items per page |

**Response (200):** `PaginatedResponse<LocationSummary>`

```typescript
interface LocationSummary {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  location_type: LocationType | null;
  created_at: string;
  updated_at: string;
}
```

---

### `POST /locations`

Create a new location in the current user's portfolio.

**Request:**
```typescript
{
  name: string;                    // required, max 200 chars
  address?: string | null;
  city?: string | null;            // max 100 chars
  state?: string | null;           // max 100 chars
  country?: string | null;         // max 100 chars
  latitude?: number | null;        // -90 to 90
  longitude?: number | null;       // -180 to 180
  location_type?: LocationType | null;
  description?: string | null;
}
```

**Response (201):** `Location`

---

### `GET /locations/{id}`

Get full location detail including files.

**Response (200):**

```typescript
interface Location {
  id: string;
  owner_id: string;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  location_type: LocationType | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  files: File[];  // ordered by sort_order
}
```

**Who can access:** Owner, users it's shared with, or production members (if the location is added to one of their productions).

---

### `PATCH /locations/{id}`

Update a location. All fields optional — only send what changed.

**Request:**
```typescript
{
  name?: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_type?: LocationType | null;
  description?: string | null;
}
```

**Response (200):** `Location`

**Who can write:** Owner, or users with `edit` share permission.

---

### `DELETE /locations/{id}`

Delete a location and all its files.

**Response:** `204 No Content`

**Who can delete:** Owner only.

---

## Files

Files are attachments on a location — photos, videos, documents. Upload uses a **presigned URL flow** (client uploads directly to S3, not through the API).

### Upload Flow

```
1. POST /locations/{id}/files/presign   →  get presigned URL + storage_key
2. PUT  <presigned_url>                 →  upload file directly to S3
3. POST /locations/{id}/files/confirm   →  finalize the file record in the DB
```

### `POST /locations/{id}/files/presign`

Request presigned upload URL(s).

**Request:**
```typescript
{
  files: Array<{
    filename: string;      // "sunset-photo.jpg"
    content_type: string;  // "image/jpeg"
  }>;
}
```

**Response (200):**
```typescript
{
  presigned_uploads: Array<{
    filename: string;
    storage_key: string;    // save this — needed for confirm step
    upload_url: string;     // presigned S3 PUT URL
    expires_in: number;     // seconds until URL expires
  }>;
}
```

**S3 upload**: `PUT` the file body to `upload_url` with `Content-Type` header matching the `content_type` you provided.

---

### `POST /locations/{id}/files/confirm`

Confirm upload completed and create the file record.

**Request:**
```typescript
{
  files: Array<{
    storage_key: string;   // from presign response
    filename: string;
    content_type: string;
    size_bytes: number;
    caption?: string | null;
    sort_order?: number;   // default 0
  }>;
}
```

**Response (201):**
```typescript
File[]  // array of created file records
```

`file_type` is auto-inferred from `content_type`:
- `image/*` → `"photo"`
- `video/*` → `"video"`
- `application/pdf` → `"document"`
- everything else → `"other"`

---

### `GET /locations/{id}/files`

List files for a location.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `file_type` | FileType | Filter by type (`photo`, `video`, `document`, `other`) |

**Response (200):**

```typescript
interface File {
  id: string;
  location_id: string;
  file_type: FileType;
  storage_key: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  caption: string | null;
  sort_order: number;
  created_at: string;
}
```

Returns `File[]` ordered by `sort_order` ascending.

---

### `PATCH /locations/{id}/files/{file_id}`

Update file metadata (caption or sort order).

**Request:**
```typescript
{
  caption?: string | null;
  sort_order?: number;
}
```

**Response (200):** `File`

---

### `DELETE /locations/{id}/files/{file_id}`

Delete a file (removes from storage too).

**Response:** `204 No Content`

---

## Productions

### `GET /productions`

List productions the current user is a member of.

**Response (200):** `PaginatedResponse<ProductionSummary>`

```typescript
interface ProductionSummary {
  id: string;
  name: string;
  description: string | null;
  status: ProductionStatus;
  my_role: ProductionRole;   // the current user's role
  created_at: string;
  updated_at: string;
}
```

---

### `POST /productions`

Create a production. The caller automatically becomes `owner`.

**Request:**
```typescript
{
  name: string;               // required, max 200 chars
  description?: string | null;
  status?: ProductionStatus;  // default "active"
}
```

**Response (201):** `Production`

---

### `GET /productions/{id}`

Get production detail.

**Response (200):**

```typescript
interface Production {
  id: string;
  name: string;
  description: string | null;
  status: ProductionStatus;
  my_role: ProductionRole;
  created_at: string;
  updated_at: string;
}
```

---

### `PATCH /productions/{id}`

Update production details. Owner or manager only.

**Request:**
```typescript
{
  name?: string;
  description?: string | null;
  status?: ProductionStatus;
}
```

**Response (200):** `Production`

---

### `DELETE /productions/{id}`

Delete a production. Owner only.

**Response:** `204 No Content`

---

## Production Members

### `GET /productions/{id}/members`

List members of a production. Any member can view.

**Response (200):**

```typescript
interface ProductionMember {
  user_id: string;
  display_name: string;
  email: string;
  role: ProductionRole;
  joined_at: string;
}
```

Returns `ProductionMember[]`.

---

### `POST /productions/{id}/members`

Add a member. Owner or manager only.

**Request:**
```typescript
{
  user_id: string;             // UUID of user to add
  role?: ProductionRole;       // default "member"
}
```

**Response (201):** `ProductionMember`

---

### `PATCH /productions/{id}/members/{user_id}`

Change a member's role. Owner only.

**Request:**
```typescript
{
  role: ProductionRole;
}
```

**Response (200):** `ProductionMember`

---

### `DELETE /productions/{id}/members/{user_id}`

Remove a member. Owner or manager only. Cannot remove the owner.

**Response:** `204 No Content`

---

## Production Locations

### `GET /productions/{id}/locations`

List locations added to a production. Any member can view.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | ProductionLocationStatus | Filter by status |
| `page` | integer | Page number |
| `per_page` | integer | Items per page |

**Response (200):** `PaginatedResponse<ProductionLocationDetail>`

```typescript
interface ProductionLocationDetail {
  production_id: string;
  location_id: string;
  status: ProductionLocationStatus;
  notes: string | null;
  added_by: {
    id: string;
    display_name: string;
  };
  added_at: string;
  location: LocationSummary;  // the actual location data
}
```

---

### `POST /productions/{id}/locations`

Add a location to a production. Any member can add.

**Request:**
```typescript
{
  location_id: string;
  status?: ProductionLocationStatus;  // default "scouted"
  notes?: string | null;
}
```

**Response (201):** `ProductionLocationDetail`

---

### `PATCH /productions/{id}/locations/{location_id}`

Update status or notes. Owner or manager only.

**Request:**
```typescript
{
  status?: ProductionLocationStatus;
  notes?: string | null;
}
```

**Response (200):** `ProductionLocationDetail`

---

### `DELETE /productions/{id}/locations/{location_id}`

Remove a location from a production. Owner or manager only.

**Response:** `204 No Content`

---

## Location Sharing

### `POST /locations/{id}/shares`

Share a location with another user. Location owner only.

**Request:**
```typescript
{
  shared_with_id: string;              // UUID of recipient
  permission?: SharePermission;        // default "view"
}
```

**Response (201):**

```typescript
interface LocationShareResponse {
  id: string;
  location_id: string;
  shared_by_id: string;
  shared_with: {
    id: string;
    display_name: string;
    email: string;
  };
  permission: SharePermission;
  created_at: string;
}
```

Returns `409` if already shared with that user.

---

### `GET /locations/{id}/shares`

List who a location is shared with. Location owner only.

**Response (200):** `LocationShareResponse[]`

---

### `DELETE /locations/{id}/shares/{share_id}`

Revoke a share. Location owner only.

**Response:** `204 No Content`

---

### `GET /shared-with-me`

List locations others have shared with the current user.

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `page` | integer | Page number |
| `per_page` | integer | Items per page |

**Response (200):** `PaginatedResponse<SharedLocationDetail>`

```typescript
interface SharedLocationDetail {
  share_id: string;
  permission: SharePermission;
  shared_by: {
    id: string;
    display_name: string;
  };
  created_at: string;
  location: LocationSummary;
}
```

---

## Entity Relationships (for UI)

```
User
 ├── owns Location[]
 │     ├── has File[]  (photos, videos, docs)
 │     ├── shared via LocationShare[]  →  other Users
 │     └── added to ProductionLocation[]  →  Productions
 │
 └── member of Production[]  (via ProductionMember)
       └── has ProductionLocation[]  →  Locations
```

### Key concepts

- **My Locations** (`GET /locations`): The user's private portfolio. They own these.
- **Shared With Me** (`GET /shared-with-me`): Locations other users have given them access to.
- **Production Locations** (`GET /productions/{id}/locations`): Locations added to a production by any member. These are *references* to locations owned by various users.
- A single location can appear in multiple productions and be shared with multiple users simultaneously.

### Permission model

| Role | What they can do |
|------|-----------------|
| Location owner | Full CRUD on location + files, share with others |
| Share recipient (`view`) | Read-only access to location + files |
| Share recipient (`edit`) | Read + update location + files |
| Production owner | Full control of production, members, production-locations |
| Production manager | Manage members (add/remove), manage production-locations |
| Production member | View production, add locations to production |
