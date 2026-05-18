from sqlalchemy import JSON, TypeDecorator

try:
    from sqlalchemy.dialects.postgresql import JSONB as _PgJSONB
except ImportError:
    _PgJSONB = None


class JSONB(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if _PgJSONB and dialect.name == "postgresql":
            return dialect.type_descriptor(_PgJSONB())
        return dialect.type_descriptor(JSON())
