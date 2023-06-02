from ninja import NinjaAPI

from timor_locations.router import router

api = NinjaAPI(csrf=True)
api.add_router("/", router)
