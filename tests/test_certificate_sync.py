from app.services.certificate_sync import _certificate_url


def test_certificate_url_builds_expected_pattern():
    url = _certificate_url("sampleuser", "responsive-web-design")
    assert url == "https://www.freecodecamp.org/certification/sampleuser/responsive-web-design"
