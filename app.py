from dash import (
    Dash,
)
import dash_bootstrap_components as dbc

from nightscout_dash.layout import generate_ns_layout


# Load all callbacks. Could set up class to handle registering callbacks but this isn't really unwieldy yet.
from nightscout_dash import (
    update_data,
    distribution_table,
    basal_rate_plot,
    site_change_plot,
)

update_data.register_callbacks()
distribution_table.register_callbacks()
basal_rate_plot.register_callbacks()
site_change_plot.register_callbacks()


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
server = app.server  # used for Heroku deployment
app.layout = generate_ns_layout
app.title = "Nightscout analysis"

if __name__ == "__main__":
    app.run_server(debug=True)
