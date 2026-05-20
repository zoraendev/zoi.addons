# -*- coding: utf-8 -*-
{
    'name': 'Automatizations',
    'summary': 'Base modular para automatizaciones operativas y transaccionales',
    'description': """
Modulo base para exponer automatizaciones, consultas y transacciones por dominio.
La primera iteracion incorpora la capa logica de customers para construir el
perfil que usara el bot al reconocer clientes y deja preparada la estructura
para products y sales_orders.
    """,
    'author': 'Zoraen',
    'website': 'https://www.zoraen.com',
    'category': 'Sales',
    'version': '1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'sale'],
    'data': [],
    'demo': [],
    'installable': True,
    'application': False,
}
