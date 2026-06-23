# -*- coding: utf-8 -*-

from odoo import api, fields, models


RRHH_RISK_THRESHOLDS = [
    {'key': 'low', 'label': 'Riesgo bajo', 'min': 0.0, 'max': 5.0},
    {'key': 'moderate', 'label': 'Riesgo moderado', 'min': 5.1, 'max': 12.0},
    {'key': 'high', 'label': 'Riesgo alto', 'min': 12.1, 'max': 20.0},
    {'key': 'very_high', 'label': 'Riesgo muy alto', 'min': 20.1, 'max': None},
]


PREDICTOR_QUESTIONS = [
    {
        'key': 'family_structure',
        'factor': 'Situacion familiar',
        'factor_key': 'family',
        'weight': 3.0,
        'badge': 'Alto x3',
        'label': 'Padres vivos y presentes en su vida',
        'options': [
            {'value': '0', 'label': 'Ambos presentes', 'points': 0},
            {'value': '2', 'label': 'Uno fallecido o ausente', 'points': 2},
            {'value': '4', 'label': 'Ambos fallecidos o ausentes', 'points': 4},
        ],
    },
    {
        'key': 'family_contact',
        'factor': 'Situacion familiar',
        'factor_key': 'family',
        'weight': 3.0,
        'badge': 'Alto x3',
        'label': 'Contacto activo con padre y madre',
        'options': [
            {'value': '0', 'label': 'Si con ambos', 'points': 0},
            {'value': '2', 'label': 'No con uno', 'points': 2},
            {'value': '4', 'label': 'No con ninguno', 'points': 4},
        ],
    },
    {
        'key': 'asset_congruence',
        'factor': 'Patrimonio y finanzas',
        'factor_key': 'patrimony',
        'weight': 3.0,
        'badge': 'Alto x3',
        'label': 'Patrimonio congruente con sus ingresos',
        'options': [
            {'value': '0', 'label': 'Totalmente congruente', 'points': 0},
            {'value': '3', 'label': 'Algo desproporcionado', 'points': 3},
            {'value': '5', 'label': 'Muy desproporcionado', 'points': 5},
        ],
    },
    {
        'key': 'income_gaps',
        'factor': 'Patrimonio y finanzas',
        'factor_key': 'patrimony',
        'weight': 2.0,
        'badge': 'Medio x2',
        'label': 'Brechas de ingreso sin explicar',
        'options': [
            {'value': '0', 'label': 'No', 'points': 0},
            {'value': '1', 'label': 'Una brecha corta', 'points': 1},
            {'value': '3', 'label': 'Multiples o largas', 'points': 3},
        ],
    },
    {
        'key': 'living_context',
        'factor': 'Entorno y estilo de vida',
        'factor_key': 'environment',
        'weight': 2.5,
        'badge': 'Medio alto x2.5',
        'label': 'Con quien vive actualmente',
        'options': [
            {'value': '0', 'label': 'Con familia', 'points': 0},
            {'value': '3', 'label': 'Solo', 'points': 3},
            {'value': '4', 'label': 'Con amigos', 'points': 4},
        ],
    },
    {
        'key': 'tattoo_visibility',
        'factor': 'Entorno y estilo de vida',
        'factor_key': 'environment',
        'weight': 2.0,
        'badge': 'Medio x2',
        'label': 'Tatuajes abundantes en zonas visibles',
        'options': [
            {'value': '0', 'label': 'Sin tatuajes o discretos', 'points': 0},
            {'value': '2', 'label': 'Tres o mas tatuajes', 'points': 2},
            {'value': '4', 'label': 'Cuello o cara', 'points': 4},
        ],
    },
    {
        'key': 'job_count',
        'factor': 'Historial laboral',
        'factor_key': 'work_history',
        'weight': 2.0,
        'badge': 'Medio x2',
        'label': 'Cantidad de empleos en su historial',
        'options': [
            {'value': '0', 'label': 'Uno a cuatro', 'points': 0},
            {'value': '1', 'label': 'Cinco a seis', 'points': 1},
            {'value': '3', 'label': 'Siete o mas', 'points': 3},
        ],
    },
    {
        'key': 'conflict_history',
        'factor': 'Historial laboral',
        'factor_key': 'work_history',
        'weight': 1.0,
        'badge': 'Bajo medio x1',
        'label': 'Salidas por conflicto interpersonal',
        'options': [
            {'value': '0', 'label': 'No', 'points': 0},
            {'value': '1', 'label': 'Si una vez', 'points': 1},
            {'value': '3', 'label': 'Recurrente', 'points': 3},
        ],
    },
    {
        'key': 'recent_alcohol',
        'factor': 'Condiciones del examen',
        'factor_key': 'exam',
        'weight': 2.0,
        'badge': 'Medio x2',
        'label': 'Consumo de alcohol en las ultimas 72 horas',
        'options': [
            {'value': '0', 'label': 'No', 'points': 0},
            {'value': '3', 'label': 'Si', 'points': 3},
        ],
    },
    {
        'key': 'sleep_condition',
        'factor': 'Condiciones del examen',
        'factor_key': 'exam',
        'weight': 1.0,
        'badge': 'Bajo x1',
        'label': 'Horas de sueno antes del examen',
        'options': [
            {'value': '0', 'label': 'Siete horas o mas', 'points': 0},
            {'value': '1', 'label': 'Cinco a seis horas', 'points': 1},
            {'value': '2', 'label': 'Menos de cinco', 'points': 2},
        ],
    },
    {
        'key': 'breakfast_condition',
        'factor': 'Condiciones del examen',
        'factor_key': 'exam',
        'weight': 1.0,
        'badge': 'Bajo x1',
        'label': 'Llego desayunado',
        'options': [
            {'value': '0', 'label': 'Si desayuno', 'points': 0},
            {'value': '1', 'label': 'No desayuno', 'points': 1},
        ],
    },
]


