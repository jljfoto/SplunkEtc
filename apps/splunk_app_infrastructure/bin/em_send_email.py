# coding=utf-8

import logging
import datetime
import re
import splunk.entity as entity
import splunk.secure_smtplib as secure_smtplib
import splunk.ssl_context as ssl_context
import splunk.clilib.cli_common as comm
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from collections import namedtuple

from splunk.util import normalizeBoolean
from em_abstract_custom_alert_action import AbstractCustomAlertAction

CHARSET = "UTF-8"
EMAIL_DELIM = re.compile('\s*[,;]\s*')
ALERT_SEVERITY = {
    '1': 'INFO',
    '3': 'WARNING',
    '5': 'CRITICAL'
}

EMAIL_BODY_HTML = """\
    <html>
    <head></head>
    <body>
        <div>
            <span>Alert Title :</span>
            <b>{alert_title}</b>
        </div>
        <div>
            <span>Severity :</span>
                <b>{alert_severity} {metric_name} : {current_value}</b>
        </div>
        <div>
            <span>{manage_by_type} triggered this alert:</span>
            <b>{manage_by_value}</b>
        </div>
        <div>
            <span>Time triggered:</span>
            <b>{triggered_time}</b>
        <div>
        <div><a href="{base_url}/app/splunk_app_infrastructure/alerts">Investigate Now</a></div>
    </body>
    </html>
    """

EmailContent = namedtuple('EmailContent', 'sender recipients email')


class EMSendEmailAlertAction(AbstractCustomAlertAction):
    """
    Reads the results from the saved search and sends a custom email based on the configuration.
    """
    ssContent = None

    def getAlertActions(self, sessionKey, namespace=None):
        """
        Fetches the email alert settings
        """
        settings = None
        try:
            settings = entity.getEntity(
                '/configs/conf-alert_actions',
                'email',
                sessionKey=sessionKey, owner="nobody", namespace=namespace)
        except Exception as e:
            logging.error("Could not access or parse email stanza of alert_actions.conf. Error=%s" % str(e))
        return settings

    def make_email_subject(self, result, payload):
        """
        Subject for the email template
        """
        return "[Splunk] %s : %s " % (ALERT_SEVERITY[result.get('current_state')], payload.get('search_name'))

    def make_email_body(self, result, payload):
        """
        Constructs the body of the email template . The body is a html string which is formated with
        the values from the results
        """
        settings = payload.get('configuration')
        trigger_time = None
        if settings:
            trigger_time = datetime.datetime.utcfromtimestamp(
                float(settings.get('trigger_time'))).strftime('%Y-%m-%dT%H:%M:%SZ')

        managed_by_value = ''
        if result.get('managed_by_type') == 'entity':
            managed_by_value = result.get('entity_title')
        else:
            managed_by_value = '%s (%s)' % (result.get('managed_by_id'), result.get('entity_title'))

        body = EMAIL_BODY_HTML.format(alert_title=payload.get('search_name'),
                                      alert_severity=ALERT_SEVERITY[result.get('current_state')],
                                      metric_name=result.get('metric_name'),
                                      current_value=round(float(result.get('current_value', 0)), 2),
                                      manage_by_type=result.get('managed_by_type'),
                                      manage_by_value=managed_by_value,
                                      triggered_time=trigger_time,
                                      base_url=comm.getWebUri())
        return body

    def construct_email(self, result, sender, recipients, payload):
        """
        Constructs the email object with the right MIME type
        """
        email = MIMEMultipart()
        body = self.make_email_body(result, payload)
        email_body = MIMEText(body, 'html')
        email.attach(email_body)
        email['From'] = sender
        email['To'] = ', '.join(recipients)
        email['Subject'] = Header(self.make_email_subject(result, payload), CHARSET)
        return email.as_string()

    def get_email_content(self, result, payload):
        """
        - Returns a Tuble with all info to send email
        """
        sender = 'no-reply@splunk.com'
        settings = payload.get('configuration')
        recipients = [r.strip() for r in settings.get('email_to', '').split(',')]
        email = self.construct_email(result, sender, recipients, payload)
        mail_log_msg = 'Sending email="%s", recipients="%s"' % (
            email,
            recipients
        )
        try:
            return EmailContent(sender=sender, recipients=recipients, email=email)
        except Exception, e:
            logging.error(str(e))
            logging.info(mail_log_msg)

    def _setup_smtp(self, payload):
        """
        Setup smtp to send out a group of emails.
        """
        namespace = payload.get('namespace', 'splunk_app_infrastructure')
        sessionKey = payload.get('session_key')
        self.ssContent = self.ssContent if self.ssContent else self.getAlertActions(sessionKey, namespace)
        use_ssl = normalizeBoolean(self.ssContent.get('use_ssl', False))
        use_tls = normalizeBoolean(self.ssContent.get('use_tls', False))
        server = self.ssContent.get('mailserver', 'localhost')
        username = self.ssContent.get('auth_username', '')
        password = self.ssContent.get('clear_password', '')

        # setup the Open SSL Context
        sslHelper = ssl_context.SSLHelper()
        serverConfJSON = sslHelper.getServerSettings(sessionKey)
        # Pass in settings from alert_actions.conf into context
        ctx = sslHelper.createSSLContextFromSettings(
            sslConfJSON=self.ssContent,
            serverConfJSON=serverConfJSON,
            isClientContext=True)

        # send the mail
        if not use_ssl:
            smtp = secure_smtplib.SecureSMTP(host=server)
        else:
            smtp = secure_smtplib.SecureSMTP_SSL(host=server, sslContext=ctx)
        # smtp.set_debuglevel(1)
        if use_tls:
            smtp.starttls(ctx)
        if len(username) > 0 and len(password) > 0:
            smtp.login(username, password)
        return smtp

    def execute(self, results, payload):
        """
        Loop through the results and send email based on settings.
        """
        if not results:
            return

        settings = payload.get('configuration')
        email_states = [r.strip() for r in settings.get('email_when', '').split(',')]
        mails_to_send = []
        for row in results:
            state_change = row.get('state_change', 'no')
            if state_change != 'no' and state_change in email_states \
                    and row.get('current_state') is not 'None':
                mails_to_send.append(self.get_email_content(row, payload))

        # check if mails need to be send, create smtp and send
        if len(mails_to_send) > 0:
            smtp = self._setup_smtp(payload)
            for item in mails_to_send:
                # in case default recipients are added
                recipients = item.recipients
                if self.ssContent.get('to'):
                    recipients.extend(EMAIL_DELIM.split(self.ssContent.get('to')))
                smtp.sendmail(item.sender, recipients, item.email)
            smtp.quit()

        return results


instance = EMSendEmailAlertAction()

if __name__ == '__main__':
    instance.run()
