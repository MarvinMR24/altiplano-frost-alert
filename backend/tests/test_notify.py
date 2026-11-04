import json
import smtplib
from typing import ClassVar

import httpx
import pytest

from app.services.notify_email import EmailError, SmtpEmailSender, alert_email
from app.services.notify_push import send_push


class FakeSMTP:
    instances: ClassVar[list] = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.calls, self.sent = host, port, [], []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user))
        if password == "wrong":
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    def send_message(self, msg):
        self.sent.append(msg)


def _alert(**kw):
    return alert_email("to@example.com", language="es", aoi_name="Chacra", level_label="alto", night_date="2018-07-15",
                       explanation={"headline": "H", "why": "W", "actions": ["A1"], "caveats": ["C1"]},
                       probability_pct=62, cell_name="Oruro", model_version="m1",
                       data_source="ERA5-Land reanalysis (Copernicus CDS)", mode="replay",
                       processed_at="2026-11-03T10:00:00", **kw)


def test_alert_email_content():
    msg = _alert()
    assert "alto" in msg.subject and "Chacra" in msg.subject and "2018-07-15" in msg.subject
    assert msg.subject.startswith("[REPLAY]")
    assert "reanálisis" in msg.text and "replay" in msg.text.lower() and "<li>A1</li>" in msg.html
    assert "tiempo real" not in msg.text.lower()


def test_smtp_starttls_login_and_multipart():
    FakeSMTP.instances.clear()
    sender = SmtpEmailSender("smtp.example.com", 587, "bot@example.com", "app-password", "bot@example.com",
                             smtp_factory=FakeSMTP)
    sender.send(_alert())
    smtp = FakeSMTP.instances[-1]
    assert (smtp.host, smtp.port) == ("smtp.example.com", 587)
    assert smtp.calls.index("starttls") < smtp.calls.index(("login", "bot@example.com"))
    msg = smtp.sent[0]
    assert msg.is_multipart() and {p.get_content_type() for p in msg.iter_parts()} == {"text/plain", "text/html"}


def test_smtp_error_has_no_secret():
    sender = SmtpEmailSender("smtp.example.com", 587, "bot@example.com", "wrong", "bot@example.com", smtp_factory=FakeSMTP)
    with pytest.raises(EmailError) as err:
        sender.send(_alert())
    assert "535" in str(err.value) and "wrong" not in str(err.value) and "bot@" not in str(err.value)
    assert "wrong" not in repr(sender)


def test_push_batches_filters_and_tickets():
    requests = []

    def handler(request):
        msgs = json.loads(request.content)
        requests.append(msgs)
        data = []
        for m in msgs:
            if m["to"].endswith("bad]"):
                data.append({"status": "error", "message": f"{m['to']} is not registered",
                             "details": {"error": "DeviceNotRegistered"}})
            else:
                data.append({"status": "ok", "id": "ticket-" + m["to"][-4:-1]})
        return httpx.Response(200, json={"data": data})

    tokens = [f"ExponentPushToken[t{i:03d}]" for i in range(249)] + ["ExponentPushToken[bad]", "not-a-token"]
    results = send_push(tokens, title="T", body="B", data={"alert_id": "a1"}, url="https://exp.host/--/api/v2/push/send",
                        client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert [len(r) for r in requests] == [100, 100, 50]
    assert all(m["data"] == {"alert_id": "a1"} for batch in requests for m in batch)
    by = {r.token: r for r in results}
    assert by["not-a-token"].status == "skipped"
    assert by["ExponentPushToken[bad]"].error == "DeviceNotRegistered"
    assert by["ExponentPushToken[t007]"].ticket_id == "ticket-007"
    assert sum(r.status == "sent" for r in results) == 249


def test_push_http_error_is_recorded():
    def handler(request):
        return httpx.Response(500)

    res = send_push(["ExponentPushToken[x]"], title="T", body="B", data={}, url="https://exp.host/x",
                    client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert res[0].status == "error" and res[0].error.startswith("request_failed")
