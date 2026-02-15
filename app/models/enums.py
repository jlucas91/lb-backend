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
