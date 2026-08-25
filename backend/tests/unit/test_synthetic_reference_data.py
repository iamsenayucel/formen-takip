from dataclasses import dataclass

from app.services.synthetic.reference_data import kpis_needing_plant_target_variance


@dataclass
class _FakeKpi:
    code: str


_SIX_KPIS = [_FakeKpi(c) for c in ("AGIR_GITME", "GSF", "ISKARTA", "INKITA", "PLANA_UYUM", "OEE")]


class TestKpisNeedingPlantTargetVariance:
    def test_oee_is_excluded(self):
        codes = [k.code for k in kpis_needing_plant_target_variance(_SIX_KPIS)]
        assert "OEE" not in codes

    def test_other_five_kpis_are_kept_in_order(self):
        codes = [k.code for k in kpis_needing_plant_target_variance(_SIX_KPIS)]
        assert codes == ["AGIR_GITME", "GSF", "ISKARTA", "INKITA", "PLANA_UYUM"]

    def test_count_matches_pre_oee_kpi_count(self):
        assert len(kpis_needing_plant_target_variance(_SIX_KPIS)) == 5
