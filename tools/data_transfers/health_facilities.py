import logging

from django.apps import apps

import pandas as pd
from django.core.paginator import Paginator
from django.http import HttpResponse

from tools.constants import CONTENT_TYPES, XLSX

logger = logging.getLogger(__name__)

HEADER_CODE = "Code"
HEADER_NAME = "Name"
HEADER_ACCOUNTING_CODE = "Accounting code"
HEADER_EMAIL = "Email"
HEADER_PHONE = "Phone"
HEADER_FAX = "Fax"
HEADER_LEVEL = "Level"
HEADER_ADDRESS = "Address"
HEADER_CARE_TYPE = "Care type"
HEADER_SERVICES_PRICELIST = "Services pricelist"
HEADER_ITEMS_PRICELIST = "Items pricelist"
HEADER_LGA_CODE = "LGA code"
HEADER_LGA_NAME = "LGA name"
HEADER_LEGAL_FORM = "Legal form"

LEVEL_PRIMARY = "Primary"
LEVEL_SECONDARY = "Secondary"
LEVEL_TERTIARY = "Tertiary"

MAPPING_LEVEL_CODE_TO_TEXT = {
    "D": LEVEL_PRIMARY,
    "C": LEVEL_SECONDARY,
    "H": LEVEL_TERTIARY,
}

CARE_TYPE_IN = "In - patient"
CARE_TYPE_OUT = "Out - patient"
CARE_TYPE_BOTH = "In & Out - patient"

MAPPING_CARE_TYPE_CODE_TO_TEXT = {
    "I": CARE_TYPE_IN,
    "O": CARE_TYPE_OUT,
    "B": CARE_TYPE_BOTH,
}


def process_export_health_facilities(user_id):
    logger.info("User (audit id %s) requested export of health facility list XLSX", user_id)
    HealthFacility = apps.get_model('location', 'HealthFacility')
    hfs = (HealthFacility.objects.filter(validity_to__isnull=True)
                                 .prefetch_related("location")
                                 .prefetch_related("legal_form")
                                 .prefetch_related("services_pricelist")
                                 .prefetch_related("items_pricelist")
                                 .order_by("code")
                                 .values("code",
                                         "name",
                                         "acc_code",
                                         "email",
                                         "phone",
                                         "level",
                                         "care_type",
                                         "address",
                                         "fax",
                                         "services_pricelist__name",
                                         "items_pricelist__name",
                                         "location__code",
                                         "location__name",
                                         "legal_form__legal_form"))

    data = []

    for hf in hfs:
        new_data_line = {
            HEADER_CODE: hf["code"],
            HEADER_NAME: hf["name"],
            HEADER_ACCOUNTING_CODE: hf["acc_code"],
            HEADER_LGA_CODE: hf["location__code"],
            HEADER_LGA_NAME: hf["location__name"],
            HEADER_SERVICES_PRICELIST: hf["services_pricelist__name"],
            HEADER_ITEMS_PRICELIST: hf["items_pricelist__name"],
            HEADER_LEVEL: MAPPING_LEVEL_CODE_TO_TEXT.get(hf["level"], "?"),
            HEADER_CARE_TYPE: MAPPING_CARE_TYPE_CODE_TO_TEXT.get(hf["care_type"], "?"),
            HEADER_LEGAL_FORM: hf["legal_form__legal_form"],
            HEADER_EMAIL: hf["email"],
            HEADER_PHONE: hf["phone"],
            HEADER_FAX: hf["fax"],
            HEADER_ADDRESS: hf["address"],
        }
        data.append(new_data_line)

    df = pd.DataFrame(data=data)

    from core import datetime
    now = datetime.datetime.now()
    timestamp = datetime.datetime.strftime(now, "%Y-%m-%d_%H%M%S")
    filename = f"export-health_facilities-{timestamp}.xlsx"
    response = HttpResponse(content_type=CONTENT_TYPES[XLSX])
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response) as writer:
        df.to_excel(writer, index=False)

    return response
