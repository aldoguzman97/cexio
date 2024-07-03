import hmac
import hashlib
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants
BASE_URL = 'https://cex.io/api/%s/'
API_KEY_LENGTH = 26
API_SECRET_LENGTH = 27

# Set logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Custom exceptions
class ApiError(Exception):
    """Base class for API errors."""
    pass

class NetworkError(ApiError):
    """Exception raised for network-related errors."""
    pass

class InvalidCredentialsError(ApiError):
    """Exception raised for invalid API credentials."""
    pass

class ApiResponseError(ApiError):
    """Exception raised for API response errors."""
    def __init__(self, status_code, message, data=None):
        self.status_code = status_code
        self.message = message
        self.data = data
        super().__init__(f"API returned status code {status_code}: {message}")

    @staticmethod
    def from_response(response):
        status_code = response.status_code
        try:
            body = response.json()
            message = body.get('error', response.text)
        except ValueError:
            body = response.text
            message = body
        return ApiResponseError(status_code, message, body)

# Helper functions
def create_session_with_retries(retries=3, backoff_factor=0.3):
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

class Api:
    def __init__(self, username, api_key, api_secret):
        self.username = username
        self.api_key = api_key
        self.api_secret = api_secret
        self.validate_api_credentials(api_key, api_secret)
        self.session = create_session_with_retries()

    @staticmethod
    def validate_api_credentials(api_key, api_secret):
        """Validate API key and secret length."""
        if not api_key or not api_secret:
            raise InvalidCredentialsError("API key and secret cannot be empty.")
        # Flexible length validation
        if len(api_key) < 20 or len(api_secret) < 20:
            raise InvalidCredentialsError("API key or secret length is too short. Check if they are correct.")

    def _create_signature(self, nonce):
        """Create a signature for the private API request."""
        message = nonce + self.username + self.api_key
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        return signature

    def _validate_params(self, required_params, provided_params):
        """Validate that all required parameters are provided."""
        missing_params = [param for param in required_params if param not in provided_params]
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

    def _api_request(self, command, params=None, market='', private=False, method='GET'):
        """Send an API request to the specified command."""
        params = params or {}
        url = f"{BASE_URL % command}{market}"
        headers = {'User-agent': f'bot-cex.io-{self.username}', 'Content-Type': 'application/json'}
        
        if private:
            nonce = str(int(time.time() * 1000))
            signature = self._create_signature(nonce)
            params.update({'key': self.api_key, 'signature': signature, 'nonce': nonce})
            self._validate_params(['nonce', 'key', 'signature'], params)
            logging.info(f"Making private API call to {command} with params: {[k for k in params.keys()]}")
        else:
            logging.info(f"Making public API call to {command} with params: {params}")

        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            else:
                response = self.session.post(url, json=params, headers=headers, timeout=30)

            response.raise_for_status()
            try:
                response_data = response.json()
            except ValueError:
                raise ApiResponseError(response.status_code, "Invalid JSON response")
            if 'error' in response_data:
                raise ApiResponseError.from_response(response)
            logging.info(f"Received response for {command}: {response_data}")
            return response_data
        except requests.exceptions.Timeout:
            logging.error(f"Request to {command} timed out.")
            raise NetworkError(f"Request to {command} timed out.")
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err.response.text}")
            raise ApiResponseError.from_response(http_err.response)
        except requests.exceptions.RequestException as req_err:
            logging.error(f"An error occurred: {req_err}")
            raise NetworkError(f"An error occurred: {req_err}")

    def api_call(self, command, params=None, market='', private=False, method='GET'):
        """General API call method."""
        if not private:
            method = 'GET'
        return self._api_request(command, params, market, private, method)

    def public_api_call(self, command, market='BTC/USD', params=None):
        """Public API call method."""
        return self.api_call(command, params, market)

    def private_api_call(self, command, params=None):
        """Private API call method."""
        return self.api_call(command, params, private=True, method='POST')

    # Currency limits
    def get_currency_limits(self):
        """Get currency limits."""
        return self.public_api_call('currency_limits')

    # Ticker
    def get_ticker(self, symbol1='BTC', symbol2='USD'):
        """Get ticker for a pair."""
        return self.public_api_call(f'ticker/{symbol1}/{symbol2}')

    # Tickers for all pairs by markets
    def get_tickers(self, symbols=None):
        """Get tickers for given markets."""
        symbols = '/'.join(symbols) if symbols else ''
        return self.public_api_call(f'tickers/{symbols}')

    # Last price
    def get_last_price(self, symbol1='BTC', symbol2='USD'):
        """Get the last price for a pair."""
        return self.public_api_call(f'last_price/{symbol1}/{symbol2}')

    # Last prices for given markets
    def get_last_prices(self, symbols):
        """Get last prices for given markets."""
        return self.public_api_call(f'last_prices/{"/".join(symbols)}')

    # Convert currency
    def convert(self, symbol1, symbol2, amount):
        """Convert one symbol to another."""
        params = {'amnt': amount}
        return self.private_api_call(f'convert/{symbol1}/{symbol2}', params)

    # Chart (price stats)
    def get_price_stats(self, symbol1, symbol2, last_hours=None):
        """Get price stats."""
        params = {'lastHours': last_hours, 'maxRespArrSize': 100}  # Adjust maxRespArrSize to a valid value
        return self.private_api_call(f'price_stats/{symbol1}/{symbol2}', params)

    # Historical OHLCV Chart
    def historical_ohlcv(self, date, symbol1, symbol2):
        """Fetch historical OHLCV data."""
        url = f'https://cex.io/api/ohlcv/hd/{date}/{symbol1}/{symbol2}'
        try:
            response = self.session.get(url, headers={'Accept': '*/*'})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred while fetching historical OHLCV data: {e}")
            raise NetworkError(f"An error occurred while fetching historical OHLCV data: {e}")

    # Orderbook
    def get_order_book(self, symbol1, symbol2, depth=10):
        """Get order book."""
        return self.public_api_call(f'order_book/{symbol1}/{symbol2}', params={'depth': depth})

    # Trade history
    def get_trade_history(self, symbol1, symbol2, since):
        """Get trade history."""
        return self.public_api_call(f'trade_history/{symbol1}/{symbol2}', params={'since': since})

    # Account balance
    def get_balance(self):
        """Get account balance."""
        return self.private_api_call('balance')

    # Open orders
    def get_open_orders(self, symbol1='', symbol2=''):
        """Get open orders."""
        if symbol1 and symbol2:
            return self.private_api_call(f'open_orders/{symbol1}/{symbol2}')
        elif symbol1:
            return self.private_api_call(f'open_orders/{symbol1}')
        else:
            return self.private_api_call('open_orders')

    # Open orders by pair
    def get_open_orders_by_pair(self, pair):
        """Get open orders by pair."""
        return self.private_api_call('open_orders', {'pair': pair})

    # Open orders by symbol
    def get_open_orders_by_symbol(self, symbol):
        """Get open orders by symbol."""
        return self.private_api_call('open_orders', {'symbol': symbol})

    # Mass cancel place orders
    def mass_cancel_place_orders(self, cancel_orders, place_orders, cancel_placed_orders_if_place_failed=False):
        """Cancel and place multiple orders."""
        params = {
            'cancel-orders': cancel_orders,
            'place-orders': place_orders,
            'cancelPlacedOrdersIfPlaceFailed': cancel_placed_orders_if_place_failed
        }
        return self.private_api_call('mass_cancel_place_orders', params)

    # Active order status
    def get_active_order_status(self, orders_list):
        """Get active orders status."""
        params = {
            'orders_list': orders_list
        }
        return self.private_api_call('active_orders_status', params)

    # Archived orders
    def get_archived_orders(self, symbol1, symbol2):
        """Get archived orders."""
        return self.private_api_call(f'archived_orders/{symbol1}/{symbol2}')

    # Cancel order
    def cancel_order(self, order_id):
        """Cancel an order."""
        return self.private_api_call('cancel_order', {'id': order_id})

    # Cancel all orders for a pair
    def cancel_orders(self, symbol1, symbol2):
        """Cancel all orders for a pair."""
        return self.private_api_call(f'cancel_orders/{symbol1}/{symbol2}')

    # Place order
    def place_order(self, order_type, amount, price, symbol1, symbol2):
        """Place an order."""
        params = {
            'type': order_type,
            'amount': amount,
            'price': price
        }
        return self.private_api_call(f'place_order/{symbol1}/{symbol2}', params)

    # Get order details
    def get_order_details(self, order_id):
        """Get order details."""
        return self.private_api_call('get_order', {'id': order_id})

    # Get order transactions
    def get_order_transactions(self, order_id):
        """Get order transactions."""
        return self.private_api_call('get_order_tx', {'id': order_id})

    # Get crypto address
    def get_crypto_address(self, currency):
        """Get crypto address."""
        nonce = str(int(time.time() * 1000))
        signature = self._create_signature(nonce)
        params = {
            'key': self.api_key,
            'signature': signature,
            'nonce': nonce,
            'currency': currency
        }
        return self.private_api_call('get_address', params)

    # Get all crypto addresses
    def get_all_crypto_addresses(self, currency):
        """Get all crypto addresses."""
        nonce = str(int(time.time() * 1000))
        signature = self._create_signature(nonce)
        params = {
            'key': self.api_key,
            'signature': signature,
            'nonce': nonce,
            'currency': currency
        }
        return self.private_api_call('get_crypto_address', params)

    # Get my fee
    def get_my_fee(self):
        """Get user's fee."""
        return self.private_api_call('get_myfee')

    # Cancel replace order
    def cancel_replace_order(self, symbol1, symbol2, order_type, amount, price, order_id):
        """Cancel and replace an order."""
        params = {
            'symbol1': symbol1,
            'symbol2': symbol2,
            'type': order_type,
            'amount': amount,
            'price': price,
            'order_id': order_id
        }
        return self.private_api_call(f'cancel_replace_order/{symbol1}/{symbol2}', params)

    # Currency profile
    def get_currency_profile(self):
        """Get currency profile."""
        return self.private_api_call('currency_profile')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

# Example usage:
if __name__ == "__main__":
    api = Api('your_username', 'your_api_key', 'your_api_secret')
    try:
        # Fetch the last price for BTC/USD
        result = api.get_last_price('BTC', 'USD')
        print(result)
    except ApiError as e:
        logging.error(f"An API error occurred: {e}")
