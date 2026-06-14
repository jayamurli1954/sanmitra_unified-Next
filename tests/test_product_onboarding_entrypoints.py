from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_shared_product_onboarding_script_requires_app_key_and_terms_payload() -> None:
    source = (REPO_ROOT / "frontend" / "shared" / "product-onboarding.js").read_text(encoding="utf-8")

    assert '"X-App-Key": form.dataset.appKey' in source
    assert "terms_accepted" in source
    assert "authority_designation" in source
    assert "/api/v1/onboarding-requests/register" in source
    assert "Contact verification and plan/payment approval" in source


def test_mandir_public_entrypoints_use_mandir_app_key() -> None:
    landing_source = (REPO_ROOT / "frontend" / "mandir-public" / "index.html").read_text(encoding="utf-8")
    onboarding_source = (REPO_ROOT / "frontend" / "mandir-public" / "onboarding.html").read_text(encoding="utf-8")

    assert "./onboarding.html?intent=register" in landing_source
    assert "./onboarding.html?intent=demo" in landing_source
    assert ">Login<" in landing_source
    assert 'data-app-key="mandirmitra"' in onboarding_source
    assert "Designation / Authority" in onboarding_source
    assert "OTP / Verification Channel" in onboarding_source
    assert "terms_accepted" in onboarding_source


def test_mitrabooks_build_publishes_landing_as_folder_index() -> None:
    build_script = (REPO_ROOT / "frontend" / "scripts" / "build.js").read_text(encoding="utf-8")
    vercel_config = (REPO_ROOT / "frontend" / "vercel.json").read_text(encoding="utf-8")
    landing_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "landing.html").read_text(encoding="utf-8")
    onboarding_source = (REPO_ROOT / "frontend" / "mitrabooks-erp" / "onboarding.html").read_text(encoding="utf-8")

    assert "publishMitraBooksLandingIndex" in build_script
    assert "fs.copyFileSync(appShell, loginShell)" in build_script
    assert "fs.copyFileSync(landingShell, appShell)" in build_script
    assert '"/mitrabooks-erp/login"' in vercel_config
    assert '"/mitrabooks-erp/login.html"' in vercel_config
    assert "./login.html" in landing_source
    assert "./login.html" in onboarding_source


def test_gruhamitra_landing_and_service_use_gruha_app_key() -> None:
    landing_source = (REPO_ROOT / "frontend" / "gruhamitra" / "src" / "screens" / "LandingScreen.jsx").read_text(encoding="utf-8")
    onboarding_source = (REPO_ROOT / "frontend" / "gruhamitra" / "src" / "screens" / "SocietyOnboardingScreen.jsx").read_text(encoding="utf-8")
    service_source = (REPO_ROOT / "frontend" / "gruhamitra" / "src" / "services" / "authService.js").read_text(encoding="utf-8")

    assert "/onboard-society?intent=register" in landing_source
    assert "/onboard-society?intent=demo" in landing_source
    assert ">Login<" in landing_source
    assert "Designation / Authority" in onboarding_source
    assert "OTP / Verification Channel" in onboarding_source
    assert "terms_accepted" in onboarding_source
    assert "organization_type: 'HOUSING'" in service_source
    assert "terms_accepted: Boolean(data?.terms_accepted)" in service_source
