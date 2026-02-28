# SmugMug Sync — API & Process Reference

## SmugMug Internal API

We use SmugMug's internal JSON-RPC API (the same one their Organizer webapp uses), not their public OAuth API.

**Base URL:** `https://www.smugmug.com/services/api/json/1.4.0/`

All calls are GET requests with parameters in the query string. Authentication is via `SMSESS` session cookie obtained by logging in with username/password.

---

## Authentication

SmugMug uses cookie-based session auth. The key cookie is `SMSESS`. We authenticate programmatically via their internal login flow:

### Login flow

1. **GET `https://www.smugmug.com/login`** — returns the login page HTML and sets an initial `SMSESS` cookie.
2. **Extract `csrfToken`** from the page HTML via regex: `csrfToken":"([a-f0-9]{32})"`.
3. **POST to the JSON-RPC API** with `method=rpc.user.login` and form-encoded body:

```
Email={email}&Password={password}&OTPCode=&KeepLoggedIn=1&IsOAuth=0
&TimeZone=America/New_York&method=rpc.user.login&_token={csrfToken}
```

Required headers:
- `X-Requested-With: XMLHttpRequest`
- `Referer: https://www.smugmug.com/login`
- `Origin: https://www.smugmug.com`
- `Content-Type: application/x-www-form-urlencoded; charset=UTF-8`
- Full Chrome `User-Agent` string (SmugMug returns "Bad bot" for short/missing UA)

4. **On success** (`stat: "ok"`, HTTP 200): The `Set-Cookie` header contains the authenticated `SMSESS` cookie. On failure: HTTP 403 for invalid credentials, or `stat: "fail"` with a `message` field.

The authenticated `SMSESS` cookie is then used for all subsequent API calls.

### Account fields

- `email` — SmugMug login email (used for authentication)
- `password` — SmugMug login password
- `smugmug_nick` — SmugMug vanity URL nickname (e.g. `veronicarioseco`), used as the `nick` parameter in API calls

---

## API Methods

### 1. `rpc.organizer.getnodesbypath` — Fetch folder/gallery tree

Returns a **flat array** of all folders and albums in the account hierarchy.

**Parameters:**

| Param | Value | Notes |
|-------|-------|-------|
| `method` | `rpc.organizer.getnodesbypath` | |
| `paths` | `/` | Path to fetch children of. `/` = root |
| `depth` | `10` | Levels to recurse. High number = full tree |
| `childrenOnly` | `true` | Exclude the root node itself |
| `nick` | `{username}` | SmugMug account nickname |
| `pageNumber` | `1` | Only used at depth=1 |
| `pageSize` | `500` | Only used at depth=1 |

**Response shape:**

```json
{
  "stat": "ok",
  "paginationData": null,
  "nodes": [
    {
      "NodeID": "5qhczG",
      "ParentID": "J9qz87",
      "Type": 2,
      "Name": "My Folder",
      "UrlPath": "/My-Folder",
      "RemoteID": "",
      "RemoteKey": null,
      "HasChildren": true,
      "Depth": 1,
      "Description": ""
    },
    {
      "NodeID": "kpswCN",
      "ParentID": "5qhczG",
      "Type": 4,
      "Name": "My Album",
      "UrlPath": "/My-Folder/My-Album",
      "RemoteID": 474821359,
      "RemoteKey": "LQfhjb",
      "HasChildren": false,
      "Depth": 2,
      "Description": ""
    }
  ]
}
```

**Node types:**
- `Type=2` → **Folder** (container for other folders and albums)
- `Type=4` → **Album/Gallery** (contains images — maps to a "location" in our domain)

**Key fields per node:**

| Field | Meaning | Our model field |
|-------|---------|-----------------|
| `NodeID` | Unique short string ID | `smugmug_uri` |
| `ParentID` | Parent's `NodeID` | Resolved to `parent_id` (folders) or `folder_id` (galleries) |
| `Type` | 2=Folder, 4=Album | Determines target table |
| `Name` | Display name | `name` |
| `UrlPath` | URL-safe path from root | `url_path` |
| `RemoteID` | Numeric album ID (albums only; empty string for folders) | Used as `albumId` param in `getimages` |
| `RemoteKey` | Album key string (albums only) | `smugmug_album_key`, used as `albumKey` param in `getimages` |
| `HasChildren` | Whether node has children | Informational only (we fetch full tree in one call) |
| `Depth` | Level in tree (1 = root children) | Informational |
| `Description` | User-entered description | `description` (galleries) |

**Parent resolution:** The invisible root node's `NodeID` (e.g. `J9qz87`) appears as `ParentID` on all depth=1 nodes. Nodes whose `ParentID` equals this root ID are top-level items — we store them with `parent_id=NULL` / `folder_id=NULL`.

---

### 2. `rpc.organizer.getimages` — Fetch images in a gallery

Returns all images in a single album/gallery with metadata and download URLs.

**Parameters:**

| Param | Value | Notes |
|-------|-------|-------|
| `method` | `rpc.organizer.getimages` | |
| `albumId` | `{RemoteID}` | Numeric album ID from the node |
| `albumKey` | `{RemoteKey}` | Album key from the node |
| `nick` | `{username}` | SmugMug account nickname |
| `limit` | `100` | Page size |
| `startIndex` | `0` | Offset for pagination |

**Response shape:**