CHECKLIST_TEMPLATE = [
    {
        'key': 'family',
        'label': 'Factor 1: Situacion familiar',
        'items': [
            {
                'key': 'family_parents',
                'label': 'Padres vivos y relacion activa',
                'help': 'Marcar si la respuesta deja una alerta o inconsistencia.',
                'alert': 'Factor estadistico mas fuerte en la base historica.',
            },
            {
                'key': 'family_legal_issues',
                'label': 'Antecedentes legales en familia directa',
                'help': 'Explorar impacto del antecedente en la vida del candidato.',
                'alert': 'Profundizar si existe contacto o dependencia con esa red.',
            },
            {
                'key': 'family_living',
                'label': 'Vive solo o con amigos',
                'help': 'Marcar si no cuenta con red familiar inmediata.',
                'alert': 'En la muestra interna fue una senal operativa importante.',
            },
        ],
    },
    {
        'key': 'finance',
        'label': 'Factor 2: Patrimonio y finanzas',
        'items': [
            {
                'key': 'finance_assets',
                'label': 'Bienes sin explicacion financiera clara',
                'help': 'Vehiculo, casa u otros activos sin soporte convincente.',
                'alert': 'Incongruencia patrimonial de alta prioridad.',
            },
            {
                'key': 'finance_story',
                'label': 'Narrativa patrimonial inconsistente',
                'help': 'La historia de vida no cuadra con sus ingresos reportados.',
                'alert': 'Pedir detalle de compras mayores y financiamiento.',
            },
            {
                'key': 'finance_gaps',
                'label': 'Brechas sin explicar',
                'help': 'Periodos sin actividad o ingresos que requieren aclaracion.',
                'alert': 'Registrar que hizo en esos periodos.',
            },
        ],
    },
    {
        'key': 'work',
        'label': 'Factor 3: Entorno y laboral',
        'items': [
            {
                'key': 'work_job_count',
                'label': 'Rotacion laboral extrema',
                'help': 'Numero de empleos por encima de lo esperable para el rol.',
                'alert': 'Cruzar con motivos de salida y referencias.',
            },
            {
                'key': 'work_exit_reason',
                'label': 'Salidas por conflicto o relato inestable',
                'help': 'Renuncias repetidas o problemas interpersonales.',
                'alert': 'Profundizar si el patron es recurrente.',
            },
            {
                'key': 'work_tattoos',
                'label': 'Tatuajes visibles abundantes',
                'help': 'Cantidad o ubicacion en cuello, cara o manos.',
                'alert': 'La senal es cantidad y visibilidad, no el tatuaje aislado.',
            },
        ],
    },
    {
        'key': 'exam',
        'label': 'Factor 4: Condiciones del examen',
        'items': [
            {
                'key': 'exam_rest_food',
                'label': 'Sin descanso o sin desayuno',
                'help': 'Registrar si llega con mala preparacion fisiologica.',
                'alert': 'Puede justificar reprogramacion o seguimiento.',
            },
            {
                'key': 'exam_alcohol',
                'label': 'Consumo reciente de alcohol',
                'help': 'Confirmar si hubo alcohol en las ultimas 72 horas.',
                'alert': 'Interfiere con la prueba y es senal de riesgo.',
            },
        ],
    },
]


