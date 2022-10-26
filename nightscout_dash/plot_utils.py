def add_light_style(fig) -> None:
    """
    Add some basic common styling to a figure for a consistent look across graphs.
    :param fig: Plotly Figure object
    :return: None
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(
        zeroline=True,
        linecolor="gray",
        mirror=True,
        gridcolor="rgba(.9,.9,.9,1)",
        gridwidth=0.5,
    )
    fig.update_yaxes(
        zeroline=True,
        linecolor="gray",
        mirror=True,
        gridcolor="rgba(.9,.9,.9,1)",
        gridwidth=0.5,
    )
