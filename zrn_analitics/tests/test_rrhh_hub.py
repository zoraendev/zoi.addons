# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestRrhhHub(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.home_model = cls.env['zrn_analitics.home']
        cls.job_model = cls.env['hr.job']
        cls.applicant_model = cls.env['hr.applicant']
        cls.predictor_model = cls.env['zrn.rrhh.predictor']
        cls.checklist_model = cls.env['zrn.rrhh.interview.checklist']
        cls.pattern_model = cls.env['zrn.rrhh.validated.pattern']

        cls.job = cls.job_model.create({
            'name': 'Auxiliar de Bodega',
            'company_id': cls.env.company.id,
        })
        cls.applicant_a = cls.applicant_model.create({
            'name': 'Solicitud RRHH A',
            'partner_name': 'Candidato Uno',
            'job_id': cls.job.id,
            'email_from': 'candidato1@example.com',
        })
        cls.applicant_b = cls.applicant_model.create({
            'name': 'Solicitud RRHH B',
            'partner_name': 'Candidato Dos',
            'job_id': cls.job.id,
            'email_from': 'candidato2@example.com',
        })

    def test_01_rrhh_upsert_creates_single_records(self):
        self.home_model.upsert_rrhh_predictor(self.applicant_a.id, {
            'family_structure': '4',
            'family_contact': '2',
            'asset_congruence': '3',
            'income_gaps': '1',
            'living_context': '3',
            'tattoo_visibility': '2',
            'job_count': '3',
            'conflict_history': '1',
            'recent_alcohol': '3',
            'sleep_condition': '1',
            'breakfast_condition': '1',
        })
        self.home_model.upsert_rrhh_predictor(self.applicant_a.id, {
            'family_structure': '2',
            'family_contact': '2',
        })
        self.home_model.upsert_rrhh_checklist(self.applicant_a.id, {
            'family_parents': True,
            'finance_assets': True,
            'work_job_count': True,
        })

        predictor_records = self.predictor_model.search([('applicant_id', '=', self.applicant_a.id)])
        checklist_records = self.checklist_model.search([('applicant_id', '=', self.applicant_a.id)])
        pattern_records = self.pattern_model.search([('applicant_id', '=', self.applicant_a.id)])

        self.assertEqual(len(predictor_records), 1)
        self.assertEqual(len(checklist_records), 1)
        self.assertEqual(len(pattern_records), 1)
        self.assertGreater(pattern_records.matched_pattern_count, 0)

        with self.assertRaises(Exception):
            self.predictor_model.create({
                'applicant_id': self.applicant_a.id,
                'company_id': self.env.company.id,
            })

    def test_02_rrhh_payload_contains_current_records(self):
        self.home_model.upsert_rrhh_predictor(self.applicant_b.id, {
            'family_structure': '0',
            'family_contact': '0',
            'asset_congruence': '0',
            'income_gaps': '0',
            'living_context': '0',
            'tattoo_visibility': '0',
            'job_count': '0',
            'conflict_history': '0',
            'recent_alcohol': '0',
            'sleep_condition': '0',
            'breakfast_condition': '0',
        })
        payload = self.home_model.get_rrhh_hub_payload({
            'selected_applicant_id': self.applicant_b.id,
        })

        self.assertEqual(payload['current_applicant']['id'], self.applicant_b.id)
        self.assertIn('historical_rows', payload)
        self.assertTrue(any(
            row['applicant_id'] == self.applicant_b.id
            for row in payload['historical_rows']
        ))
        self.assertEqual(payload['current_predictor']['risk_level'], 'low')
        self.assertIn('questions', payload['predictor_config'])
        self.assertIn('sections', payload['checklist_template'])
        self.assertIn('library', payload['validated_patterns'])

    def test_03_rrhh_cascade_delete_related_records(self):
        applicant = self.applicant_model.create({
            'name': 'Solicitud RRHH C',
            'partner_name': 'Candidato Tres',
            'job_id': self.job.id,
        })
        self.home_model.upsert_rrhh_predictor(applicant.id, {
            'family_structure': '4',
            'recent_alcohol': '3',
        })
        self.home_model.upsert_rrhh_checklist(applicant.id, {
            'exam_alcohol': True,
        })
        predictor = self.predictor_model.search([('applicant_id', '=', applicant.id)], limit=1)
        checklist = self.checklist_model.search([('applicant_id', '=', applicant.id)], limit=1)
        pattern = self.pattern_model.search([('applicant_id', '=', applicant.id)], limit=1)

        self.assertTrue(predictor)
        self.assertTrue(checklist)
        self.assertTrue(pattern)

        applicant.unlink()

        self.assertFalse(self.predictor_model.browse(predictor.id).exists())
        self.assertFalse(self.checklist_model.browse(checklist.id).exists())
        self.assertFalse(self.pattern_model.browse(pattern.id).exists())
