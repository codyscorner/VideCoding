from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QLabel,
)

from . import config as cfg


class SettingsDialog(QDialog):
    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("S3 Browser Settings")
        self.setMinimumWidth(420)

        self.profile_edit = QLineEdit(current_config.get("profile_name", "runpod-s3"))
        self.region_edit = QLineEdit(current_config.get("region", ""))
        self.endpoint_edit = QLineEdit(current_config.get("endpoint_url", ""))
        self.bucket_edit = QLineEdit(current_config.get("bucket_name", ""))

        self.access_key_edit = QLineEdit()
        self.access_key_edit.setPlaceholderText("Leave blank to keep existing credentials")
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_key_edit.setPlaceholderText("Leave blank to keep existing credentials")

        form = QFormLayout()
        form.addRow("Profile name:", self.profile_edit)
        form.addRow("Region:", self.region_edit)
        form.addRow("Endpoint URL:", self.endpoint_edit)
        form.addRow("Bucket name:", self.bucket_edit)

        cred_note = QLabel(
            "Credentials are stored in your local AWS credentials file, never in this app's config."
            + chr(10)
            + f"Settings file: {cfg.CONFIG_PATH}"
        )
        cred_note.setWordWrap(True)
        cred_note.setStyleSheet("color: gray; font-size: 11px;")

        form.addRow(QLabel("<b>Credentials (optional update)</b>"))
        form.addRow("Access Key ID:", self.access_key_edit)
        form.addRow("Secret Access Key:", self.secret_key_edit)
        form.addRow(cred_note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.result_config: dict | None = None

    def _on_accept(self):
        profile = self.profile_edit.text().strip()
        region = self.region_edit.text().strip()
        endpoint = self.endpoint_edit.text().strip()
        bucket = self.bucket_edit.text().strip()

        if not all([profile, region, endpoint, bucket]):
            QMessageBox.warning(self, "Missing fields", "All connection fields are required.")
            return

        access_key = self.access_key_edit.text().strip()
        secret_key = self.secret_key_edit.text().strip()
        if access_key or secret_key:
            if not (access_key and secret_key):
                QMessageBox.warning(
                    self, "Incomplete credentials", "Provide both Access Key ID and Secret Access Key."
                )
                return
            cfg.save_aws_credentials(profile, access_key, secret_key)

        cfg.save_aws_config(profile, region)

        self.result_config = {
            "profile_name": profile,
            "region": region,
            "endpoint_url": endpoint,
            "bucket_name": bucket,
        }
        cfg.save_config(self.result_config)
        self.accept()
