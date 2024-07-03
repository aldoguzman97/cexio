# CEX.IO API Python Module

This Python module allows users to interact with the CEX.IO API using RESTful `GET` and `POST` requests. The module supports both public and private API calls, ensuring a broad range of functionalities from fetching market data to managing account details.

## Table of Contents

1. [Installation](#installation)
2. [Usage](#usage)
3. [API Methods](#api-methods)
4. [Debugging](#debugging)
5. [Error Handling](#error-handling)
6. [Logging](#logging)
7. [Examples](#examples)
8. [Contributing](#contributing)
9. [License](#license)

## Installation

To use the CEX.IO API Python module, you'll need to have Python 3 installed. You can install the required dependencies using `pip`.

```bash
pip install requests urllib3
```

## Usage

### Initialization

First, import the `Api` class and initialize it with your CEX.IO username, API key, and API secret. You can obtain your API key and secret from your [CEX.IO profile](https://cex.io/trade/profile#/api).

```python
from your_module_name import Api

api = Api('your_username', 'your_api_key', 'your_api_secret')
```

### Sample API Calls

#### Public API Call
Fetch the latest price for the BTC/USD pair:
```python
result = api.get_last_price('BTC', 'USD')
print(result)
```

#### Private API Call
Fetch your account balance:
```python
balance = api.get_balance()
print(balance)
```

## API Methods

### Public Methods

- `get_currency_limits()`: Get currency limits.
- `get_ticker(symbol1='BTC', symbol2='USD')`: Get ticker for a pair.
- `get_tickers(symbols=None)`: Get tickers for given markets.
- `get_last_price(symbol1='BTC', symbol2='USD')`: Get the last price for a pair.
- `get_last_prices(symbols)`: Get last prices for given markets.
- `get_order_book(symbol1, symbol2, depth=10)`: Get order book.
- `get_trade_history(symbol1, symbol2, since)`: Get trade history.

### Private Methods

- `get_balance()`: Get account balance.
- `get_open_orders(symbol1='', symbol2='')`: Get open orders.
- `convert(symbol1, symbol2, amount)`: Convert one symbol to another.
- `place_order(order_type, amount, price, symbol1, symbol2)`: Place an order.
- `cancel_order(order_id)`: Cancel an order.
- `get_order_details(order_id)`: Get order details.
- `get_crypto_address(currency)`: Get crypto address.
- `get_my_fee()`: Get user's fee.

## Debugging

Logging is configured at the INFO level. You can change the logging level to DEBUG to get more detailed output for debugging purposes.

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

## Error Handling

Custom exceptions are provided to handle different error scenarios:

- `ApiError`: Base class for all API-related errors.
- `NetworkError`: Raised for network-related errors.
- `InvalidCredentialsError`: Raised for invalid API credentials.
- `ApiResponseError`: Raised for errors in API responses.

Example of handling errors:

```python
try:
    result = api.get_last_price('BTC', 'USD')
    print(result)
except ApiError as e:
    logging.error(f"An API error occurred: {e}")
```

## Logging

The module provides an option to enable or disable logging dynamically when initializing the `Api` class instance. To enable logging, pass `logging_enabled=True` during initialization.

### Example with Logging Enabled

```python
api = Api('your_username', 'your_api_key', 'your_api_secret', logging_enabled=True)
```

### Example with Logging Disabled (default)

```python
api = Api('your_username', 'your_api_key', 'your_api_secret', logging_enabled=False)
```

## Examples

### Fetching Last Price

```python
api = Api('your_username', 'your_api_key', 'your_api_secret')
try:
    last_price = api.get_last_price('BTC', 'USD')
    print(last_price)
except ApiError as e:
    logging.error(f"An API error occurred: {e}")
```

### Placing an Order

```python
try:
    order = api.place_order('buy', 1.0, 50000, 'BTC', 'USD')
    print(order)
except ApiError as e:
    logging.error(f"An API error occurred: {e}")
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.