NON_PREDICTIVE_FACTORS = [
    'Nivel educativo',
    'Edad',
    'Relacion regular con familia',
    'Estabilidad laboral simple',
]


VALIDATED_PATTERN_LIBRARY = [
    {
        'key': 'family_context',
        'field': 'family_context_flag',
        'label': 'Situacion familiar dificil',
        'strength': 'triple',
        'approved_pct': 27,
        'rejected_pct': 67,
        'approved_detail': '6 de 22',
        'rejected_detail': '6 de 9',
        'description': 'Padres fallecidos, ausentes o sin contacto activo duplican la probabilidad de falla.',
    },
    {
        'key': 'asset_mismatch',
        'field': 'asset_mismatch_flag',
        'label': 'Patrimonio desproporcionado',
        'strength': 'triple',
        'approved_pct': 0,
        'rejected_pct': 11,
        'approved_detail': '0 de 22',
        'rejected_detail': '1 de 9',
        'description': 'Incongruencia patrimonial es una senal muy especifica y de alta severidad.',
    },
    {
        'key': 'living_without_family',
        'field': 'living_without_family_flag',
        'label': 'Vive solo o con amigos',
        'strength': 'double',
        'approved_pct': 0,
        'rejected_pct': 22,
        'approved_detail': '0 de 22',
        'rejected_detail': '2 de 9',
        'description': 'La ausencia de red familiar inmediata fue una senal operativa clara en la muestra.',
    },
    {
        'key': 'visible_tattoos',
        'field': 'visible_tattoos_flag',
        'label': 'Tatuajes visibles abundantes',
        'strength': 'double',
        'approved_pct': 9,
        'rejected_pct': 22,
        'approved_detail': 'Discretos',
        'rejected_detail': 'Abundantes',
        'description': 'Importa la cantidad y la ubicacion visible, no el tatuaje aislado.',
    },
    {
        'key': 'high_turnover',
        'field': 'high_turnover_flag',
        'label': 'Rotacion laboral extrema',
        'strength': 'double',
        'approved_pct': 2.7,
        'rejected_pct': 4.3,
        'approved_detail': 'Promedio aprobados',
        'rejected_detail': 'Promedio no aprobados',
        'description': 'Alta rotacion y conflicto recurrente elevan la necesidad de verificacion.',
    },
    {
        'key': 'unexplained_gaps',
        'field': 'unexplained_gaps_flag',
        'label': 'Brechas sin explicar',
        'strength': 'simple',
        'approved_pct': 14,
        'rejected_pct': 100,
        'approved_detail': 'Casos puntuales',
        'rejected_detail': 'Alerta critica si persiste',
        'description': 'Periodos largos sin explicacion clara ameritan profundizar antes del poligrafo.',
    },
    {
        'key': 'exam_conditions',
        'field': 'exam_conditions_flag',
        'label': 'Condiciones del examen',
        'strength': 'simple',
        'approved_pct': 0,
        'rejected_pct': 100,
        'approved_detail': 'Controlable',
        'rejected_detail': 'Afecta la prueba',
        'description': 'Alcohol, falta de descanso o ayuno son senales de mala preparacion e impulsividad.',
    },
]


