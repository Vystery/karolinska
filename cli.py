from pathlib import Path

import click
import logging

from database import get_session
from database.models import Sample, File
from services.mail_service import MailService
from settings import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SAMPLE_FILE_FOLDER
from sqlalchemy.orm import Session

LOG = logging.getLogger(__name__)


@click.command("delete-sample")
@click.argument("id")
def delete_sample(id: str):
    """CLI function used to delete samples and any files associated."""
    session: Session = get_session()
    samples: list[Sample] = session.query(Sample).all()
    for sample in samples:
        if id in [sample.id, sample.name, sample.alias]:
            SampleDeleter().delete_sample(sample)
            LOG.warning(f"Deleted sample: {sample}")
    session.commit()


class SampleDeleter:
    """Class performing all actions necessary to delete a given sample"""
    def __init__(self):
        self.session: Session = get_session()
        self.mail_service = MailService(SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)

    def delete_sample(self, sample: Sample):
        self.session.delete(sample)
        self.session.commit()
        self.delete_associated_files(sample)
        self.notify_customer(sample)

    def delete_associated_files(self, sample: Sample):
        files_associated_to_given_sample = list(Path(SAMPLE_FILE_FOLDER, sample.name).iterdir())
        for file_associated_to_given_sample in files_associated_to_given_sample:
            file_associated_to_given_sample.unlink()

    def notify_customer(self, sample):
        customer_email = sample.customer.email
        body = (f"Dear {sample.customer.name}.\nSample {sample} has been manually deleted from our database along with "
                f"all associated files.\nBest regards,\nDNAServicesAB")
        self.mail_service.send_email(from_addr="order@DNAServicesAB.se", to_addrs=customer_email,
                                     subject="Sample Deletion", body=body)
