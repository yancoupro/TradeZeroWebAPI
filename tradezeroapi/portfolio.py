from __future__ import annotations

import warnings
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium import webdriver
from selenium.webdriver.common.by import By
from typing import overload, Optional, Literal

from .enums import PortfolioTab, OrderType


class Portfolio:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    @overload
    def portfolio(self, return_type: Literal['df'] = 'df') -> Optional[pd.DataFrame]:
        ...

    @overload
    def portfolio(self, return_type: Literal['dict']) -> Optional[dict]:
        ...

    def portfolio(self, return_type: Literal['df', 'dict'] = 'df') -> pd.DataFrame | dict | None:
        """
        return the Portfolio table as a pandas.DataFrame or nested dict, with the symbol column as index.
        the column names are the following: 'type', 'qty', 'p_close', 'entry',
        'price', 'change', '%change', 'day_pnl', 'pnl', 'overnight'
        note that if the portfolio is empty Pandas won't be able to locate the table,
        and therefore will return None

        :param return_type: 'df' or 'dict'
        :return: pandas.DataFrame or None if table empty
        """
        portfolio_symbols = self.driver.find_elements(By.XPATH, '//*[@id="opTable-1"]/tbody/tr/td[1]')
        df = pd.read_html(self.driver.page_source, attrs={'id': 'opTable-1'})[0]

        if len(portfolio_symbols) == 0 or df.loc[0, 0].lower() == "you have no open positions.":
            warnings.warn('Portfolio is empty')
            return None

        df.columns = [
            'symbol', 'type', 'qty', 'p_close', 'entry', 'price', 'change', '%change', 'day_pnl', 'pnl', 'overnight'
        ]
        df = df.set_index('symbol')
        if return_type == 'dict':
            return df.to_dict('index')
        return df

    def close_position_overview(self) -> pd.DataFrame:
        """
        Extracts a table with the given ID from a webpage and returns its content as a pandas DataFrame.

        The method assumes that the WebDriver instance is already navigated to the page containing the table
        and that the table has a structure of rows (<tr>) and cells (<td>) within a <tbody> element.

        Returns:
        - DataFrame: A pandas DataFrame containing the table data.

        Example Output:
        +-------+------+-----+---------+-------+-------+-------+---------+----------------+----------------+-----+
        | Symbol| Type | Qty | p_close | Entry | Close | PNL   | Day PNL | Opened         | Closed         | O/N |
        +-------+------+-----+---------+-------+-------+-------+---------+----------------+----------------+-----+
        | ACET  | Long | 100 | 1.180   | 1.220 | 1.180 | -4.000| -4.000  | 11-14 10:08:35 | 11-14 10:29:15 | No  |
        +-------+------+-----+---------+-------+-------+-------+---------+----------------+----------------+-----+
        """

        # First, click on the 'Closed Positions' tab to make sure it's active
        self.driver.find_element(By.ID, "portfolio-tab-cp-1").click()

        # Find all rows in the table
        rows = self.driver.find_elements(By.XPATH, '//table[@id="cpTable-1"]/tbody/tr')

        # List to hold all rows of data
        data: list[list[str]] = []

        # Extract data from each row
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            row_data: list[str] = [cell.text for cell in cells]
            data.append(row_data)

        # Column names (these should be customized to match the specific table's column headers)
        column_names: list[str] = ["Symbol", "Type", "Qty", "p_close", "Entry", "Close", "PNL", "Day PNL", "Opened", "Closed", "O/N"]

        # Create the DataFrame
        df = pd.DataFrame(data, columns=column_names)
        
        # Set 'Symbol' column as the index of the DataFrame
        df.set_index('Symbol', inplace=True)

        # Return the DataFrame
        return df

    def get_inventory(self):
        """
        Extracts inventory data from a specific HTML table using Selenium.

        This method identifies a table within a webpage by its ID, iterates through
        each row of the table, and extracts text from each cell while excluding a 
        specific, undesired column. It compiles the text into a pandas DataFrame 
        with predefined column headers. Rows without any table data cells are ignored.

        Returns:
            pandas.DataFrame: A DataFrame containing the inventory data, structured 
            according to predefined headers.
        """
        # Find the table by ID
        table = self.driver.find_element(By.ID, "locate-inventory-table")
        
        # Find all the rows in the table
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        # Specify the desired headers
        headers = ['Symbol', 'Available', 'Unavailable', 'Pre-Borrow', 'Action']
        
        # Initialize an empty list to hold all row data
        all_row_data = []
        
        # Iterate over the rows
        for row in rows:
            # Find all cell tags in this row
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                # If there are no td tags, it might be the header row with th tags
                cells = row.find_elements(By.TAG_NAME, "th")
            # Get the text from each cell, ignoring the fifth cell (if exists)
            row_data = [cell.text for idx, cell in enumerate(cells) if idx != 4]
            # Append the row's text to the aggregated list
            all_row_data.append(row_data)
        
        # Exclude any empty rows if they exist
        all_row_data = [row for row in all_row_data if row]
        
        # Create the DataFrame assuming all data rows have the same number of columns as the headers
        df = pd.DataFrame(all_row_data, columns=headers)
        
        return df

    def open_orders(self) -> pd.DataFrame:
        """
        return DF with only positions that were opened today (intraday positions)

        :return: pandas.DataFrame
        """
        df = self.portfolio()

        # if there are no open position: return an empty dataframe
        if df is None:
            return pd.DataFrame()

        filt = df['overnight'] == 'Yes'
        return df.loc[~filt]

    def invested(self, symbol) -> bool:
        """
        returns True if the given symbol is in portfolio, else: false

        :param symbol: str: e.g: 'aapl', 'amd', 'NVDA', 'GM'
        :return: bool
        """
        data = self.portfolio('dict')
        if data is None:
            return False

        return symbol.upper() in data.keys()

    def _switch_portfolio_tab(self, tab: PortfolioTab) -> None:
        """
        Switch the focus to a given tab

        Note that this is idem-potent, meaning you can switch twice consecutively in the same tab.

        :param tab: enum of PortfolioTab
        :return: None
        """
        portfolio_tab = self.driver.find_element(By.ID, tab)
        portfolio_tab.click()

    def get_active_orders(self, return_type: str = 'df'):
        """
        Get a dataframe with all the active orders and their info

        :param return_type: 'df' or 'dict'
        :return: dataframe or dictionary (based on the return_type parameter)
        """
        active_orders = self.driver.find_elements(By.XPATH, '//*[@id="aoTable-1"]/tbody/tr[@order-id]')
        if len(active_orders) == 0:
            warnings.warn('There are no active orders')
            return

        df = pd.read_html(self.driver.page_source, attrs={'id': 'aoTable-1'})[0]
        df = df.drop(0, axis=1)  # remove the first column which contains the button "CANCEL"
        df.columns = ['ref_number', 'symbol', 'side', 'qty', 'type', 'status', 'tif', 'limit', 'stop', 'placed']
        # df = df.set_index('symbol')  # cant set it as a column since its not always unique

        if return_type == 'dict':
            return df.to_dict('index')
        return df

    def symbol_present_in_active_orders(self, symbol: str) -> bool:
        """
        Check if a given symbol is present in the active orders tab

        :param symbol:
        :return: True or False
        """
        return symbol.upper() in self.get_active_orders()['symbol'].values

    def cancel_active_order(self, symbol: str, order_type: OrderType) -> None:
        """
        Cancel a pending order

        :param symbol:
        :param order_type: enum of OrderType
        :return: None
        """
        symbol = symbol.upper()
        self._switch_portfolio_tab(tab=PortfolioTab.active_orders)

        df = self.get_active_orders()
        assert symbol in df['symbol'].values, f'Given symbol {symbol} is not present in the active orders tab'

        # find the ref-id of all the orders we have to cancel:
        filt = (df['symbol'] == symbol) & (df['type'] == order_type)
        ids_to_cancel = df[filt]['ref_number'].values
        ids_to_cancel = [x.replace('S.', '') for x in ids_to_cancel]

        for order_id in ids_to_cancel:
            cancel_button = self.driver.find_element(
                By.XPATH, f'//div[@id="portfolio-content-tab-ao-1"]//*[@order-id="{order_id}"]/td[@class="red"]')
            cancel_button.click()
