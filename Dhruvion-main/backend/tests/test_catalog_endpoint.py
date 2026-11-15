from app.api import routes_v2


class _Catalog:
    def __init__(self):
        self.search_args = None

    def search(self, **kwargs):
        self.search_args = kwargs
        return []

    def get_statistics(self):
        return {"total_datasets": 0}


def test_dataset_catalog_endpoint_uses_catalog_service(monkeypatch):
    catalog = _Catalog()
    monkeypatch.setattr(routes_v2, "get_catalog_service", lambda: catalog)

    response = routes_v2.get_dataset_catalog(region_id="gale_crater")

    assert response.datasets == []
    assert catalog.search_args["region_id"] == "gale_crater"
