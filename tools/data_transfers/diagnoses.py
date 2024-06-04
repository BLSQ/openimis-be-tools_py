import logging

from django.apps import apps

import pandas as pd
from django.core.paginator import Paginator
from django.http import HttpResponse

from tools.constants import CONTENT_TYPES, XLSX

logger = logging.getLogger(__name__)

HEADER_CODE = "Code"
HEADER_NAME = "Name"


def process_export_diagnoses(user_id):
    logger.info("User (audit id %s) requested export of diagnoses list XLSX", user_id)
    Diagnosis = apps.get_model('medical', 'Diagnosis')
    diagnoses = (Diagnosis.objects.filter(validity_to__isnull=True)
                                  .values("code", "name"))

    data = []

    paginator = Paginator(diagnoses, 1000)
    for page_number in paginator.page_range:
        page = paginator.page(page_number)

        for diagnosis in page.object_list:
            new_data_line = {
                HEADER_CODE: diagnosis["code"],
                HEADER_NAME: diagnosis["name"],
            }
            data.append(new_data_line)

    df = pd.DataFrame(data=data)

    from core import datetime
    now = datetime.datetime.now()
    timestamp = datetime.datetime.strftime(now, "%Y-%m-%d_%H%M%S")
    filename = f"export-diagnoses-{timestamp}.xlsx"
    response = HttpResponse(content_type=CONTENT_TYPES[XLSX])
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response) as writer:
        df.to_excel(writer, index=False)

    return response
