from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Formen Performans Takip Sistemi"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Yalnızca geliştirme/demo ortamı içindir; get_current_identity içinde OIDC token
    # doğrulamasını atlar. Aşağıdaki _forbid_auth_bypass_outside_development doğrulayıcısı
    # bu seçeneği ENVIRONMENT=development dışında zorunlu olarak kapatır.
    auth_bypass: bool = False

    database_url: str = "postgresql+psycopg://formen:formen@localhost:5433/formen_takip"

    # SQLAlchemy connection pool (app/db/session.py) varsayılanlarıyla aynı
    # (pool_size=5, max_overflow=10) — "production optimum değer" iddiası değil,
    # örtük davranışı configurable hale getirir. Gerçek production değeri worker
    # sayısı, PostgreSQL max_connections ve ölçülen yükle doğrulanmalı (bkz. README
    # "DB Connection Pool").
    db_pool_size: int = 5
    db_max_overflow: int = 10
    # Havuzda boş bağlantı yokken yeni bir checkout'un bekleyeceği azami süre (saniye).
    # SQLAlchemy varsayılanıyla aynıdır; aşılırsa TimeoutError fırlatılır.
    db_pool_timeout: int = 30
    # Bu süreden uzun açık kalan bağlantılar sonraki checkout'ta yeniden kurulur.
    # SQLAlchemy varsayılanı sınırsız (-1); 1800sn, proxy/LB'nin sessizce kapattığı
    # bayat bağlantılara karşı ucuz bir güvenlik payı. pool_pre_ping bundan bağımsız.
    db_pool_recycle: int = 1800

    # Red Hat SSO / Keycloak (OIDC) — bkz. README "Authentication Architecture".
    # Backend yalnızca kaynak sunucu (resource server) rolündedir: kendi token'ını
    # üretmez, yalnızca SSO'nun imzaladığı access token'ları doğrular.
    oidc_issuer_url: str | None = None
    oidc_audience: str | None = None
    # JWKS URI genellikle issuer'ın /.well-known/openid-configuration'ından keşfedilir;
    # kurumsal SSO farklı bir yol kullanıyorsa burada override edilebilir.
    oidc_jwks_uri: str | None = None
    # Uygulama içi stabil kimlik ilişkilendirmesi için kullanılacak token claim'i.
    # Kurumun Red Hat SSO konfigürasyonu doğrulandıktan sonra "employee_id" gibi bir
    # claim'e geçirilebilir; varsayılan OIDC standardı "sub"dur.
    oidc_user_id_claim: str = "sub"
    oidc_jwks_cache_seconds: int = 3600

    timezone: str = "Europe/Istanbul"

    cors_origins: list[str] = ["http://localhost:5173"]

    trusted_proxy_ips: str = "127.0.0.1"

    sap_base_url: str | None = None
    sap_client_id: str | None = None
    sap_client_secret: str | None = None

    llm_enabled: bool = False
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 30

    llm_analysis_mode: str = "single_context"
    llm_tool_calling_enabled: bool = True
    llm_demo_tool_calling_enabled: bool = True
    llm_max_tool_calls: int = 10
    llm_max_analysis_steps: int = 12
    llm_tool_timeout_seconds: int = 10
    llm_analysis_timeout_seconds: int = 60
    llm_max_date_range_days: int = 365

    # Formen aylık performans raporu — kalıcı PDF depolama (bkz. app/services/storage).
    # "local" yalnızca yerel geliştirme içindir (backend container filesystem'inde
    # ephemeral bir dizin); production'da report_storage_provider zorunlu olarak "s3"
    # olmalıdır (aşağıdaki _require_report_storage_config_in_production'a bakın).
    report_storage_provider: str = "local"
    aws_region: str | None = None
    reports_s3_bucket: str | None = None
    local_report_storage_dir: str = ".local_reports"

    # CloudFront Signed URL — private S3 origin için browser erişimi. IT/DevOps
    # tarafından sağlanana kadar boş kalır; bu durumda erişim endpoint'i CloudFront
    # yerine backend üzerinden authenticated bir proxy'ye düşer (bkz.
    # app/services/cloudfront_signing.py).
    cloudfront_domain: str | None = None
    cloudfront_key_pair_id: str | None = None
    cloudfront_private_key: str | None = None
    report_signed_url_ttl_seconds: int = 300

    # Kurumsal SMTP — formen aylık raporunun ilgili formene + şefe e-postayla
    # gönderimi için. smtp_enabled=False iken email job'ı hiçbir gönderim denemez,
    # raporları PENDING olarak bırakır (rapor üretimi/erişimi bundan etkilenmez).
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    email_max_retry_count: int = 5
    # Watchdog eşiği (app/services/job_reconciliation.py): Bu süreden uzun SENDING
    # durumunda kalan rapor çökmüş kabul edilir ve RECONCILIATION_REQUIRED durumuna
    # taşınır. SMTP idempotency garantisi vermediğinden otomatik yeniden denenmez;
    # aksi halde gerçek formene/şefe mükerrer e-posta gönderilebilir.
    email_stale_claim_timeout_seconds: int = 900

    # Devam eden bir durumda takılan anomali analiz işleri için watchdog eşiği.
    # llm_analysis_timeout_seconds ve iki structured-output denemesinin toplamından
    # belirgin biçimde uzundur; yavaş çalışanı değil, gerçekten çöken worker'ı yakalar.
    anomaly_stale_claim_timeout_seconds: int = 600

    rate_limit_enabled: bool = True
    rate_limit_default_limit: int = 300
    rate_limit_default_window_seconds: int = 300
    rate_limit_llm_limit: int = 5
    rate_limit_llm_window_seconds: int = 60
    rate_limit_report_limit: int = 10
    rate_limit_report_window_seconds: int = 60
    rate_limit_pdf_limit: int = 20
    rate_limit_pdf_window_seconds: int = 60

    @property
    def llm_available(self) -> bool:
        return self.llm_enabled and bool(self.llm_api_key)

    @property
    def smtp_available(self) -> bool:
        return self.smtp_enabled and bool(self.smtp_host) and bool(self.smtp_from)

    @model_validator(mode="after")
    def _require_oidc_config_in_production(self) -> "Settings":
        if self.environment == "production" and (not self.oidc_issuer_url or not self.oidc_audience):
            raise ValueError(
                "OIDC_ISSUER_URL ve OIDC_AUDIENCE production ortamında zorunludur "
                "(fail-closed: eksik SSO yapılandırmasıyla uygulama başlatılmaz)."
            )
        return self

    @model_validator(mode="after")
    def _forbid_auth_bypass_outside_development(self) -> "Settings":
        if self.auth_bypass and self.environment != "development":
            raise ValueError(
                "AUTH_BYPASS is forbidden outside ENVIRONMENT=development "
                "(fail-closed: startup refused)."
            )
        return self

    @model_validator(mode="after")
    def _forbid_unsafe_production_http_settings(self) -> "Settings":
        if self.environment != "production":
            return self
        if self.debug:
            raise ValueError(
                "DEBUG must be false when ENVIRONMENT=production "
                "(fail-closed: debug responses can expose internal details)."
            )
        if "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' when ENVIRONMENT=production "
                "(fail-closed: configure explicit trusted origins)."
            )
        return self

    @model_validator(mode="after")
    def _validate_db_pool_settings(self) -> "Settings":
        if self.db_pool_size < 1:
            raise ValueError("DB_POOL_SIZE en az 1 olmalıdır.")
        if self.db_max_overflow < 0:
            raise ValueError("DB_MAX_OVERFLOW negatif olamaz.")
        if self.db_pool_timeout < 1:
            raise ValueError("DB_POOL_TIMEOUT en az 1 saniye olmalıdır.")
        if self.db_pool_recycle < -1 or self.db_pool_recycle == 0:
            raise ValueError(
                "DB_POOL_RECYCLE -1 (devre dışı) olmalı veya pozitif saniye sayısı olmalıdır."
            )
        return self

    @model_validator(mode="after")
    def _require_explicit_test_database_when_environment_test(self) -> "Settings":
        # ENVIRONMENT=test, kendi geçici Postgres container'ını hazırlayan entegrasyon
        # testlerine ayrılmıştır (tests/integration/_ephemeral_db.py) ve normal
        # DATABASE_URL kullanılmaz. Gerçek veritabanına yanlışlıkla yıkıcı test
        # çalıştırmamak için adında açık bir "test" işareti olmayan veritabanıyla
        # uygulama başlatılmaz.
        if self.environment == "test" and "test" not in self.database_url.lower():
            raise ValueError(
                "ENVIRONMENT=test requires DATABASE_URL to reference an explicitly "
                "named test database (fail-closed: refusing to start against a "
                "database that isn't clearly marked as a test database)."
            )
        return self

    # report-storage bilerek OIDC'deki gibi constructor-level fail-closed kullanmıyor:
    # OIDC app-wide cross-cutting bir concern ama report storage yalnızca aylık rapor
    # akışını etkiler — AWS provizyonlanmadan tüm backend'i ayağa kaldırmamalı. Fail-closed
    # kontrolü bunun yerine kullanım noktasında yapılır, bkz. app/services/storage/factory.py.


@lru_cache
def get_settings() -> Settings:
    return Settings()
