from mplchart.indicators import Indicator


class VWAP(Indicator):
    """Volume Weighted Average Price"""

    same_scale: bool = True  # VWAP should be plotted on the same scale as price

    def __init__(self):
        """
        Initialize VWAP indicator.
        Note: VWAP is typically calculated per session, so no period parameter is needed
        """
        super().__init__()

    def __call__(self, prices):
        """
        Calculate VWAP for the given price data.

        Args:
            prices: Price data containing OHLCV information

        Returns:
            pandas.Series: VWAP values
        """
        # Calculate typical price for each bar
        typical_price = (prices["high"] + prices["low"] + prices["close"]) / 3

        # Calculate cumulative values
        cum_tp_vol = (typical_price * prices["volume"]).cumsum()
        cum_vol = prices["volume"].cumsum()

        # Calculate VWAP
        vwap = cum_tp_vol / cum_vol

        return vwap

    def get_series(self, prices):
        """
        Override get_series to specify which price series to use (VWAP).
        """
        return self.__call__(prices)

    def plot_result(self, data, chart, ax=None):
        """
        Custom plot method to ensure VWAP is plotted on the same axis as the candles.
        """
        # Ensure ax is the main price chart axis
        if ax is None:
            ax = chart.get_axes(self)  # Get the main axes where candles are plotted

        # Extract VWAP values and corresponding x-values (timestamps)
        xv, yv = self.series_xy(data)

        # Ensure there is valid data to plot
        if len(xv) == 0 or len(yv) == 0:
            return  # No data, skip plotting

        # Get the color for VWAP (fallback to "line" if no specific color is set)
        color = chart.get_color("vwap", ax, self, fallback="line")

        # Plot the VWAP line on the main price chart
        ax.plot(xv, yv, label="VWAP", color=color)

        # Ensure the legend is updated
        handles, labels = ax.get_legend_handles_labels()
        if "VWAP" not in labels:
            ax.legend()
