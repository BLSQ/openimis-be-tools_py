import logging

from django.apps import apps

import pandas as pd
from django.http import HttpResponse, JsonResponse

from tools.constants import CONTENT_TYPES, XLSX
from tools.utils import convert_pandas_empty_values_to_none

logger = logging.getLogger(__name__)

HEADER_NIN = "NIN"
HEADER_NO_LONGER_FORMAL_SECTOR = "Not formal sector"


def process_export_formal_sector(user_id):
    logger.info("User (audit id %s) requested export of formal sector list XLSX", user_id)
    Insuree = apps.get_model('insuree', 'Insuree')
    fs_insurees = (Insuree.objects.filter(validity_to__isnull=True,
                                          is_formal_sector=True)
                                  .values("chf_id"))

    data = []
    for fs_insuree in fs_insurees:
        new_data_line = {
            HEADER_NIN: fs_insuree["chf_id"],
            HEADER_NO_LONGER_FORMAL_SECTOR: None,
        }
        data.append(new_data_line)

    df = pd.DataFrame(data=data)

    from core import datetime
    now = datetime.datetime.now()
    timestamp = datetime.datetime.strftime(now, "%Y-%m-%d_%H%M%S")
    filename = f"export-formal_sector-{timestamp}.xlsx"
    response = HttpResponse(content_type=CONTENT_TYPES[XLSX])
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response) as writer:
        df.to_excel(writer, index=False)

    return response


def process_import_formal_sector(file, user_id):
    column_mapping = {
        HEADER_NIN: int,
        HEADER_NO_LONGER_FORMAL_SECTOR: convert_pandas_empty_values_to_none
    }
    df = pd.read_excel(file, engine='openpyxl', converters=column_mapping)
    new_column_names = {
        HEADER_NIN: "nin",
        HEADER_NO_LONGER_FORMAL_SECTOR: "delete",
    }
    df.rename(columns=new_column_names, inplace=True)

    errors = []
    total_sent = 0
    updated = 0
    skipped = 0
    Insuree = apps.get_model("insuree", "Insuree")

    for index, row in df.iterrows():
        total_sent += 1
        logger.info("Processing row %s", index + 2)
        nin = row["nin"]
        remove_fs_status = row["delete"]

        insuree = (Insuree.objects.filter(validity_to__isnull=True,
                                          chf_id=nin)
                                  .first())
        if not insuree:
            error_message = f"Error line {index + 2} - unknown NIN {nin}"
            logger.error(error_message)
            errors.append(error_message)
            continue

        if not insuree.is_formal_sector:
            if remove_fs_status:
                error_message = f"Error line {index + 2} - NIN {nin} was not formal sector, its status cannot be removed"
                logger.error(error_message)
                errors.append(error_message)
                continue

            logger.info(f"Updating {nin} - it is now formal sector")
            update_insuree_formal_sector_status(insuree, True, user_id)
            updated += 1
        else:
            if remove_fs_status:
                logger.info(f"Updating {nin} - it is no longer formal sector")
                update_insuree_formal_sector_status(insuree, False, user_id)
                updated += 1
                continue

            logger.info(f"Skipping {nin} - it is already formal sector and the status should not be removed")
            skipped += 1

    success = len(errors) != total_sent
    response_data = {
        "data": {
            "sent": total_sent,
            "failed": len(errors),
            "updated": updated,
            "skipped": skipped,
        },
        "success": success,
        "errors": errors,
    }
    return JsonResponse(data=response_data, status=200)


def update_insuree_formal_sector_status(insuree, new_status, audit_user_id):
    insuree.save_history()
    from core import datetime
    now = datetime.datetime.now()
    insuree.validity_from = now
    insuree.is_formal_sector = new_status
    insuree.audit_user_id = audit_user_id
    insuree.save()
