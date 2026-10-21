"""
mailer.py - email notifications.

send_email() sends through your SMTP account (settings in backend/.env).
If MAIL_SERVER is empty it does NOT send anything; it prints the email in the
server terminal instead, so you can test the whole flow (and click the link)
before setting up a real mail account.

notify_potential_match() is what tells a lost-item owner "we may have found it".
The email contains only a link: the found item's photo and location are shown
after logging in, never in the email itself.
"""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape


def one_line(text, limit=80):
    """Collapse whitespace/newlines so user text can't break an email header."""
    return " ".join(str(text or "").split())[:limit]


def send_email(app, to, subject, text, html=None):
    """Returns True if sent, False if it was only printed (no MAIL_SERVER)."""
    cfg = app.config
    subject = one_line(subject, 150)

    if not cfg["MAIL_SERVER"]:
        app.logger.info("EMAIL (not sent, MAIL_SERVER is empty)\n  To: %s\n  Subject: %s\n\n%s", to, subject, text)
        return False

    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="foundit")
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    server, port = cfg["MAIL_SERVER"], cfg["MAIL_PORT"]
    context = ssl.create_default_context()
    if port == 465:
        smtp = smtplib.SMTP_SSL(server, port, context=context, timeout=20)
    else:
        smtp = smtplib.SMTP(server, port, timeout=20)
    with smtp:
        if port != 465 and cfg["MAIL_USE_TLS"]:
            smtp.starttls(context=context)
        if cfg["MAIL_USERNAME"]:
            smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
        smtp.send_message(msg)
    return True


def notify_potential_match(app, match):
    """Email the owner of the lost report a link to the Potential Match page."""
    owner = match.lost_report.owner
    item = one_line(match.lost_report.item_name)
    first_name = one_line(owner.name.split()[0] if owner.name.split() else "there", 40)
    link = f"{app.config['APP_BASE_URL']}/potential-match.html?id={match.id}"

    text = (
        f"Hi {first_name},\n\n"
        f'Good news: someone has handed in an item that might be your lost "{item}".\n\n'
        f"Please take a look and tell us whether it's yours:\n{link}\n\n"
        "You'll need to log in with your AUPP email. If it isn't yours, just choose "
        '"This isn\'t my item" and we\'ll keep looking.\n\n'
        "FoundIt - AUPP Campus Lost & Found\n"
    )
    html = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;color:#14213a;line-height:1.5">
  <h2 style="color:#123761;margin-bottom:8px">We may have found your item</h2>
  <p>Hi {escape(first_name)},</p>
  <p>Someone has handed in an item that might be your lost <strong>{escape(item)}</strong>.</p>
  <p><a href="{escape(link)}" style="display:inline-block;background:#123761;color:#ffffff;
     padding:12px 22px;border-radius:8px;text-decoration:none;font-weight:600">Review the possible match</a></p>
  <p style="color:#5b6472;font-size:14px">You'll need to log in with your AUPP email. If it isn't yours,
     choose &ldquo;This isn&rsquo;t my item&rdquo; and we&rsquo;ll keep looking.</p>
  <p style="color:#5b6472;font-size:13px">FoundIt &middot; AUPP Campus Lost &amp; Found</p>
</div>"""

    return send_email(app, owner.email, f"Possible match for your lost {item}", text, html)
