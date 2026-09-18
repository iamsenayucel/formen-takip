
from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta

from app.core import clock
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.enums import Role, ScopeType
from app.models.foreman import Foreman
from app.services.authz_admin import assign_role, revoke_role
from app.services.ingestion import backfill_data_quality_issues, run_ingestion
from app.services.monthly_foreman_report import (
    generate_and_store_report_pdf,
    get_or_generate_monthly_report,
    latest_completed_period,
)
from app.services.job_reconciliation import (
    reconcile_stale_anomaly_jobs,
    reconcile_stale_email_jobs,
    resolve_email_reconciliation,
)
from app.services.monthly_report_email import send_monthly_report_email
from app.services.providers.synthetic_provider import SyntheticDataProvider
from app.services.rescoring import apply_scoring_model_v2
from app.services.synthetic.anomaly_generator import seed_anomalies
from app.services.synthetic.contribution_generator import seed_contribution_works
from app.services.synthetic.production_generator import GenerationParams, seed_production_data
from app.services.synthetic.reference_data import (
    kpis_needing_plant_target_variance,
    load_existing_reference_data,
    regenerate_personnel_identities,
    seed_reference_data,
    validate_plant_kpi_target_coverage,
)

# Sentetik/demo veri üretiminde created_by_subject alanı için kullanılan sabit
# değer — gerçek kullanıcı kimliği artık yalnızca Red Hat SSO tarafından üretilir,
# bu script uygulama içi bir "admin kullanıcı" kavramına ihtiyaç duymaz.
SYNTHETIC_SEED_SUBJECT = "synthetic-seed-script"

# Aynı gerekçeyle: `assign-role`/`revoke-role` CLI komutlarını interaktif çalıştıran
# operatörün OIDC kimliği yoktur (bu bir HTTP request değildir) — audit_logs.subject
# alanında "kim yaptı" sorusunu SYNTHETIC_SEED_SUBJECT'ten ayrıştırılabilir şekilde
# yanıtlamak için ayrı bir sabit kullanılır.
CLI_OPERATOR_SUBJECT = "cli-operator"


