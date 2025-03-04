from flask import Flask, request, jsonify
from sqlalchemy.orm import Session
from database import get_session
from database.models import Sample, Customer
from services.laboratory_information_service import LaboratoryInformationService
from clients.laboratory_information_client import LaboratoryInformationClient
from settings import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    LABORATORY_API_KEY,
    LABORATORY_BASE_URL,
)

app = Flask(__name__)


@app.route("/add-sample", methods=["GET"])
def add_sample():
    """Endpoint to add samples."""
    session: Session = get_session()

    sample_name = request.args.get("sample_name")
    customer_email = request.args.get("customer_email")
    customer_name = request.args.get("customer_name")
    source = request.args.get("source")
    concentration = request.args.get("concentration")

    if "clinic" in customer_name:
        customer_id = int(customer_name.split("clinic")[1])
        samples = session.query(Sample).filter(Sample.customer_id == customer_id).all()
    else:
        samples = session.query(Sample).all()

    laboratory_client = LaboratoryInformationClient(
        api_key=LABORATORY_API_KEY,
        base_url=LABORATORY_BASE_URL,
    )
    email_service = MailService(SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD)
    laboratory_service = LaboratoryInformationService(
        client=laboratory_client,
        mail_service=email_service,
    )

    if sample_name and customer_email and customer_name and source and concentration:
        try:
            customer = (
                session.query(Customer).filter(Customer.email == customer_email).first()
            )
            sample = Sample(
                name=sample_name,
                source=source,
                concentration=concentration,
                customer_name=customer_name,
                customer_id=customer.id,
            )
            laboratory_service.track_sample(sample)
            laboratory_service.set_sample_status(sample, "pending")
            if sample.source == "blood":
                laboratory_service.set_storage_temperaure(sample, 2)
            if sample.source == "tissue":
                laboratory_service.set_storage_temperaure(sample, -20)
            session.add(sample)
            session.commit()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify(samples + [sample]), 201
