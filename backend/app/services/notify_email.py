"""Email through a pluggable sender: EMAIL_PROVIDER=smtp (smtplib, STARTTLS on 587, a Gmail app
password) or console (development only: writes the message, including login codes, to the log).
Passwords are never logged; errors keep only the exception type and SMTP status code."""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from html import escape

from ..config import Settings

log = logging.getLogger("frostwatch.email")


class EmailError(RuntimeError):
    pass


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailSender:
    def send(self, msg: OutgoingEmail) -> None:
        raise NotImplementedError


@dataclass
class ConsoleEmailSender(EmailSender):
    """Development only. Keeps an in-memory outbox (used by tests)."""

    outbox: list[OutgoingEmail] = field(default_factory=list)

    def send(self, msg: OutgoingEmail) -> None:
        self.outbox.append(msg)
        log.info("console email to=%s subject=%s\n%s", msg.to, msg.subject, msg.text)


@dataclass
class SmtpEmailSender(EmailSender):
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    sender: str
    smtp_factory: type = smtplib.SMTP
    timeout: float = 20.0

    def send(self, msg: OutgoingEmail) -> None:
        em = EmailMessage()
        em["From"] = self.sender
        em["To"] = msg.to
        em["Subject"] = msg.subject
        em.set_content(msg.text)
        if msg.html:
            em.add_alternative(msg.html, subtype="html")
        try:
            with self.smtp_factory(self.host, self.port, timeout=self.timeout) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(self.user, self.password)
                smtp.send_message(em)
        except smtplib.SMTPResponseException as exc:
            raise EmailError(f"{type(exc).__name__} {exc.smtp_code}") from None
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailError(type(exc).__name__) from None


def get_email_sender(settings: Settings) -> EmailSender:
    if settings.email_provider == "smtp":
        missing = [n for n, v in (("EMAIL_SMTP_HOST", settings.smtp_host), ("EMAIL_SMTP_USER", settings.smtp_user),
                                  ("EMAIL_SMTP_PASSWORD", settings.smtp_password), ("EMAIL_FROM", settings.email_from)) if not v]
        if missing:
            raise RuntimeError(f"EMAIL_PROVIDER=smtp needs {', '.join(missing)}")
        return SmtpEmailSender(settings.smtp_host, settings.smtp_port, settings.smtp_user, settings.smtp_password,
                               settings.email_from)
    if settings.email_provider == "console":
        if settings.is_production:
            raise RuntimeError("EMAIL_PROVIDER=console is for development only")
        return ConsoleEmailSender()
    raise RuntimeError(f"EMAIL_PROVIDER must be 'smtp' or 'console', got {settings.email_provider!r}")


def login_code_email(to: str, code: str, language: str = "es") -> OutgoingEmail:
    if language == "en":
        subject = "Your FrostWatch code"
        text = f"Your FrostWatch code is {code}. It expires in 10 minutes. If you did not ask for it, ignore this email."
    else:
        subject = "Tu código de FrostWatch"
        text = f"Tu código de FrostWatch es {code}. Vence en 10 minutos. Si no lo pediste, ignora este correo."
    return OutgoingEmail(to=to, subject=subject, text=text, html=f"<p>{escape(text)}</p>")


def alert_email(to: str, *, language: str, aoi_name: str, level_label: str, night_date: str, explanation: dict,
                probability_pct: int, cell_name: str, model_version: str, data_source: str, mode: str,
                processed_at: str) -> OutgoingEmail:
    es = language == "es"
    replay = mode == "replay"
    tag = ("[REPLAY] " if replay else "") + ("[MOCK] " if data_source == "MOCK" else "")
    if es:
        subject = f"{tag}Helada: riesgo {level_label} en {aoi_name} (noche del {night_date})"
        lines = [explanation["headline"], "",
                 f"Zona: {aoi_name} (celda {cell_name})", f"Noche: {night_date}",
                 f"Probabilidad: {probability_pct}% (nivel {level_label})", "", explanation["why"], "",
                 "Qué hacer:", *[f"- {a}" for a in explanation["actions"]], "",
                 "Ten en cuenta:", *[f"- {c}" for c in explanation["caveats"]], "",
                 f"Datos de reanálisis: {data_source}. Modelo {model_version}.",
                 f"Calculado al procesar la noche ({processed_at} UTC)."]
        if replay:
            lines.append("Esto es una repetición (replay) de una noche pasada, no un aviso de hoy.")
    else:
        subject = f"{tag}Frost: {level_label} risk at {aoi_name} (night of {night_date})"
        lines = [explanation["headline"], "",
                 f"Area: {aoi_name} (cell {cell_name})", f"Night: {night_date}",
                 f"Probability: {probability_pct}% ({level_label} level)", "", explanation["why"], "",
                 "What to do:", *[f"- {a}" for a in explanation["actions"]], "",
                 "Keep in mind:", *[f"- {c}" for c in explanation["caveats"]], "",
                 f"Reanalysis data: {data_source}. Model {model_version}.",
                 f"Computed when the night was processed ({processed_at} UTC)."]
        if replay:
            lines.append("This is a replay of a past night, not a warning for today.")
    text = "\n".join(lines)
    html = _html(lines)
    return OutgoingEmail(to=to, subject=subject, text=text, html=html)


def _html(lines: list[str]) -> str:
    parts, in_list = [], False
    for line in lines:
        if line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{escape(line[2:])}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        if line:
            parts.append(f"<p>{escape(line)}</p>")
    if in_list:
        parts.append("</ul>")
    return "<html><body>" + "".join(parts) + "</body></html>"