```json
{
  "stat": "ok",
  "imageCount": 71,
  "pagination": {
    "limit": 100,
    "startIndex": 0,
    "nextIndex": null,
    "totalCount": 71
  },
  "images": [ ... ]
}
```

**Pagination:** If `pagination.nextIndex` is not `null`, make another request with `startIndex={nextIndex}`. Repeat until `nextIndex` is `null`.

**Key fields per image:**

| Field | Meaning | Our model field |
|-------|---------|-----------------|
| `ImageKey` | Unique short string ID | `smugmug_image_key` and `smugmug_uri` |
| `FileName` | Display filename (no extension) | — |
| `Components[0].FileName` | Real filename with extension | `filename` |
| `Caption` | User caption | `caption` |
| `OriginalWidth` | Pixel width of original | `width` |
| `OriginalHeight` | Pixel height of original | `height` |
| `Latitude` / `Longitude` | GPS coords (0 = not set) | Useful for future location mapping |
| `SortPosition` | Order within album | For ordering |
| `Format` | File format (`jpg`, `png`, etc.) | Informational |
| `GalleryUrl` | Public URL to image page | Informational |

**Image sizes (`Sizes` dict):**

Each image has multiple size renditions. Keys are size codes:

| Code | Description | Typical use |
|------|-------------|-------------|
| `O` | Original | Often `usable: false` (cold storage / paywalled) |
| `5K`, `4K`, `X5`–`X2` | Very large | Usually `usable: false`, `cold: true` |
| `XL` | ~1024px wide | **Best usable size** — use for downloads |
| `L` | ~800px | Good fallback |
| `M` | ~600px | Medium |
| `S` | ~400px | Small |
| `Th` | 150x150 square | Thumbnail |
| `Ti` | 100x100 square | Tiny thumbnail |
| `D` | Download | Has URL but `cold: true` (may need warming) |

Only entries with `usable: true` have a `url` field. Our download strategy: pick the largest `usable: true` size that is not `cold`. Priority order: `XL` > `L` > `M` > `S`.

---

## Sync Process

### Overview

For a single SmugMug account, the full sync is:

1. **Fetch tree** — 1 API call to get all folders + galleries
2. **Upsert folders & galleries** — parse the flat node list, resolve parent relationships
3. **Fetch images** — 1+ API calls per gallery (paginated)
4. **Upsert images** — match on `(gallery_id, smugmug_uri)`
5. **Update status** — mark account as synced or failed

### Step-by-step

#### Step 1: Fetch the full node tree

```
GET ?method=rpc.organizer.getnodesbypath&paths=/&depth=10&childrenOnly=true&nick={nick}&pageSize=500
```

Single request returns every folder and album as a flat list. Tested with a real account: 29 nodes in one response. Should scale to hundreds of nodes without issue.

#### Step 2: Partition and upsert nodes

Iterate through `nodes[]`:

- **Identify the root `ParentID`**: The `ParentID` on depth=1 nodes is the invisible root. Any node whose `ParentID` equals this value is a top-level item.

- **Type=2 (Folder)**: Upsert into `smugmug_folders`:
  - Match on `(account_id, smugmug_uri)` where `smugmug_uri = NodeID`
  - Set `parent_id` by looking up the folder whose `smugmug_uri = ParentID` (NULL if root)
  - Set `name`, `url_path`, `sort_order` (use list index or `Depth`)

- **Type=4 (Album)**: Upsert into `smugmug_galleries`:
  - Match on `(account_id, smugmug_uri)` where `smugmug_uri = NodeID`
  - Set `folder_id` by looking up the folder whose `smugmug_uri = ParentID` (NULL if parent is root)
  - Set `name`, `url_path`, `description`, `smugmug_album_key = RemoteKey`

**Ordering matters:** Process folders first (all Type=2), then albums (Type=4), so `folder_id` lookups succeed.

#### Step 3: Fetch images per gallery

For each gallery with a valid `RemoteID` and `RemoteKey`:

```
GET ?method=rpc.organizer.getimages&albumId={RemoteID}&albumKey={RemoteKey}&nick={nick}&limit=100&startIndex=0
```

Paginate until `nextIndex` is null.

#### Step 4: Upsert images

For each image in the response:

- Match on `(gallery_id, smugmug_uri)` where `smugmug_uri = ImageKey`
- Set `filename = Components[0].FileName` (fallback to `FileName` + `.` + `Format`)
- Set `caption`, `width = OriginalWidth`, `height = OriginalHeight`
- Set `smugmug_image_key = ImageKey`
- Set `smugmug_url` = URL of the best usable size (XL > L > M > S)

Update the gallery's `image_count` from the response `imageCount`.

#### Step 5: Finalize

- Set `last_synced_at = now()` on all upserted records
- Set account `sync_status = "idle"`, `last_synced_at = now()`
- On any error: set `sync_status = "failed"`, `sync_error = {error message}`

### Estimated API calls

For a given account: **1 + N** where N = number of galleries. A typical account with 25 galleries = 26 API calls. Galleries with >100 images add extra calls for pagination.

### Future enhancements

- **Image download to S3**: After upserting an image, if `file_id` is null, download the image from `smugmug_url`, upload to S3, create a `File` record, and link it
- **Incremental sync**: Compare `DateModified` on nodes to skip unchanged galleries
- **Rate limiting**: Add delays between API calls if SmugMug starts throttling
