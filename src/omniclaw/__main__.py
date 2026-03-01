from omniclaw.app import create_app
from omniclaw.config import load_settings


app = create_app(load_settings())

