from enum import Enum

from django.utils.translation import gettext_lazy as _

MAX_S3_BUCKET_LENGTH = 63
MAX_S3_KEY_LENGTH = 1024

SEP_AND_PREFIX_LENGTH = 5
MAX_STORAGE_PATH_LENGTH = (
    SEP_AND_PREFIX_LENGTH + MAX_S3_BUCKET_LENGTH + MAX_S3_KEY_LENGTH
)  # bucket/key separator is a single slash


class IntegerEnumWithChoices(int, Enum):
    @classmethod
    def choices(cls) -> tuple[tuple[int, str], ...]:
        return tuple((e.value, str(e.value)) for e in cls)

    @classmethod
    def values(cls) -> tuple:
        return tuple(e.value for e in cls)


class StringEnumWithChoices(str, Enum):
    @classmethod
    def choices(cls) -> tuple[tuple[str, str], ...]:
        return tuple((str(e.value), str(e.value)) for e in cls)

    @classmethod
    def values(cls) -> tuple:
        return tuple(e.value for e in cls)


class ProcessingStates(StringEnumWithChoices):
    MISSING = "missing"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    DELETED = "deleted"
    ERROR = "error"

    @classmethod
    def get_default(cls) -> str:
        return cls.MISSING.value

    @classmethod
    def choices(cls) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str], tuple[str, str]]:
        result = (
            (cls.MISSING.value, _("アップロード待ち")),
            (cls.UPLOADED.value, _("アップロード済")),
            (cls.DELETED.value, _("削除済")),
            (cls.ERROR.value, _("エラー")),
        )
        return result


class PresignedUrlClientMethods(StringEnumWithChoices):
    PUT = "put_object"
    GET = "get_object"
    POST = "post_object"
