import logging

from django.apps import apps
from django.db.models import F

import pandas as pd
from django.http import HttpResponse, JsonResponse

from autoenroll.services import autoenroll_family
from tools.constants import CONTENT_TYPES, XLSX

logger = logging.getLogger(__name__)

HEADER_NIN = "NIN"
HEADER_NO_LONGER_INDIGENT = "No longer indigent"


def process_export_indigents(user_id):
    logger.info("User (audit id %s) requested export of ingident list XLSX", user_id)
    Family = apps.get_model('insuree', 'Family')
    indigents = (Family.objects.filter(validity_to__isnull=True,
                                       poverty=True)
                               .values(chf_id=F("head_insuree__chf_id")))

    data = []
    for indigent in indigents:
        new_data_line = {
            HEADER_NIN: indigent["chf_id"],
            HEADER_NO_LONGER_INDIGENT: None,
        }
        data.append(new_data_line)

    df = pd.DataFrame(data=data)

    from core import datetime
    now = datetime.datetime.now()
    timestamp = datetime.datetime.strftime(now, "%Y-%m-%d_%H%M%S")
    filename = f"export-indigents-{timestamp}.xlsx"
    response = HttpResponse(content_type=CONTENT_TYPES[XLSX])
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response) as writer:
        df.to_excel(writer, index=False)

    return response


def _convert_empty_values_to_none(value):
    if pd.isna(value):
        return None
    return bool(value)


def process_import_indigents(file, user_id):
    column_mapping = {
        HEADER_NIN: int,
        HEADER_NO_LONGER_INDIGENT: _convert_empty_values_to_none
    }
    df = pd.read_excel(file, engine='openpyxl', converters=column_mapping)
    new_column_names = {
        HEADER_NIN: "nin",
        HEADER_NO_LONGER_INDIGENT: "delete",
    }
    df.rename(columns=new_column_names, inplace=True)

    errors = []
    total_sent = 0
    updated = 0
    Insuree = apps.get_model("insuree", "Insuree")

    for index, row in df.iterrows():
        total_sent += 1
        logger.info("Processing row %s", index + 2)
        nin = row["nin"]
        remove_indigent_status = row["delete"]

        insuree = (Insuree.objects.filter(validity_to__isnull=True,
                                          chf_id=nin)
                                  .first())
        if not insuree:
            error_message = f"Error line {index + 2} - unknown NIN {nin}"
            logger.error(error_message)
            errors.append(error_message)
            continue

        family = insuree.family
        if not family.poverty:
            if remove_indigent_status:
                error_message = f"Error line {index + 2} - NIN {nin} was not indigent, its status cannot be removed"
                logger.error(error_message)
                errors.append(error_message)
                continue

            logger.info(f"Updating and autoenrolling family {nin} - it is now indigent")
            update_family_poverty_status(family, True, user_id)
            autoenroll_family(insuree, family)
            updated += 1
        else:
            if remove_indigent_status:
                logger.info(f"Updating family {nin} - it is no longer indigent")
                update_family_poverty_status(family, False, user_id)
                updated += 1
            else:
                Policy = apps.get_model("policy", "Policy")
                active_policies = family.policies.filter(validity_to__isnull=True, status=Policy.STATUS_ACTIVE).all()
                if not active_policies:
                    # Reenrolling the family, but instead the policy should be renewed. Currently, there's no way of renewing
                    logger.info(f"Enrolling again family {nin} - it didn't have any active policy")
                    autoenroll_family(family.head_insuree, family)
                    updated += 1
                else:
                    error_message = f"Error line {index + 2} - NIN {nin} already has an active policy, nothing happened"
                    logger.error(error_message)
                    errors.append(error_message)
                    continue

    success = len(errors) != total_sent
    # success = True
    response_data = {
        "data": {
            "sent": total_sent,
            "failed": len(errors),
            "updated": updated,
        },
        "success": success,
        "errors": errors,
    }
    return JsonResponse(data=response_data, status=200)


def update_family_poverty_status(family, new_status, audit_user_id):
    family.save_history()
    from core import datetime
    now = datetime.datetime.now()
    family.validity_from = now
    family.poverty = new_status
    family.audit_user_id = audit_user_id
    family.save()