PREDICTOR_KEYS = [question['key'] for question in PREDICTOR_QUESTIONS]
CHECKLIST_KEYS = [
    item['key']
    for section in CHECKLIST_TEMPLATE
    for item in section['items']
]


def _selection_from_options(question_key):
    question = next(
        (item for item in PREDICTOR_QUESTIONS if item['key'] == question_key),
        None,
    )
    if not question:
        return []
    return [(option['value'], option['label']) for option in question['options']]


def _selection_to_float(value):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _get_predictor_result(values):
    total = 0.0
    answered_count = 0
    factor_scores = {
        'family': 0.0,
        'patrimony': 0.0,
        'environment': 0.0,
        'work_history': 0.0,
        'exam': 0.0,
    }
    for question in PREDICTOR_QUESTIONS:
        key = question['key']
        if values.get(key) not in (False, None, ''):
            answered_count += 1
        score = _selection_to_float(values.get(key)) * float(question['weight'])
        total += score
        factor_scores[question['factor_key']] += score

    if not answered_count:
        risk_level = 'not_evaluated'
        risk_label = 'Sin evaluar'
        summary_text = 'Seleccione respuestas para calcular el predictor.'
    elif total <= 5:
        risk_level = 'low'
        risk_label = 'Riesgo bajo'
        summary_text = 'Alta probabilidad de aprobar. Puede avanzar al poligrafo.'
    elif total <= 12:
        risk_level = 'moderate'
        risk_label = 'Riesgo moderado'
        summary_text = 'Profundizar entrevista antes de decidir si pasa a poligrafo.'
    elif total <= 20:
        risk_level = 'high'
        risk_label = 'Riesgo alto'
        summary_text = 'Riesgo alto de no aprobacion. Validar si justifica el costo de la prueba.'
    else:
        risk_level = 'very_high'
        risk_label = 'Riesgo muy alto'
        summary_text = 'Muy probable que no apruebe. Revisar descarte o verificacion adicional.'

    return {
        'answered_count': answered_count,
        'score_total': round(total, 1),
        'risk_level': risk_level,
        'risk_label': risk_label,
        'summary_text': summary_text,
        'factor_scores': factor_scores,
    }


