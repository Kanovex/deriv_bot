import asyncio
import json
import websockets
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Pull credentials from environment variables for security
DERIV_APP_ID = os.environ.get("DERIV_APP_ID", "1089")
DERIV_API_TOKEN = os.environ.get("DERIV_API_TOKEN", "YOUR_DERIV_TOKEN_HERE")
DERIV_WS_URL = f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"

async def execute_deriv_option(symbol, contract_type, duration, duration_unit, stake):
    async with websockets.connect(DERIV_WS_URL) as ws:
        # 1. Authorize API Connection
        await ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
        auth_res = json.loads(await ws.recv())
        if "error" in auth_res:
            return {"status": "error", "message": auth_res["error"]["message"]}

        # 2. Request Contract Proposal (Pricing)
        proposal_req = {
            "proposal": 1,
            "amount": stake,
            "basis": "stake",
            "currency": "USD", # Change to your Deriv account currency if not USD
            "symbol": symbol,
            "contract_type": contract_type,
            "duration": duration,
            "duration_unit": duration_unit
        }
        await ws.send(json.dumps(proposal_req))
        proposal_res = json.loads(await ws.recv())
        if "error" in proposal_res:
            return {"status": "error", "message": proposal_res["error"]["message"]}

        proposal_id = proposal_res["proposal"]["id"]

        # 3. Buy the Contract
        buy_req = {
            "buy": proposal_id,
            "price": stake
        }
        await ws.send(json.dumps(buy_req))
        buy_res = json.loads(await ws.recv())
        if "error" in buy_res:
            return {"status": "error", "message": buy_res["error"]["message"]}

        return {"status": "success", "contract_id": buy_res["buy"]["contract_id"]}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        symbol = data.get("symbol")
        contract_type = data.get("contract_type")
        duration = data.get("duration", 15)
        duration_unit = data.get("duration_unit", "m")
        stake = data.get("stake", 10.0)

        print(f"Received Signal: {contract_type} on {symbol} for {stake}")

        # Execute async WebSocket call
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            execute_deriv_option(symbol, contract_type, duration, duration_unit, stake)
        )
        loop.close()

        print(f"Trade Execution Result: {result}")
        return jsonify(result), 200

    except Exception as e:
        print(f"Webhook Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)