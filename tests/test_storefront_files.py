"""Pure-stdlib catalog integrity checks for the fictional FrameOps window/door storefront."""
from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class StorefrontIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'public/catalog.json').read_text(encoding='utf-8'))

    def test_catalog_has_unique_original_fictional_products(self):
        products=self.catalog['products']
        self.assertEqual(len(products),17)
        self.assertEqual(len({p['sku'] for p in products}),len(products))
        self.assertTrue(self.catalog['fictional'])
        brands={p['brand'] for p in products}
        self.assertEqual(brands,{'CanyonVale','SolaraForm','AeroLoom','HaloLight'})
        for p in products:
            self.assertGreater(p['price_low'],0)
            self.assertGreater(p['price_high'],p['price_low'])
            self.assertEqual(p['visual'],f"/images/{p['sku'].lower()}.svg")
            visual=ROOT/'public'/p['visual'].lstrip('/')
            self.assertTrue(visual.is_file(),visual)
            self.assertIn('<svg',visual.read_text())

    def test_scripts_social_settings_and_journey_in_html(self):
        html=(ROOT/'public/index.html').read_text()
        js=(ROOT/'public/business_settings.js').read_text()
        for name in ('catalog','storefront','demo_journey','business_settings','quick_checkout'):
            self.assertIn(f'<script src="/{name}.js"></script>',html)
        self.assertIn('data-nav="business-settings"',html)
        for platform in ('facebook','x','medium','linkedin','youtube','instagram','tiktok'):
            self.assertIn(f"key:'{platform}'",js)
        self.assertIn('localStorage',js)
        self.assertIn('BroadcastChannel',js)
        journey=(ROOT/'public/demo_journey.js').read_text()
        self.assertIn('BroadcastChannel',journey)
        self.assertIn("case 'deposit'",journey)
        self.assertIn("case 'cancel_installation'",journey)

if __name__=='__main__':unittest.main()
