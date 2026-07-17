from base.modules.regulatory import AbstractAgencyBackend


class AgencyRegistry:
    _backends: dict[str, AbstractAgencyBackend] = {}

    @classmethod
    def register(cls, backend):
        code = backend.agency_code.lower()
        if code:
            cls._backends[code] = backend

    @classmethod
    def get(cls, code):
        return cls._backends.get(code.lower()) if code else None

    @classmethod
    def choices(cls):
        return [(code, b.agency_name) for code, b in cls._backends.items()]


agency_registry = AgencyRegistry()
