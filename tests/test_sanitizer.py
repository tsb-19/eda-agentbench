"""Unit tests for log sanitizer."""

from eda_agentbench.sanitizer.log_sanitizer import LogSanitizer


def test_sanitize_user_home():
    s = LogSanitizer()
    result = s.sanitize("Error in /home/tsb/project/file.v")
    assert "/home/tsb" not in result
    assert "<USER_HOME>" in result


def test_sanitize_license_server():
    s = LogSanitizer()
    result = s.sanitize("Checkout: 27000@b01-server")
    assert "27000@b01-server" not in result
    assert "<LICENSE_SERVER>" in result


def test_sanitize_eda_root():
    s = LogSanitizer()
    result = s.sanitize("Using /EDA/soft2/synopsys/vcs/S-2021.09-SP1/amd64/bin/vcs")
    assert "/EDA/soft2/synopsys" not in result
    assert "<EDA_ROOT>" in result


def test_sanitize_ip_address():
    s = LogSanitizer()
    result = s.sanitize("Server at 192.168.1.100 responding")
    assert "192.168.1.100" not in result
    assert "<IP_ADDR>" in result


def test_sanitize_multiple_rules():
    s = LogSanitizer()
    text = "User /home/tsb ran /EDA/soft2/synopsys/vcs/bin/vcs on 10.0.0.1"
    result = s.sanitize(text)
    assert "/home/tsb" not in result
    assert "/EDA/soft2/synopsys" not in result
    assert "10.0.0.1" not in result


def test_sanitize_file(tmp_path):
    s = LogSanitizer()
    input_f = tmp_path / "raw.log"
    output_f = tmp_path / "clean.log"
    input_f.write_text("User: /home/tsb\nLicense: 27000@b01\n")
    s.sanitize_file(input_f, output_f)
    content = output_f.read_text()
    assert "/home/tsb" not in content
    assert "27000@b01" not in content
    assert "<USER_HOME>" in content
    assert "<LICENSE_SERVER>" in content
