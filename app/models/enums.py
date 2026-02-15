import enum


class LocationType(enum.StrEnum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    OUTDOOR = "outdoor"
    INSTITUTIONAL = "institutional"
    HOSPITALITY = "hospitality"
    TRANSPORTATION = "transportation"
    HISTORICAL = "historical"
    STUDIO = "studio"
    OTHER = "other"


class FileType(enum.StrEnum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


class ProductionStatus(enum.StrEnum):
    ACTIVE = "active"
    WRAPPED = "wrapped"
    ARCHIVED = "archived"


class ProductionRole(enum.StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"


class ProductionLocationStatus(enum.StrEnum):
    SCOUTED = "scouted"
    APPROVED = "approved"
    REJECTED = "rejected"
    BOOKED = "booked"


class SharePermission(enum.StrEnum):
    VIEW = "view"
    EDIT = "edit"


class ProjectType(enum.StrEnum):
    MOVIE = "movie"
    TV_SHOW = "tv_show"
    COMMERCIAL = "commercial"
    MUSIC_VIDEO = "music_video"
    DOCUMENTARY = "documentary"
    SHORT_FILM = "short_film"
    OTHER = "other"


class ProjectStatus(enum.StrEnum):
    ACTIVE = "active"
    WRAPPED = "wrapped"
    ARCHIVED = "archived"


class ProjectRole(enum.StrEnum):
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"


class ScoutingStatus(enum.StrEnum):
    DRAFT = "draft"
    COMPLETE = "complete"
