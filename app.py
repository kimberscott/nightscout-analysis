from dash import Dash
import dash_bootstrap_components as dbc

from nightscout_dash.layout import generate_ns_layout
from nightscout_dash.basal_rate_plot import BasalRatePlot
from nightscout_dash.distribution_table import DistributionTable
from nightscout_dash.site_change_plot import SiteChangePlot
from nightscout_dash.update_data import DataUpdater

# Load all callbacks. Could set up base class to handle registering callbacks but this isn't really unwieldy yet.
DataUpdater.register_callbacks()
BasalRatePlot.register_callbacks()
DistributionTable.register_callbacks()
SiteChangePlot.register_callbacks()


app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
server = app.server  # used for Heroku deployment
app.layout = generate_ns_layout
app.title = "Nightscout analysis"

if __name__ == "__main__":
    app.run_server(debug=True)
