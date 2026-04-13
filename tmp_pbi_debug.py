settings = env['ir.config_parameter'].sudo()
keys = [
    'pbi_connections.instance_key',
    'pbi_connections.client_validation_base_url',
    'pbi_connections.client_key',
    'pbi_connections.client_validation_api_key',
]

print('CONFIG:')
for key in keys:
    print(f'{key}={settings.get_param(key)!r}')

config = env['pbi_connections.api.config'].sudo().search([], order='id asc', limit=1)
print('CONFIG_RECORD_ID:', config.id)
print('BEFORE:', {
    'show_dashboard': config.show_dashboard,
    'state': config.client_validation_state,
    'code': config.client_status_code,
    'title': config.client_status_title,
    'message': config.client_status_message,
    'debug': config.client_validation_debug,
})

config._refresh_client_validation_status()
config.invalidate_recordset()

print('AFTER:', {
    'show_dashboard': config.show_dashboard,
    'state': config.client_validation_state,
    'code': config.client_status_code,
    'title': config.client_status_title,
    'message': config.client_status_message,
    'debug': config.client_validation_debug,
})

inicio = env['pbi_connections.inicio'].sudo().search([], order='id asc', limit=1)
print('INICIO:', {
    'id': inicio.id,
    'show_dashboard': inicio.show_dashboard,
    'state': inicio.client_validation_state,
    'code': inicio.client_status_code,
    'title': inicio.client_status_title,
    'message': inicio.client_status_message,
    'debug': inicio.client_validation_debug,
})

