from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.client_ip import TrustedProxyClientIPMiddleware
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.errors import ServiceUnavailableError
from app.core.logging_config import configure_logging
from app.core.request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from app.core.security_headers import install_security_headers
from app.db.session import SessionLocal
from app.schemas.base import ApiResponse, CamelModel, ErrorEnvelope

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="Üst yönetim için formen performans takip ve analiz sistemi (Faz 1 — çekirdek API).",
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(TrustedProxyClientIPMiddleware, trusted_proxies=settings.trusted_proxy_ips)
install_security_headers(app, environment=settings.environment)

register_exception_handlers(app)

app.include_router(api_router)


class HealthStatus(CamelModel):
    status: str
    database: str | None = None


@app.get("/health", response_model=ApiResponse[HealthStatus])
@app.get("/health/live", response_model=ApiResponse[HealthStatus])
def liveness() -> ApiResponse[HealthStatus]:
    # Process çalışıyor ve istek kabul ediyor. Veritabanına veya başka bir bağımlılığa
    # dokunmaz; Postgres kesintisi container'ı restart döngüsüne sokmamalı, durumu
    # yalnızca /health/ready yansıtmalıdır.
    return ApiResponse(data=HealthStatus(status="ok"))


@app.get("/health/ready", response_model=ApiResponse[HealthStatus])
def readiness() -> ApiResponse[HealthStatus]:
    # Yalnızca her isteğin ihtiyaç duyduğu veritabanını kontrol eder. SMTP, S3,
    # CloudFront ve LLM kendi fail-soft davranışı olan isteğe bağlı entegrasyonlardır;
    # bunlardaki kesinti tüm backend'i "not ready" durumuna düşürmemelidir.
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        raise ServiceUnavailableError(
            "Veritabanı bağlantısı kullanılamıyor.",
            details={"dependency": "database", "status": "unreachable"},
        )
    return ApiResponse(data=HealthStatus(status="ok", database="reachable"))


def _custom_openapi() -> dict:
    if app.openapi_schema is not None:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    error_schema = ErrorEnvelope.model_json_schema(ref_template="#/components/schemas/{model}")
    components.update(error_schema.pop("$defs", {}))
    components["ErrorEnvelope"] = error_schema

    request_id_header = {
        "description": "İstek korelasyon kimliği.",
        "schema": {"type": "string"},
    }
    error_codes = ("400", "401", "403", "404", "409", "422", "429", "500")
    error_response = {
        "description": "Standart API hata zarfı.",
        "headers": {REQUEST_ID_HEADER: request_id_header},
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}},
    }

    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = operation.setdefault("responses", {})
            for response in responses.values():
                response.setdefault("headers", {}).setdefault(REQUEST_ID_HEADER, request_id_header)
            if path.startswith("/api/v1"):
                for code in error_codes:
                    documented = dict(error_response)
                    documented["headers"] = dict(error_response["headers"])
                    if code == "429":
                        documented["headers"]["Retry-After"] = {
                            "description": "Yeni isteğe kadar beklenecek saniye.",
                            "schema": {"type": "integer"},
                        }
                    responses[code] = documented
            elif path == "/health/ready":
                responses["503"] = error_response

    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi
