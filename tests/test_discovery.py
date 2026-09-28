import unittest

from edge_engine.config import ResearchConfig
from edge_engine.discovery import select_markets


class DiscoveryTests(unittest.TestCase):
    def test_selects_typed_btc_15m_updown(self):
        payloads = [
            {"slug": "target", "question": "BTC up?", "active": True, "status": "OPEN",
             "assetPriceTerms": {"marketType": "ASSET_PRICE_MARKET_TYPE_UP_DOWN", "horizon": "15m",
                                  "windowStart": "2026-09-28T16:00:00Z", "windowEnd": "2026-09-28T16:15:00Z",
                                  "asset": {"symbol": "btc"}, "priceToBeat": {"value": 70000}}},
            {"slug": "wrong", "question": "ETH up?", "assetPriceTerms": {
                "marketType": "ASSET_PRICE_MARKET_TYPE_UP_DOWN", "horizon": "15m", "asset": {"symbol": "eth"}}},
        ]
        selected = select_markets(payloads, ResearchConfig())
        self.assertEqual([market.slug for market in selected], ["target"])
        self.assertEqual(selected[0].price_to_beat, 70000.0)


if __name__ == "__main__":
    unittest.main()