def _build_pattern_flags(predictor, checklist):
    flags = {
        'family_context_flag': False,
        'asset_mismatch_flag': False,
        'living_without_family_flag': False,
        'visible_tattoos_flag': False,
        'high_turnover_flag': False,
        'unexplained_gaps_flag': False,
        'exam_conditions_flag': False,
    }
    if predictor:
        flags['family_context_flag'] = (
            _selection_to_float(predictor.family_structure) >= 2
            or _selection_to_float(predictor.family_contact) >= 2
        )
        flags['asset_mismatch_flag'] = _selection_to_float(predictor.asset_congruence) >= 3
        flags['living_without_family_flag'] = _selection_to_float(predictor.living_context) >= 3
        flags['visible_tattoos_flag'] = _selection_to_float(predictor.tattoo_visibility) >= 2
        flags['high_turnover_flag'] = (
            _selection_to_float(predictor.job_count) >= 3
            or _selection_to_float(predictor.conflict_history) >= 3
        )
        flags['unexplained_gaps_flag'] = _selection_to_float(predictor.income_gaps) >= 1
        flags['exam_conditions_flag'] = (
            _selection_to_float(predictor.recent_alcohol) >= 3
            or _selection_to_float(predictor.sleep_condition) >= 1
            or _selection_to_float(predictor.breakfast_condition) >= 1
        )
    if checklist:
        flags['family_context_flag'] = flags['family_context_flag'] or bool(
            checklist.family_parents or checklist.family_legal_issues or checklist.family_living
        )
        flags['asset_mismatch_flag'] = flags['asset_mismatch_flag'] or bool(
            checklist.finance_assets or checklist.finance_story
        )
        flags['living_without_family_flag'] = flags['living_without_family_flag'] or bool(
            checklist.family_living
        )
        flags['visible_tattoos_flag'] = flags['visible_tattoos_flag'] or bool(
            checklist.work_tattoos
        )
        flags['high_turnover_flag'] = flags['high_turnover_flag'] or bool(
            checklist.work_job_count or checklist.work_exit_reason
        )
        flags['unexplained_gaps_flag'] = flags['unexplained_gaps_flag'] or bool(
            checklist.finance_gaps
        )
        flags['exam_conditions_flag'] = flags['exam_conditions_flag'] or bool(
            checklist.exam_rest_food or checklist.exam_alcohol
        )
    return flags


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    zrn_predictor_ids = fields.One2many(
        'zrn.rrhh.predictor',
        'applicant_id',
        string='Predictores RRHH',
    )
    zrn_validated_pattern_ids = fields.One2many(
        'zrn.rrhh.validated.pattern',
        'applicant_id',
        string='Patrones validados RRHH',
    )
    zrn_interview_checklist_ids = fields.One2many(
        'zrn.rrhh.interview.checklist',
        'applicant_id',
        string='Checklists RRHH',
    )

    def _zrn_rrhh_get_predictor(self):
        self.ensure_one()
        return self.zrn_predictor_ids[:1]

    def _zrn_rrhh_get_checklist(self):
        self.ensure_one()
        return self.zrn_interview_checklist_ids[:1]

    def _zrn_rrhh_get_pattern(self):
        self.ensure_one()
        return self.zrn_validated_pattern_ids[:1]

    def _zrn_rrhh_recompute_pattern_records(self):
        pattern_model = self.env['zrn.rrhh.validated.pattern']
        for applicant in self:
            pattern = applicant._zrn_rrhh_get_pattern()
            if not pattern:
                pattern = pattern_model.create({
                    'applicant_id': applicant.id,
                    'company_id': applicant.company_id.id or self.env.company.id,
                })
            pattern.recompute_from_sources()


class ZrnRrhhPredictor(models.Model):
    _name = 'zrn.rrhh.predictor'
    _description = 'Predictor RRHH por solicitud'
    _order = 'evaluation_date desc, id desc'
    _rec_name = 'applicant_id'

    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Solicitud',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    evaluation_date = fields.Date(
        string='Fecha de evaluacion',
        default=fields.Date.context_today,
    )
    notes = fields.Text(string='Observaciones')

    family_structure = fields.Selection(_selection_from_options('family_structure'), string='Padres presentes')
    family_contact = fields.Selection(_selection_from_options('family_contact'), string='Contacto con padres')
    asset_congruence = fields.Selection(_selection_from_options('asset_congruence'), string='Patrimonio congruente')
    income_gaps = fields.Selection(_selection_from_options('income_gaps'), string='Brechas de ingreso')
    living_context = fields.Selection(_selection_from_options('living_context'), string='Con quien vive')
    tattoo_visibility = fields.Selection(_selection_from_options('tattoo_visibility'), string='Tatuajes visibles')
    job_count = fields.Selection(_selection_from_options('job_count'), string='Cantidad de empleos')
    conflict_history = fields.Selection(_selection_from_options('conflict_history'), string='Historial de conflicto')
    recent_alcohol = fields.Selection(_selection_from_options('recent_alcohol'), string='Alcohol reciente')
    sleep_condition = fields.Selection(_selection_from_options('sleep_condition'), string='Horas de sueno')
    breakfast_condition = fields.Selection(_selection_from_options('breakfast_condition'), string='Desayuno')

    answered_count = fields.Integer(
        string='Respuestas contestadas',
        compute='_compute_predictor_metrics',
        store=True,
    )
    score_total = fields.Float(
        string='Score total',
        compute='_compute_predictor_metrics',
        store=True,
    )
    family_score = fields.Float(string='Score familiar', compute='_compute_predictor_metrics', store=True)
    patrimony_score = fields.Float(string='Score patrimonial', compute='_compute_predictor_metrics', store=True)
    environment_score = fields.Float(string='Score entorno', compute='_compute_predictor_metrics', store=True)
    work_history_score = fields.Float(string='Score laboral', compute='_compute_predictor_metrics', store=True)
    exam_score = fields.Float(string='Score examen', compute='_compute_predictor_metrics', store=True)
    risk_level = fields.Selection(
        [
            ('not_evaluated', 'Sin evaluar'),
            ('low', 'Riesgo bajo'),
            ('moderate', 'Riesgo moderado'),
            ('high', 'Riesgo alto'),
            ('very_high', 'Riesgo muy alto'),
        ],
        string='Nivel de riesgo',
        compute='_compute_predictor_metrics',
        store=True,
    )
    risk_label = fields.Char(string='Etiqueta de riesgo', compute='_compute_predictor_metrics', store=True)
    summary_text = fields.Text(string='Interpretacion', compute='_compute_predictor_metrics', store=True)

    _sql_constraints = [
        (
            'zrn_rrhh_predictor_applicant_unique',
            'unique(applicant_id)',
            'Solo puede existir un predictor por solicitud.',
        ),
    ]

    @api.depends(*PREDICTOR_KEYS)
    def _compute_predictor_metrics(self):
        for record in self:
            values = {key: getattr(record, key) for key in PREDICTOR_KEYS}
            result = _get_predictor_result(values)
            record.answered_count = result['answered_count']
            record.score_total = result['score_total']
            record.family_score = round(result['factor_scores']['family'], 1)
            record.patrimony_score = round(result['factor_scores']['patrimony'], 1)
            record.environment_score = round(result['factor_scores']['environment'], 1)
            record.work_history_score = round(result['factor_scores']['work_history'], 1)
            record.exam_score = round(result['factor_scores']['exam'], 1)
            record.risk_level = result['risk_level']
            record.risk_label = result['risk_label']
            record.summary_text = result['summary_text']

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped('applicant_id')._zrn_rrhh_recompute_pattern_records()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.mapped('applicant_id')._zrn_rrhh_recompute_pattern_records()
        return result


class ZrnRrhhInterviewChecklist(models.Model):
    _name = 'zrn.rrhh.interview.checklist'
    _description = 'Checklist de entrevista RRHH por solicitud'
    _order = 'id desc'
    _rec_name = 'applicant_id'

    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Solicitud',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    interview_date = fields.Date(
        string='Fecha de entrevista',
        default=fields.Date.context_today,
    )
    observations = fields.Text(string='Observaciones')

    family_parents = fields.Boolean(string='Padres y relacion activa')
    family_legal_issues = fields.Boolean(string='Antecedentes legales familiares')
    family_living = fields.Boolean(string='Vive solo o con amigos')
    finance_assets = fields.Boolean(string='Bienes sin explicacion')
    finance_story = fields.Boolean(string='Narrativa patrimonial inconsistente')
    finance_gaps = fields.Boolean(string='Brechas sin explicar')
    work_job_count = fields.Boolean(string='Rotacion laboral extrema')
    work_exit_reason = fields.Boolean(string='Conflicto o salida recurrente')
    work_tattoos = fields.Boolean(string='Tatuajes visibles abundantes')
    exam_rest_food = fields.Boolean(string='Sin descanso o desayuno')
    exam_alcohol = fields.Boolean(string='Alcohol reciente')

    alert_count = fields.Integer(
        string='Alertas marcadas',
        compute='_compute_checklist_metrics',
        store=True,
    )
    summary_text = fields.Text(
        string='Resumen checklist',
        compute='_compute_checklist_metrics',
        store=True,
    )

    _sql_constraints = [
        (
            'zrn_rrhh_checklist_applicant_unique',
            'unique(applicant_id)',
            'Solo puede existir un checklist por solicitud.',
        ),
    ]

    @api.depends(*CHECKLIST_KEYS)
    def _compute_checklist_metrics(self):
        for record in self:
            alert_count = sum(1 for key in CHECKLIST_KEYS if getattr(record, key))
            record.alert_count = alert_count
            if not alert_count:
                record.summary_text = 'Sin alertas marcadas en la entrevista.'
            elif alert_count <= 2:
                record.summary_text = 'Alertas puntuales. Requiere seguimiento dirigido.'
            elif alert_count <= 4:
                record.summary_text = 'Varias alertas relevantes. Conviene profundizar antes de poligrafo.'
            else:
                record.summary_text = 'Acumulacion alta de alertas. Escalar revision de RRHH.'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped('applicant_id')._zrn_rrhh_recompute_pattern_records()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.mapped('applicant_id')._zrn_rrhh_recompute_pattern_records()
        return result


class ZrnRrhhValidatedPattern(models.Model):
    _name = 'zrn.rrhh.validated.pattern'
    _description = 'Patrones validados RRHH por solicitud'
    _order = 'id desc'
    _rec_name = 'applicant_id'

    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Solicitud',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    family_context_flag = fields.Boolean(string='Situacion familiar dificil')
    asset_mismatch_flag = fields.Boolean(string='Patrimonio desproporcionado')
    living_without_family_flag = fields.Boolean(string='Vive sin red familiar')
    visible_tattoos_flag = fields.Boolean(string='Tatuajes visibles')
    high_turnover_flag = fields.Boolean(string='Rotacion alta')
    unexplained_gaps_flag = fields.Boolean(string='Brechas sin explicar')
    exam_conditions_flag = fields.Boolean(string='Condiciones del examen')

    matched_pattern_count = fields.Integer(string='Patrones coincidentes')
    severity_level = fields.Selection(
        [
            ('low', 'Baja'),
            ('moderate', 'Moderada'),
            ('high', 'Alta'),
        ],
        string='Severidad',
    )
    summary_text = fields.Text(string='Resumen')

    _sql_constraints = [
        (
            'zrn_rrhh_validated_pattern_applicant_unique',
            'unique(applicant_id)',
            'Solo puede existir un registro de patrones por solicitud.',
        ),
    ]

    def recompute_from_sources(self):
        for record in self:
            predictor = record.applicant_id._zrn_rrhh_get_predictor()
            checklist = record.applicant_id._zrn_rrhh_get_checklist()
            flags = _build_pattern_flags(predictor, checklist)
            matched_count = sum(1 for value in flags.values() if value)
            severity = 'low'
            summary = 'Sin patrones activos.'
            predictor_level = predictor.risk_level if predictor else 'not_evaluated'
            if matched_count >= 4 or predictor_level in ('high', 'very_high'):
                severity = 'high'
                summary = 'Combinacion de patrones de alto riesgo. Requiere validacion profunda.'
            elif matched_count >= 2 or predictor_level == 'moderate':
                severity = 'moderate'
                summary = 'Hay patrones suficientes para pedir entrevista ampliada y referencias.'
            elif matched_count:
                summary = 'Existe al menos un patron a monitorear antes de avanzar.'
            record.write({
                **flags,
                'matched_pattern_count': matched_count,
                'severity_level': severity,
                'summary_text': summary,
            })

