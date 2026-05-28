from urllib.parse import urlencode
from config.settings import url_volunteer


class UrlService:

    @staticmethod
    def build_url_volunteers(checkbox_vars, location_ids_types, location: str, distance) -> str:
        params = []
        for key, var in checkbox_vars.items():
            if var.get():
                params.append(("categories[]", var.get()))

        if location:
            location_data = location_ids_types.get(location, ("", "", ""))
            params.extend([
                ("region[location]", location),
                ("region[location_id]", location_data[0] or ""),
                ("region[location_type]", location_data[1] or ""),
            ])
            if len(location_data) > 2 and location_data[2] == 'Postcode':
                params.append(("region[range]", distance))

        return f"{url_volunteer}?{urlencode(params)}" if params else url_volunteer