def cmd_seed(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    period_end = date.fromisoformat(args.end_date) if args.end_date else clock.today_local()
    period_start = date.fromisoformat(args.start_date) if args.start_date else period_end - timedelta(days=365)

    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models.organization import Plant

        existing = db.scalar(select(Plant).limit(1))
        if existing:
            print(
                "Referans veri zaten mevcut. Seed yalnızca boş veritabanında çalışır; "
                "sentetik veriyi yeniden üretmek için veritabanını sıfırlayın, migration'ları "
                "uygulayın ve seed komutunu tekrar çalıştırın."
            )
            sys.exit(1)

        print(f"[1/3] Referans veri + KPI hedefleri üretiliyor (seed={args.seed})...")
        ref = seed_reference_data(
            db, rng,
            min_plants_per_foreman=args.min_plants_per_foreman,
            max_plants_per_foreman=args.max_plants_per_foreman,
            period_start=period_start,
            period_end=period_end,
        )
        print(
            f"  -> {len(ref.factories)} fabrika, {len(ref.plants)} tesis, {len(ref.chiefs)} şef, "
            f"{len(ref.foremen)} formen, {len(ref.kpis)} KPI oluşturuldu."
        )
        coverage_ok, missing = validate_plant_kpi_target_coverage(db)
        if coverage_ok:
            covered_kpi_count = len(kpis_needing_plant_target_variance(ref.kpis))
            print(f"  -> Tesis x KPI hedef kapsaması doğrulandı ({len(ref.plants)} tesis x {covered_kpi_count} KPI).")
        else:
            print(f"  -> UYARI: {len(missing)} tesis/KPI kombinasyonunda PLANT hedefi eksik: {missing[:10]}")

        print(f"[2/3] Üretim verisi üretiliyor ({period_start} -> {period_end})...")
        params = GenerationParams(
            missing_rate=args.missing_rate,
            error_rate=args.error_rate,
            anomaly_rate=args.anomaly_rate,
            duplicate_rate=args.duplicate_rate,
        )
        production = seed_production_data(db, rng, ref, period_start, period_end, params)
        print(
            f"  -> {len(production.products)} ürün, "
            f"{sum(len(v) for v in production.lines_by_plant.values())} hat, "
            f"{len(production.work_calendar)} çalışma takvimi kaydı, "
            f"{len(production.production_records)} üretim kaydı oluşturuldu."
        )

        print("[3/3] KPI türetme ve ingestion çalıştırılıyor...")
        provider = SyntheticDataProvider(db, rng, duplicate_rate=args.duplicate_rate)
        run = run_ingestion(db, provider, period_start, period_end, plant_codes=[p.code for p in ref.plants])
        print(
            f"  -> İşlenen: {run.processed_count}, başarılı: {run.success_count}, "
            f"atlanan (tekrar): {run.skipped_count}, hatalı: {run.error_count}, durum: {run.status.value}"
        )

        print("[4/5] Katkı ve iyileştirme çalışmaları örnek verisi üretiliyor...")
        contrib = seed_contribution_works(db, rng, SYNTHETIC_SEED_SUBJECT, count=40)
        print(
            f"  -> {contrib.works_created} çalışma oluşturuldu "
            f"({contrib.published_count} yayımlandı, {contrib.draft_count} taslak)."
        )

        print("[5/5] Sentetik ML tespitleri (Tespitler modülü) üretiliyor...")
        anomalies = seed_anomalies(db, rng)
        print(f"  -> {anomalies.anomalies_created} tespit oluşturuldu.")

        _seed_dev_role_assignments(db)
    finally:
        db.close()


_DEV_ROLE_ASSIGNMENTS = (
    # (subject, role) — subject'ler auth bypass sabiti (dev-demo-user) ve
    # keycloak/formen-dev-realm.json'da "id" alanıyla sabitlenmiş 3 demo kullanıcıdır
    # (dev-user, sef-demo-user, formen-demo-user); Keycloak internal user id, token'ın
    # `sub` claim'i olarak kullanıldığından bu id'ler önceden bilinebilir/sabittir.
    ("dev-demo-user", Role.OPERATIONS_MANAGER),
    ("dev-user", Role.OPERATIONS_MANAGER),
    ("sef-demo-user", Role.SUPERVISOR),
    ("formen-demo-user", Role.FOREMAN),
)


def _seed_dev_role_assignments(db) -> None:
    """Yerel geliştirme kimliklerine (auth bypass subject'i + local Keycloak dev realm
    kullanıcıları) otomatik rol + ALL scope atar, böylece taze bir `docker compose up` +
    `seed` sonrası uygulama ek bir manuel `assign-role` adımı gerekmeden üç farklı rolle
    denenebilir. Yalnızca development ortamında çalışır — production seed'i (zaten dolu bir
    DB'de çalışmayı reddeder) bu adımdan etkilenmez."""
    if get_settings().environment != "development":
        return
    print("[dev] Yerel geliştirme kullanıcılarına rol atanıyor (dev-user/dev-demo-user=Operasyon Yöneticisi, sef-demo=Şef, formen-demo=Formen)...")
    for subject, role in _DEV_ROLE_ASSIGNMENTS:
        assign_role(db, subject, role, scope_type=ScopeType.ALL, actor=SYNTHETIC_SEED_SUBJECT)
    db.commit()


_LEVEL_LABEL_EN = {"Kritik": "Critical", "Geliştirilmeli": "Needs Improvement", "Başarılı": "Successful"}
_TARGET_DISTRIBUTION_RANGES = {"Kritik": (25.0, 30.0), "Geliştirilmeli": (35.0, 40.0), "Başarılı": (30.0, 35.0)}
_DISTRIBUTION_TOLERANCE_PP = 3.0


def _print_synthetic_performance_validation(db, period_start: date, period_end: date) -> None:
    import statistics

    from sqlalchemy import select

    from app.schemas.common import Filters
    from app.services import analytics
    from app.services.kpi_engine import resolve_performance_level
    from app.services.level_lookup import get_performance_levels

    filters = Filters(date_from=period_start, date_to=period_end)
    levels = get_performance_levels(db)
    all_scores = analytics.foreman_scores(db, filters)
    scores = [s for s in all_scores if s.is_reliable]

    print("\nSynthetic Performance Validation")
    print(f"\nTotal Foremen: {len(scores)}")
    if not scores:
        print("UYARI: Güvenilir formen puanı bulunamadı, dağılım hesaplanamıyor.")
        return

    n = len(scores)
    counts = {"Kritik": 0, "Geliştirilmeli": 0, "Başarılı": 0}
    for s in scores:
        level = resolve_performance_level(s.total_score, levels)
        counts[level.name] = counts.get(level.name, 0) + 1

    print()
    for name in ("Kritik", "Geliştirilmeli", "Başarılı"):
        c = counts.get(name, 0)
        print(f"{name + ':':<20}{c:>5} ({c / n * 100:5.1f}%)")

    values = sorted(s.total_score for s in scores)
    quantiles = statistics.quantiles(values, n=4) if n >= 4 else [values[0], values[len(values) // 2], values[-1]]
    print("\nScore Statistics")
    print("-" * 20)
    print(f"Min:    {values[0]:.2f}")
    print(f"P25:    {quantiles[0]:.2f}")
    print(f"Median: {statistics.median(values):.2f}")
    print(f"P75:    {quantiles[2]:.2f}")
    print(f"Max:    {values[-1]:.2f}")
    print(f"Mean:   {statistics.mean(values):.2f}")

    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman))}
    ordered = sorted(scores, key=lambda s: s.total_score)
    sample_idxs = sorted(set([0, n // 4, n // 2, (3 * n) // 4, n - 1]))

    print(f"\n{'Foreman':<24}{'Score':>8}   Level")
    print("-" * 46)
    for idx in sample_idxs:
        s = ordered[idx]
        f = foremen_by_id.get(s.key)
        name = f"{f.first_name} {f.last_name}" if f else str(s.key)
        level = resolve_performance_level(s.total_score, levels)
        print(f"{name:<24}{s.total_score:>8.1f}   {_LEVEL_LABEL_EN.get(level.name, level.name)}")

    print()
    all_within_tolerance = True
    for name, (lo, hi) in _TARGET_DISTRIBUTION_RANGES.items():
        pct = counts.get(name, 0) / n * 100
        within_tolerance = (lo - _DISTRIBUTION_TOLERANCE_PP) <= pct <= (hi + _DISTRIBUTION_TOLERANCE_PP)
        all_within_tolerance = all_within_tolerance and within_tolerance
        print(f"{name}: %{pct:.1f} (hedef %{lo:.0f}-{hi:.0f}) -> {'OK' if within_tolerance else 'UYARI'}")

    if all_within_tolerance:
        print("\nDağılım hedeflenen aralıklara uygun.")
    else:
        print(
            "\nUYARI: Dağılım hedeflenen aralıklardan belirgin şekilde sapıyor — "
            "app/services/synthetic/production_generator.py içindeki TIER_SKILL_CENTER/TIER_SKILL_SPREAD "
            "sabitlerinin yeniden kalibre edilmesi gerekebilir."
        )


def cmd_regenerate_synthetic_performance(args: argparse.Namespace) -> None:
    from sqlalchemy import text

    rng = random.Random(args.seed)
    period_end = date.fromisoformat(args.end_date) if args.end_date else clock.today_local()
    period_start = date.fromisoformat(args.start_date) if args.start_date else period_end - timedelta(days=365)

    db = SessionLocal()
    try:
        ref = load_existing_reference_data(db)
        if not ref.plants or not ref.foremen:
            print("Mevcut organizasyon verisi bulunamadı — önce 'seed' komutunu çalıştırın.")
            sys.exit(1)

        print(
            f"[1/4] Mevcut organizasyon yapısı yüklendi: {len(ref.plants)} tesis, {len(ref.foremen)} formen, "
            f"{len(ref.assignments)} atama (organizasyon yapısı değiştirilmeyecek)."
        )

        print("[2/4] Eski sentetik üretim/performans verisi temizleniyor (organizasyon ve KPI tanımları korunuyor)...")
        db.execute(
            text(
                "TRUNCATE performance_scores, performance_records, data_quality_issues, integration_runs, "
                "production_records, foreman_work_calendar, company_calendar, production_lines, products CASCADE"
            )
        )
        db.commit()

        print(f"[3/4] Üretim verisi yeniden üretiliyor ({period_start} -> {period_end}, seed={args.seed})...")
        params = GenerationParams(
            missing_rate=args.missing_rate, error_rate=args.error_rate,
            anomaly_rate=args.anomaly_rate, duplicate_rate=args.duplicate_rate,
        )
        production = seed_production_data(db, rng, ref, period_start, period_end, params)
        print(
            f"  -> {len(production.products)} ürün, "
            f"{sum(len(v) for v in production.lines_by_plant.values())} hat, "
            f"{len(production.work_calendar)} çalışma takvimi kaydı, "
            f"{len(production.production_records)} üretim kaydı oluşturuldu."
        )

        print("[4/4] KPI türetme ve ingestion çalıştırılıyor...")
        provider = SyntheticDataProvider(db, rng, duplicate_rate=args.duplicate_rate)
        run = run_ingestion(db, provider, period_start, period_end, plant_codes=[p.code for p in ref.plants])
        print(
            f"  -> İşlenen: {run.processed_count}, başarılı: {run.success_count}, "
            f"atlanan (tekrar): {run.skipped_count}, hatalı: {run.error_count}, durum: {run.status.value}"
        )

        _print_synthetic_performance_validation(db, period_start, period_end)
    finally:
        db.close()


def cmd_backfill_data_quality(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print("Eksik veri kalitesi kayıtları taranıyor (COMPLETE olmayan ama issue'su bulunmayan kayıtlar)...")
        total = backfill_data_quality_issues(db)
        print(f"  -> {total} yeni data_quality_issues kaydı oluşturuldu.")
    finally:
        db.close()


def cmd_apply_scoring_model_v2(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print("[1/3] AGIR_GITME actual/numerator/denominator yeni (bant bazlı, işaretli) türetimle yeniden hesaplanıyor...")
        result = apply_scoring_model_v2(db)
        ag = result["agir_gitme_actuals"]
        print(f"  -> güncellenen: {ag['updated']}, atlanan: {ag['skipped']}")

        print("[2/3] INKITA (Teknik+İmalat) için geriye dönük ingestion tamamlandı.")
        ik = result["inkita_backfill"]
        print(f"  -> işlenen: {ik['processed']}, başarılı: {ik['success']}, atlanan: {ik['skipped']}, hatalı: {ik['error']}")

        print("[3/3] Tüm performance_scores aktif kurallarla yeniden hesaplandı.")
        rs = result["rescore_all"]
        print(f"  -> güncellenen: {rs['updated']}, atlanan: {rs['skipped']}")
    finally:
        db.close()


def cmd_seed_contributions(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print(f"Katkı ve iyileştirme çalışmaları örnek verisi üretiliyor (seed={args.seed}, count={args.count})...")
        result = seed_contribution_works(db, random.Random(args.seed), SYNTHETIC_SEED_SUBJECT, count=args.count)
        print(
            f"  -> {result.works_created} çalışma oluşturuldu "
            f"({result.published_count} yayımlandı, {result.draft_count} taslak)."
        )
    finally:
        db.close()


def cmd_seed_anomalies(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print(f"Sentetik ML tespitleri üretiliyor (seed={args.seed})...")
        result = seed_anomalies(db, random.Random(args.seed))
        print(f"  -> {result.anomalies_created} tespit oluşturuldu (zaten var olan kodlar atlandı).")
    finally:
        db.close()


def cmd_generate_monthly_reports(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        from sqlalchemy import select

        settings = get_settings()
        if args.year and args.month:
            year, month = args.year, args.month
        else:
            year, month = latest_completed_period()
        print(f"Aylık formen raporları oluşturuluyor ({year}-{month:02d})...")

        foreman_ids = list(db.scalars(select(Foreman.id).where(Foreman.is_active.is_(True))))
        created = 0
        already_existed = 0
        errors = 0
        upload_errors = 0
        for foreman_id in foreman_ids:
            try:
                before = _report_exists(db, foreman_id, year, month)
                report = get_or_generate_monthly_report(db, foreman_id, year, month)
                already_existed += 1 if before else 0
                created += 0 if before else 1
            except ValueError as exc:
                errors += 1
                print(f"  -> {foreman_id}: {exc}")
                continue
            try:
                generate_and_store_report_pdf(db, report, settings)
            except Exception as exc:
                upload_errors += 1
                print(f"  -> {foreman_id}: PDF/S3 upload başarısız: {exc}")
        print(
            f"  -> oluşturulan: {created}, zaten mevcut: {already_existed}, hata: {errors}, "
            f"PDF/upload hatası: {upload_errors}"
        )
    finally:
        db.close()


def cmd_send_monthly_report_emails(args: argparse.Namespace) -> None:
    from sqlalchemy import select

    from app.models.enums import ReportEmailStatus
    from app.models.foreman_report import ForemanMonthlyReport

    settings = get_settings()
    if not settings.smtp_available:
        print("Aylık formen rapor e-postaları gönderimi atlandı: SMTP yapılandırılmamış "
              "(SMTP_ENABLED/SMTP_HOST/SMTP_FROM) — hiçbir gönderim denenmedi, raporlar PENDING "
              "durumunda kaldı, retry sayaçları değişmedi.")
        return

    db = SessionLocal()
    try:
        if args.year and args.month:
            year, month = args.year, args.month
        else:
            year, month = latest_completed_period()

        statuses = [ReportEmailStatus.PENDING]
        if args.retry_failed:
            statuses.append(ReportEmailStatus.FAILED)

        reports = list(
            db.scalars(
                select(ForemanMonthlyReport).where(
                    ForemanMonthlyReport.year == year,
                    ForemanMonthlyReport.month == month,
                    ForemanMonthlyReport.email_status.in_(statuses),
                )
            )
        )
        print(f"Aylık formen rapor e-postaları gönderiliyor ({year}-{month:02d}, {len(reports)} aday)...")

        sent = skipped = failed = retry_exhausted = 0
        for report in reports:
            if args.retry_failed and report.email_retry_count >= settings.email_max_retry_count:
                retry_exhausted += 1
                continue
            send_monthly_report_email(db, report, settings)
            if report.email_status == ReportEmailStatus.SENT:
                sent += 1
            elif report.email_status == ReportEmailStatus.SKIPPED:
                skipped += 1
            else:
                failed += 1
        print(
            f"  -> gönderildi: {sent}, atlandı (veri yetersiz): {skipped}, başarısız: {failed}, "
            f"deneme limiti aşıldı: {retry_exhausted}"
        )
    finally:
        db.close()


def cmd_reconcile_stale_jobs(args: argparse.Namespace) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        print(
            f"E-posta job'ları taranıyor (SENDING > {settings.email_stale_claim_timeout_seconds}s claimed_at)..."
        )
        email_result = reconcile_stale_email_jobs(db, settings)
        print(
            f"  -> {email_result.scanned_candidates} aday, {len(email_result.recovered_ids)} tanesi "
            "RECONCILIATION_REQUIRED durumuna alındı (otomatik yeniden gönderim YAPILMAZ — bkz. README "
            "'Job Claiming & Concurrency'). Çözmek için: resolve-stale-email-job --report-id <id> "
            "--resolution sent|retry"
        )

        print(
            f"Tespit analiz job'ları taranıyor (in-progress > {settings.anomaly_stale_claim_timeout_seconds}s "
            "started_at)..."
        )
        anomaly_result = reconcile_stale_anomaly_jobs(db, settings)
        print(
            f"  -> {anomaly_result.scanned_candidates} aday, {len(anomaly_result.recovered_ids)} tanesi "
            "FAILED durumuna alındı (ilgili tespit için 'Yeniden Analiz Et' ile manuel tekrar denenebilir)."
        )
    finally:
        db.close()


def cmd_resolve_stale_email_job(args: argparse.Namespace) -> None:
    import uuid as uuid_module

    db = SessionLocal()
    try:
        report = resolve_email_reconciliation(db, uuid_module.UUID(args.report_id), args.resolution)
        print(f"  -> report_id={report.id} email_status={report.email_status.value}")
    except ValueError as exc:
        print(f"Hata: {exc}")
        sys.exit(1)
    finally:
        db.close()


def _report_exists(db, foreman_id, year: int, month: int) -> bool:
    from sqlalchemy import select

    from app.models.foreman_report import ForemanMonthlyReport

    return db.scalar(
        select(ForemanMonthlyReport.id).where(
            ForemanMonthlyReport.foreman_id == foreman_id,
            ForemanMonthlyReport.year == year,
            ForemanMonthlyReport.month == month,
        )
    ) is not None


def cmd_backfill_contribution_scores(args: argparse.Namespace) -> None:
    from sqlalchemy import select

    from app.models.contribution import ContributionGain, ContributionWork
    from app.services import contribution_calc as calc

    db = SessionLocal()
    try:
        print("Katkı puanı eksik/ güncel olmayan çalışmalar yeniden hesaplanıyor...")
        works = list(db.scalars(select(ContributionWork)))
        updated = 0
        for work in works:
            gains = list(db.scalars(select(ContributionGain).where(ContributionGain.work_id == work.id)))
            work.contribution_score = calc.compute_contribution_score(work, gains)[0]
            updated += 1
        db.commit()
        print(f"  -> {updated} çalışma güncellendi.")
    finally:
        db.close()


def cmd_assign_role(args: argparse.Namespace) -> None:
    import uuid as uuid_module

    role = Role(args.role)
    scope_type = ScopeType(args.scope_type)
    factory_id = uuid_module.UUID(args.factory_id) if args.factory_id else None
    plant_ids = [uuid_module.UUID(p) for p in args.plant_id] if args.plant_id else None

    db = SessionLocal()
    try:
        try:
            assign_role(
                db, args.subject, role, scope_type=scope_type, factory_id=factory_id, plant_ids=plant_ids,
                actor=CLI_OPERATOR_SUBJECT,
            )
        except ValueError as exc:
            print(f"Hata: {exc}")
            sys.exit(1)
        db.commit()
        scope_desc = {
            "ALL": "tüm organizasyon",
            "FACTORY": f"fabrika {factory_id}",
            "PLANT": f"{len(plant_ids or [])} tesis",
        }[scope_type.value]
        print(f"  -> {args.subject}: rol={role.value}, scope={scope_desc}")
    finally:
        db.close()


def cmd_revoke_role(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        had_assignment = revoke_role(db, args.subject, actor=CLI_OPERATOR_SUBJECT)
        db.commit()
        if had_assignment:
            print(f"  -> {args.subject}: rol/scope ataması kaldırıldı (artık her yerde 403 alır).")
        else:
            print(f"  -> {args.subject}: zaten bir rol ataması yoktu (no-op, yine de audit'e yazıldı).")
    finally:
        db.close()


def cmd_regenerate_personnel(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        print("Şef/formen ad-soyad ve sicil numaraları yeniden üretiliyor (performans verisine dokunulmaz)...")
        chiefs, foremen = regenerate_personnel_identities(db, random.Random(args.seed))
        print(f"  -> {chiefs} şef, {foremen} formen güncellendi.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    seed_parser = sub.add_parser("seed", help="Organizasyon + sentetik performans verisi üretir")
    seed_parser.add_argument("--seed", type=int, default=42)
    seed_parser.add_argument("--min-plants-per-foreman", type=int, default=2)
    seed_parser.add_argument("--max-plants-per-foreman", type=int, default=4)
    seed_parser.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD")
    seed_parser.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD")
    seed_parser.add_argument("--missing-rate", type=float, default=0.02)
    seed_parser.add_argument("--error-rate", type=float, default=0.01)
    seed_parser.add_argument("--anomaly-rate", type=float, default=0.015)
    seed_parser.add_argument("--duplicate-rate", type=float, default=0.005)
    seed_parser.set_defaults(func=cmd_seed)

    regen_parser = sub.add_parser(
        "regenerate-personnel-identities",
        help="Var olan şef/formen kayıtlarının ad-soyad ve sicil numaralarını benzersiz olacak şekilde yeniden üretir",
    )
    regen_parser.add_argument("--seed", type=int, default=42)
    regen_parser.set_defaults(func=cmd_regenerate_personnel)

    regen_perf_parser = sub.add_parser(
        "regenerate-synthetic-performance",
        help="Mevcut organizasyon yapısını (fabrika/tesis/şef/formen/atama) ve KPI tanımlarını koruyarak yalnızca "
        "sentetik üretim/performans verisini daha dengeli bir Kritik/Geliştirilmeli/Başarılı dağılımıyla yeniden "
        "üretir; sonunda dağılım doğrulama raporu basar",
    )
    regen_perf_parser.add_argument("--seed", type=int, default=42)
    regen_perf_parser.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD")
    regen_perf_parser.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD")
    regen_perf_parser.add_argument("--missing-rate", type=float, default=0.02)
    regen_perf_parser.add_argument("--error-rate", type=float, default=0.01)
    regen_perf_parser.add_argument("--anomaly-rate", type=float, default=0.015)
    regen_perf_parser.add_argument("--duplicate-rate", type=float, default=0.005)
    regen_perf_parser.set_defaults(func=cmd_regenerate_synthetic_performance)

    backfill_parser = sub.add_parser(
        "backfill-data-quality-issues", help="Faz 1'de üretilmiş kayıtlar için geriye dönük veri kalitesi sorunu kayıtları oluşturur"
    )
    backfill_parser.set_defaults(func=cmd_backfill_data_quality)

    scoring_v2_parser = sub.add_parser(
        "apply-scoring-model-v2",
        help="Mevcut performans verisini KPI'a özel yeni puanlama formülleriyle yeniden hesaplar "
        "(AGIR_GITME işaretli türetim düzeltmesi + INKITA geriye dönük ingestion + tüm skorların yeniden hesaplanması)",
    )
    scoring_v2_parser.set_defaults(func=cmd_apply_scoring_model_v2)

    contrib_parser = sub.add_parser(
        "seed-contributions",
        help="Var olan tesis/formen verisine dayalı katkı ve iyileştirme çalışması örnekleri üretir "
        "(tam yeniden seed gerekmeden mevcut veritabanına eklenebilir)",
    )
    contrib_parser.add_argument("--seed", type=int, default=42)
    contrib_parser.add_argument("--count", type=int, default=40)
    contrib_parser.set_defaults(func=cmd_seed_contributions)

    anomalies_parser = sub.add_parser(
        "seed-anomalies",
        help="Tespitler modülü için sabit senaryo kataloğundan sentetik ML tespitleri üretir "
        "(zaten var olan tespit kodları atlanır, tekrar çalıştırmak güvenlidir)",
    )
    anomalies_parser.add_argument("--seed", type=int, default=42)
    anomalies_parser.set_defaults(func=cmd_seed_anomalies)

    monthly_reports_parser = sub.add_parser(
        "generate-monthly-reports",
        help="Aktif her formen için aylık bireysel değerlendirme raporu üretir (idempotent — "
        "zaten oluşturulmuş formen+ay kombinasyonları atlanır); --year/--month verilmezse en son "
        "tamamlanmış ay kullanılır",
    )
    monthly_reports_parser.add_argument("--year", type=int, default=None)
    monthly_reports_parser.add_argument("--month", type=int, default=None)
    monthly_reports_parser.set_defaults(func=cmd_generate_monthly_reports)

    send_emails_parser = sub.add_parser(
        "send-monthly-report-emails",
        help="Üretilmiş aylık formen raporlarını PDF eki ile ilgili formene (TO) ve şefine (CC) e-postayla "
        "gönderir — rapor üretiminden bağımsız, ayrı bir adımdır; --year/--month verilmezse en son "
        "tamamlanmış ay kullanılır. SENT durumundaki raporlar normalde tekrar gönderilmez.",
    )
    send_emails_parser.add_argument("--year", type=int, default=None)
    send_emails_parser.add_argument("--month", type=int, default=None)
    send_emails_parser.add_argument(
        "--retry-failed", action="store_true",
        help="PENDING'e ek olarak, email_retry_count < EMAIL_MAX_RETRY_COUNT olan FAILED raporları da tekrar dener",
    )
    send_emails_parser.set_defaults(func=cmd_send_monthly_report_emails)

    reconcile_parser = sub.add_parser(
        "reconcile-stale-jobs",
        help="Watchdog: claimed (SENDING/in-progress) süresi timeout'u aşan e-posta ve tespit analiz "
        "job'larını tarar. E-posta job'ları asla otomatik yeniden gönderilmez (duplicate mail riski) — "
        "RECONCILIATION_REQUIRED durumuna alınır ve 'resolve-stale-email-job' ile manuel çözülür. Tespit "
        "analiz job'ları FAILED yapılır (manuel 'Yeniden Analiz Et' ile tekrar denenebilir). Cron/scheduler "
        "ile periyodik çalıştırılması önerilir.",
    )
    reconcile_parser.set_defaults(func=cmd_reconcile_stale_jobs)

    resolve_email_parser = sub.add_parser(
        "resolve-stale-email-job",
        help="RECONCILIATION_REQUIRED durumundaki bir aylık rapor e-postasını operatör kararıyla çözer: "
        "'sent' (SMTP/relay loglarından gerçekten gönderildiği doğrulandı, SENT olarak işaretlenir, bir "
        "daha denenmez) veya 'retry' (gönderilmediği doğrulandı, PENDING'e alınır, bir sonraki "
        "send-monthly-report-emails çalıştırmasında tekrar denenir).",
    )
    resolve_email_parser.add_argument("--report-id", required=True, help="foreman_monthly_reports.id (UUID)")
    resolve_email_parser.add_argument("--resolution", required=True, choices=["sent", "retry"])
    resolve_email_parser.set_defaults(func=cmd_resolve_stale_email_job)

    assign_role_parser = sub.add_parser(
        "assign-role",
        help="Bir OIDC subject'e rol + veri erişim kapsamı (scope) atar (idempotent — tekrar "
        "çalıştırıldığında önceki atamanın yerine geçer, birikmez)",
    )
    assign_role_parser.add_argument("subject", help="OIDC subject (ör. Keycloak 'sub' claim'i)")
    assign_role_parser.add_argument(
        "role", choices=[r.value for r in Role], help="FOREMAN | SUPERVISOR | OPERATIONS_MANAGER"
    )
    assign_role_parser.add_argument(
        "--scope-type", choices=[s.value for s in ScopeType], default="ALL", help="ALL | FACTORY | PLANT"
    )
    assign_role_parser.add_argument("--factory-id", default=None, help="scope-type=FACTORY için zorunlu (UUID)")
    assign_role_parser.add_argument(
        "--plant-id", action="append", default=None,
        help="scope-type=PLANT için zorunlu, birden çok kez verilebilir (--plant-id X --plant-id Y)",
    )
    assign_role_parser.set_defaults(func=cmd_assign_role)

    revoke_role_parser = sub.add_parser(
        "revoke-role",
        help="Bir OIDC subject'in rol + scope atamasını tamamen kaldırır (idempotent) — "
        "subject artık her permission kontrolünde default-deny ile 403 alır",
    )
    revoke_role_parser.add_argument("subject", help="OIDC subject (ör. Keycloak 'sub' claim'i)")
    revoke_role_parser.set_defaults(func=cmd_revoke_role)

    backfill_scores_parser = sub.add_parser(
        "backfill-contribution-scores",
        help="Var olan tüm katkı çalışmalarının sistem tarafından hesaplanan 1-5 katkı puanını yeniden hesaplar "
        "(puanlama kriterleri değiştiğinde veya eski kayıtlarda puan eksikse kullanılır)",
    )
    backfill_scores_parser.set_defaults(func=cmd_backfill_contribution_scores)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
