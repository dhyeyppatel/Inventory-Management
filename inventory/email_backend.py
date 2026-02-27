import ssl
from django.core.mail.backends.smtp import EmailBackend as DefaultEmailBackend

class Python314SMTPBackend(DefaultEmailBackend):
    def open(self):
        if self.connection:
            return False
            
        connection_params = {}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
            
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            
            if self.use_tls:
                self.connection.ehlo()
                context = ssl.create_default_context()
                self.connection.starttls(context=context)
                self.connection.ehlo()
                
            # FIXED: Django uses self.username, not self.user
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise