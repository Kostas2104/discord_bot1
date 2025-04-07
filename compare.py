import requests
import json

def get_gateio_caw_data():
    """Retrieves the ask and bid price of CAW/USDT from Gate.io with 11 decimal places."""
    base_url = "https://api.gateio.ws/api/v4"
    currency_pair = "CAW_USDT"

    try:
        ticker_endpoint = f"{base_url}/spot/tickers?currency_pair={currency_pair}"
        response = requests.get(ticker_endpoint)
        response.raise_for_status()
        data = response.json()

        if data and isinstance(data, list) and len(data) > 0:
            ticker_info = data[0]
            ask = ticker_info.get('lowest_ask')
            bid = ticker_info.get('highest_bid')
            return {"exchange": "Gate.io", "ask": f"{float(ask):.11f}" if ask else None, "bid": f"{float(bid):.11f}" if bid else None}
        else:
            return {"exchange": "Gate.io", "error": f"Could not retrieve ticker data for {currency_pair}"}

    except requests.exceptions.RequestException as e:
        return {"exchange": "Gate.io", "error": f"API request error: {e}"}
    except json.JSONDecodeError as e:
        return {"exchange": "Gate.io", "error": f"JSON decoding error: {e}"}
    except Exception as e:
        return {"exchange": "Gate.io", "error": f"An unexpected error occurred: {e}"}

def get_ascendex_caw_data():
    """Retrieves the ask and bid price of CAW/USDT from AscendEx with 11 decimal places."""
    base_url = "https://ascendex.com/api/pro/v1"
    symbol = "$CAW/USDT"  # Corrected symbol

    try:
        ticker_endpoint = f"{base_url}/spot/ticker?symbol={symbol}"
        response = requests.get(ticker_endpoint)
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data and isinstance(data['data'], dict):
            ticker_info = data['data']
            ask = ticker_info.get('ask')
            bid = ticker_info.get('bid')
            return {"exchange": "AscendEx", "ask": f"{float(ask[0]):.11f}" if ask else None, "bid": f"{float(bid[0]):.11f}" if bid else None}
        else:
            return {"exchange": "AscendEx", "error": f"Could not retrieve ticker data for {symbol}"}

    except requests.exceptions.RequestException as e:
        return {"exchange": "AscendEx", "error": f"API request error: {e}"}
    except json.JSONDecodeError as e:
        return {"exchange": "AscendEx", "error": f"JSON decoding error: {e}"}
    except Exception as e:
        return {"exchange": "AscendEx", "error": f"An unexpected error occurred: {e}"}

if __name__ == "__main__":
    gateio_data = get_gateio_caw_data()
    ascendex_data = get_ascendex_caw_data()

    print("--- CAW/USDT Ask and Bid Comparison ---")
    print("---------------------------------------")

    # Print Gate.io Results
    print("Gate.io:")
    if "error" in gateio_data:
        print(f"  Error: {gateio_data['error']}")
        gateio_buy_price = None
        gateio_sell_price = None
    else:
        gateio_sell_price = gateio_data['ask']
        gateio_buy_price = gateio_data['bid']
        print(f"  Selling Price (Ask): {gateio_sell_price}")
        print(f"  Buying Price (Bid): {gateio_buy_price}")
    print("---------------------------------------")

    # Print AscendEx Results
    print("AscendEx:")
    if "error" in ascendex_data:
        print(f"  Error: {ascendex_data['error']}")
        ascendex_buy_price = None
        ascendex_sell_price = None
    else:
        ascendex_sell_price = ascendex_data['ask']
        ascendex_buy_price = ascendex_data['bid']
        print(f"  Selling Price (Ask): {ascendex_sell_price}")
        print(f"  Buying Price (Bid): {ascendex_buy_price}")
    print("---------------------------------------")

    # Comparison and Potential Arbitrage
    print("\n--- Potential Arbitrage Opportunity (if available) ---")
    arbitrage_amount = 2000000000  # 2 billion CAW tokens

    if gateio_buy_price and ascendex_sell_price:
        gateio_buy_price_float = float(gateio_buy_price)
        ascendex_sell_price_float = float(ascendex_sell_price)
        if gateio_buy_price_float < ascendex_sell_price_float:
            cost_gateio = arbitrage_amount * gateio_buy_price_float
            revenue_ascendex = arbitrage_amount * ascendex_sell_price_float
            profit = revenue_ascendex - cost_gateio
            print("Buy on Gate.io, sell on AscendEx:")
            print(f"  Buy Price on Gate.io: {gateio_buy_price}")
            print(f"  Sell Price on AscendEx: {ascendex_sell_price}")
            print(f"  Cost to buy {arbitrage_amount} CAW on Gate.io: {cost_gateio:.8f} USDT")
            print(f"  Revenue from selling {arbitrage_amount} CAW on AscendEx: {revenue_ascendex:.8f} USDT")
            print(f"  Potential Profit (without fees): {profit:.8f} USDT")
        else:
            print("No direct arbitrage opportunity (Buy Gate.io < Sell AscendEx) at this moment.")

    if ascendex_buy_price and gateio_sell_price:
        ascendex_buy_price_float = float(ascendex_buy_price)
        gateio_sell_price_float = float(gateio_sell_price)
        if ascendex_buy_price_float < gateio_sell_price_float:
            cost_ascendex = arbitrage_amount * ascendex_buy_price_float
            revenue_gateio = arbitrage_amount * gateio_sell_price_float
            profit = revenue_gateio - cost_ascendex
            print("\nBuy on AscendEx, sell on Gate.io:")
            print(f"  Buy Price on AscendEx: {ascendex_buy_price}")
            print(f"  Sell Price on Gate.io: {gateio_sell_price}")
            print(f"  Cost to buy {arbitrage_amount} CAW on AscendEx: {cost_ascendex:.8f} USDT")
            print(f"  Revenue from selling {arbitrage_amount} CAW on Gate.io: {revenue_gateio:.8f} USDT")
            print(f"  Potential Profit (without fees): {profit:.8f} USDT")
        else:
            print("No direct arbitrage opportunity (Buy AscendEx < Sell Gate.io) at this moment.")

    if not gateio_buy_price or not ascendex_sell_price or not ascendex_buy_price or not gateio_sell_price:
        print("Could not perform arbitrage calculation due to missing price data.")
