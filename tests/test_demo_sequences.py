from tests.support import drive_text


def test_sos():
    engine = drive_text("SOS")
    assert engine.preview == "SOS"
    assert engine.buffer == ""


def test_hello_123():
    engine = drive_text("HELLO 123")
    assert engine.preview == "HELLO 123"
    assert engine.buffer == ""
