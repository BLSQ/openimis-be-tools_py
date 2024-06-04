import logging

from django.apps import apps

import pandas as pd
from django.core.paginator import Paginator
from django.http import HttpResponse

from tools.constants import CONTENT_TYPES, XLSX

logger = logging.getLogger(__name__)

HEADER_CODE = "Code"
HEADER_NAME = "Name"
HEADER_TYPE = "Type"
HEADER_PARENT_CODE = "Parent Code"
HEADER_PARENT_NAME = "Parent Name"

TYPE_REGION = "R"
TYPE_DISTRICT = "D"
TYPE_WARD = "W"
TYPE_VILLAGE = "V"

LOCATION_TYPE_IN_THE_GAMBIA = {
    TYPE_REGION: "Region",
    TYPE_DISTRICT: "LGA",
    TYPE_WARD: "District",
    TYPE_VILLAGE: "Settlement",
}


def process_locations(locations, data):
    for location in locations:
        new_data_line = {
            HEADER_CODE: location["code"],
            HEADER_NAME: location["name"],
            HEADER_TYPE: LOCATION_TYPE_IN_THE_GAMBIA[location["type"]],
            HEADER_PARENT_CODE: location["parent__code"],
            HEADER_PARENT_NAME: location["parent__name"],
        }
        data.append(new_data_line)


def process_export_locations(user_id):
    logger.info("User (audit id %s) requested export of diagnoses list XLSX", user_id)
    Location = apps.get_model('location', 'Location')
    data = []

    regions = (Location.objects.filter(validity_to__isnull=True, type=TYPE_REGION)
                               .order_by("id")
                               .values("code", "name", "type", "parent__code", "parent__name"))
    process_locations(regions, data)

    districts = (Location.objects.filter(validity_to__isnull=True, type=TYPE_DISTRICT)
                                 .order_by("id")
                                 .prefetch_related("parent")
                                 .values("code", "name", "type", "parent__code", "parent__name"))
    process_locations(districts, data)

    wards = (Location.objects.filter(validity_to__isnull=True, type=TYPE_WARD)
                             .order_by("parent_id")
                             .prefetch_related("parent")
                             .values("code", "name", "type", "parent__code", "parent__name"))
    process_locations(wards, data)

    villages = (Location.objects.filter(validity_to__isnull=True, type=TYPE_VILLAGE)
                                .order_by("parent_id")
                                .prefetch_related("parent")
                                .values("code", "name", "type", "parent__code", "parent__name"))
    paginator = Paginator(villages, 500)
    for page_number in paginator.page_range:
        page = paginator.page(page_number)
        process_locations(page.object_list, data)

    df = pd.DataFrame(data=data)

    from core import datetime
    now = datetime.datetime.now()
    timestamp = datetime.datetime.strftime(now, "%Y-%m-%d_%H%M%S")
    filename = f"export-locations-{timestamp}.xlsx"
    response = HttpResponse(content_type=CONTENT_TYPES[XLSX])
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    with pd.ExcelWriter(response) as writer:
        df.to_excel(writer, index=False)

    return response
