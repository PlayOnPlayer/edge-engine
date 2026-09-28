import unittest

from edge_engine.config import ResearchConfig
from edge_engine.demo import demo_snapshots
from edge_engine.paper import PaperEngine


class PaperEngineTests(unittest.TestCase):
    def test_demo_creates_auditable_trades(self):
        engine = PaperEngine(ResearchConfig())
        trades = [trade for snapshot in demo_snapshots() for trade in engine.on_snapshot(snapshot)]
        self.assertGreaterEqual(len(trades), 2)
        self.assertEqual({trade.strategy for trade in trades}, {"PAIR_FIXED", "SMART_EXIT"})
        self.assertTrue(all(trade.data_mode == "DEMO" for trade in trades))
        self.assertTrue(all("Strict trade-through" in trade.assumptions for trade in trades))


if __name__ == "__main__":
    unittest.main()

