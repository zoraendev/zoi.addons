# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestCustomerProfileService(TransactionCase):
    def test_customer_profile_contains_stable_recognition_data(self):
        partner = self.env['res.partner'].create({
            'name': 'ACME Guatemala',
            'email': 'ventas@acme.gt',
            'phone': '+502 5555-0101',
            'mobile': '+502 4444-0202',
            'vat': 'CF-1001',
            'ref': 'CLI-ACME',
            'customer_rank': 1,
            'automation_customer_alias': 'cliente acme',
        })

        profile = partner.get_automation_customer_profile()

        self.assertEqual(profile['partner_id'], partner.id)
        self.assertEqual(profile['customer_uid'], partner.automation_customer_uid)
        self.assertEqual(profile['alias'], 'cliente acme')
        self.assertIn('ventas@acme.gt', profile['search_terms'])
        self.assertIn('50255550101', [item['normalized_value'] for item in profile['identifiers']])
        self.assertTrue(profile['fingerprint'])
        self.assertEqual(partner.automation_customer_fingerprint, profile['fingerprint'])
