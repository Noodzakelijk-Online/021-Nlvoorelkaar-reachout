import urllib
from config.settings import url_volunteer


class UrlService:

    @staticmethod
    def build_url_volunteers(checkbox_vars, location_ids_types, location: str, distance) -> str:
        categories = []
        for key, var in checkbox_vars.items():
            if var.get():
                categories.append(f"categories%5B%5D={var.get()}")

        params = []
        if location:
            location_encoded = urllib.parse.quote(location)
            params.append(f"region%5Blocation%5D={location_encoded}")
            location_id = location_ids_types[location][0] if location_ids_types[location][0] is not None else ''
            params.append(f"region%5Blocation_id%5D={location_id}")
            location_type = location_ids_types[location][1] if location_ids_types[location][1] is not None else ''
            params.append(f"region%5Blocation_type%5D={location_type}")
            if location_ids_types[location][2] == 'Postcode':
                params.append(f"region%5Brange%5D={distance}")

        if categories:
            params.extend(categories)
        return f"{url_volunteer}?{'&'.join(params)}" if params else url_volunteer
